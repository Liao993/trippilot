"""Shared Bronze ingestion flow for the per-dataset Airbnb data products.

The F06 calendar and reviews notebooks (and future datasets) previously
carried near-identical 21-cell ingestion pipelines; this module holds
that flow ONCE. A notebook now supplies only its dataset spec, the run
widgets and the result display (pre-F07 cleanup T03).

The flow is the tested F06.2/F06.3 behavior, unchanged:

* The manifest record is resolved by EXPLICIT ``source_file_id``: the
  family/entity/version identity (insideairbnb/toronto/2026-09-16 +
  csv.gz) is shared by the listings, calendar and reviews files, so
  resolving by identity alone is ambiguous (verified in F06.1).
* The landed bytes are verified BEFORE Spark parses anything: hash and
  size against the manifest, full gzip decompression (csv.gz), header
  fingerprint against the registered schema_version (schema-drift
  gate) for every CSV variant, GeoJSON structure re-validation, and
  every contract-required column present.
* Every value stays a raw string - no casting of dates, prices or
  availability (that is Silver, F09.1).
* Rows failing the contract's required-field/date checks are RETAINED
  with an explicit ``_quality_status`` / ``_quality_reason``, never
  dropped, quarantined or coerced.
* The unified ingestion manifest (F07.4: ONE shared
  ops.ingestion_manifest per environment, one row per source file per
  run) records the run: an exact rerun skips, a corrected file is
  blocked unless ``force_reload`` authorizes the replacement, and
  read/write failures are recorded on the manifest row before the
  exception propagates.
* One atomic Delta overwrite with ``replaceWhere`` replaces only this
  city/snapshot slice; ``merge_schema`` lets the table pick up the
  provenance and quality columns on first creation.
* Reconciliation asserts one run identity, raw == bronze row counts
  and the retained invalid-row count, so the retention promise is
  auditable.

City, snapshot date and source family are DERIVED from the landed
manifest record (``source_entity_id``, ``source_version``,
``source_family``) - never hard-coded in the notebooks.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from src.airbnb.geojson_reader import parse_geojson_features
from src.airbnb.ingestion import write_snapshot
from src.airbnb.row_quality import (
    annotate_row_quality,
    extract_row_validation_policy,
)
from src.airbnb.source_inspection import (
    check_required_columns,
    inspect_csv_gz_header,
    inspect_csv_header,
    inspect_geojson,
    verify_gzip_integrity,
)
from src.common.environment import (
    repo_root,
    resolve_table,
    validate_destination,
    validate_force_reload,
    validate_run_mode,
)
from src.common.ingestion_manifest import IngestionManifestStore
from src.common.provenance import (
    PROVENANCE_COLUMNS,
    build_provenance_columns,
    build_run_id,
)
from src.common.run_controls import (
    _in_dataset_scope,
    decide_ingestion_action,
    latest_successful_source_file_id,
    record_control_failure,
)
from src.common.source_acquisition import verify_landed_record
from src.common.source_manifest_store import ManifestStore
from src.quality.contract_loader import get_table_rules, load_contract

READ_OPTIONS = {
    "header": True,
    "inferSchema": False,
    "multiLine": True,
    "escape": '"',
}


def verify_and_inspect_source(
    source_record: dict,
    schema_label: str,
) -> dict:
    """Verify and inspect the landed bytes for the record's file_type (F07.2).

    csv.gz keeps the verified F06 behaviour exactly (full decompression
    + header fingerprint); plain csv gets the same header fingerprint
    through the plain-text reader; geojson is re-validated as a
    FeatureCollection with the canonical property/geometry fingerprint.
    Any other file type is a hard error before Spark touches anything.
    """
    path = source_record["landing_path"]
    file_type = source_record["file_type"]
    if file_type == "csv.gz":
        verify_gzip_integrity(path)
        return inspect_csv_gz_header(path, schema_label=schema_label)
    if file_type == "csv":
        return inspect_csv_header(path, schema_label=schema_label)
    if file_type == "geojson":
        return inspect_geojson(path, schema_label=schema_label)
    raise ValueError(f"Unsupported Bronze source file type: {file_type!r}")


@dataclass(frozen=True)
class BronzeDatasetSpec:
    """Everything the shared flow needs to know about one dataset.

    Attributes:
        dataset: dataset tag for ingestion-manifest rows and log
            messages (``calendar``, ``reviews``, ...).
        schema_label: label for header-inspection errors.
        contract_path: repo-relative Bronze contract YAML path.
        rules_key: rules key inside that contract.
        bronze_key / manifest_key: environment-resolver keys for the
            run-mode-resolved destinations. The run outcome goes to the
            ONE shared ingestion manifest (F07.4).
        default_source_file_id: notebook widget default.
    """

    dataset: str
    schema_label: str
    contract_path: str
    rules_key: str
    bronze_key: str
    manifest_key: str = "source_manifest"
    default_source_file_id: str = ""


def run_bronze_ingestion(
    spec: BronzeDatasetSpec,
    spark,
    source_file_id: str,
    run_mode: str = "test",
    force_reload: str | bool = False,
    run_id: str | None = None,
) -> dict:
    """Run the complete shared Bronze ingestion flow for one dataset.

    Returns a summary dict with the run identity, row counts and the
    verification/snapshot DataFrames for display. Raises
    AssertionError when the run must be skipped, and propagates
    read/write exceptions only after recording them on the manifest
    row. ``run_id`` optionally carries a shared identifier so one
    ingestion run loading several assets writes one manifest row per
    asset under the same run identifier (F07.4); when omitted a fresh
    run identity is built.

    Destination safety (F07.4): every target is resolved through the
    environment resolver and guarded against cross-catalog writes - a
    test run can never touch ``trippilot_dev`` and a live run can
    never touch ``trippilot_test``.
    """
    # The pyspark import stays inside the function so CI (which has no
    # Databricks-provided libraries) can import this module for the
    # pure helpers without pyspark - the row_quality.py pattern.
    from pyspark.sql import functions as F

    run_mode = validate_run_mode(run_mode)
    force_reload = validate_force_reload(force_reload)

    manifest_table = resolve_table(spec.manifest_key, run_mode)
    bronze_table = validate_destination(
        resolve_table(spec.bronze_key, run_mode), run_mode
    )
    ingestion_manifest_table = validate_destination(
        resolve_table("ingestion_manifest", run_mode), run_mode
    )

    contract = load_contract(repo_root() / spec.contract_path)
    rules = get_table_rules(contract, spec.rules_key)
    required_columns = list(rules["required_columns"])
    row_required_fields, row_date_fields = extract_row_validation_policy(
        contract, spec.rules_key
    )

    print(f"Manifest table: {manifest_table}")
    print(f"Bronze target:  {bronze_table}")
    print(f"Ingestion manifest: {ingestion_manifest_table}")
    print(
        f"Contract:       {spec.contract_path} "
        f"({len(required_columns)} required columns)"
    )
    print(f"Row validation:  required={row_required_fields} dates={row_date_fields}")

    # Resolve the exact landed record and validate the immutable
    # landing object BEFORE Spark parses it (F06.2-T02).
    store = ManifestStore(manifest_table, spark=spark)
    source_record = store.read_landed(source_file_id)

    verify_landed_record(source_record)
    inspection = verify_and_inspect_source(source_record, spec.schema_label)
    assert inspection["schema_version"] == source_record["schema_version"], (
        f"Schema drift: manifest recorded {source_record['schema_version']}, "
        f"landed header is {inspection['schema_version']}"
    )
    check_required_columns(inspection["columns"], required_columns)

    print(f"Landing path:   {source_record['landing_path']}")
    print(f"Byte size:       {source_record['byte_size']:,}")
    print(f"File hash:       {source_record['file_hash_sha256'][:16]}...")
    print(f"Schema version:  {source_record['schema_version']}")
    print(f"Observed columns ({len(inspection['columns'])}): {inspection['columns']}")
    if "feature_count" in inspection:
        print(f"Feature count:   {inspection['feature_count']:,}")

    # Dataset identity comes from the landed record itself (F06.1).
    city = source_record["source_entity_id"]
    snapshot_date = source_record["source_version"]
    source = source_record["source_family"]
    dataset = spec.dataset

    # F07.4: dataset-scoped decision from the ONE shared ingestion
    # manifest (created/repaired from the shared canonical shape).
    # The reused decision helpers scope rows by the dataset tag
    # themselves, so every dataset's history stays isolated in the
    # shared table exactly as it was in the per-dataset controls.
    manifest_store = IngestionManifestStore(ingestion_manifest_table, spark=spark)
    manifest_store.ensure_table()
    existing_controls = manifest_store.read_for_slice(city, snapshot_date)
    ingestion_action = decide_ingestion_action(
        existing_controls=existing_controls,
        city=city,
        snapshot_date=snapshot_date,
        source_file_id=source_record["source_file_id"],
        force_reload=force_reload,
        dataset=dataset,
    )
    dataset_controls = [
        control for control in existing_controls if _in_dataset_scope(control, dataset)
    ]
    print(
        f"Existing control records for {dataset}/{city}/{snapshot_date}: "
        f"{len(dataset_controls)} in dataset scope "
        f"({len(existing_controls)} manifest rows across datasets)"
    )
    print(f"Ingestion action: {ingestion_action}")

    # Safe no-op: an exact retry of the same file. A corrected file
    # without force_reload already raised above with instructions.
    assert ingestion_action == "load", (
        f"Skipping ingestion: the exact source file "
        f"{source_record['source_file_id']} already loaded successfully for "
        f"{dataset} / {city} / {snapshot_date}. Nothing was read or written. "
        "Set force_reload=true to rerun the identical file, or select the new "
        "source_file_id to reprocess a corrected file."
    )

    # Start the manifest row, linked to its exact source-file identity
    # and - when reprocessing a corrected file - the identity it replaced.
    run_id = run_id or build_run_id()
    prior_source_file_id = latest_successful_source_file_id(
        existing_controls, dataset=dataset
    )
    started_at_utc = datetime.now(UTC).isoformat()
    manifest_store.start_run(
        {
            "city": city,
            "snapshot_date": snapshot_date,
            "run_id": run_id,
            "dataset": dataset,
            "source_file_id": source_record["source_file_id"],
            "prior_source_file_id": prior_source_file_id,
            "started_at_utc": started_at_utc,
            "target_table": bronze_table,
        }
    )
    print(f"Started ingestion run: {run_id}")
    if prior_source_file_id and prior_source_file_id != source_record["source_file_id"]:
        print(f"Controlled reprocess: replacing source_file_id {prior_source_file_id}")

    # Read the landed source file: all values stay STRINGS (F06.2-T01).
    # GeoJSON sources are parsed to one row per feature with the full
    # geometry preserved as a raw JSON string (F07.2-T02); the driver-side
    # parse is bounded by the validated feature count.
    try:
        if source_record["file_type"] == "geojson":
            rows = parse_geojson_features(
                source_record["landing_path"],
                property_keys=inspection["columns"],
            )
            from pyspark.sql import types as T

            schema = T.StructType(
                [
                    T.StructField(name, T.StringType(), True)
                    for name in [*inspection["columns"], "geometry_json"]
                ]
            )
            raw_df = spark.createDataFrame(rows, schema)
        else:
            reader = spark.read
            for key, value in READ_OPTIONS.items():
                reader = reader.option(key, value)
            raw_df = reader.csv(source_record["landing_path"])
        raw_row_count = raw_df.count()
    except Exception as read_error:
        record_control_failure(spark, ingestion_manifest_table, run_id, read_error)
        raise
    print(f"Input path: {source_record['landing_path']}")
    print(f"Raw rows read: {raw_row_count:,}")

    # Row quality from the contract (F06.2-T03): invalid rows are
    # retained with an explicit reason, never dropped.
    quality_df = annotate_row_quality(raw_df, row_required_fields, row_date_fields)
    status_counts = {
        row["_quality_status"]: row["count"]
        for row in quality_df.groupBy("_quality_status").count().collect()
    }
    valid_count = status_counts.get("valid", 0)
    invalid_count = status_counts.get("invalid", 0)
    print(f"Valid rows:   {valid_count:,}")
    print(f"Invalid rows: {invalid_count:,} (retained with _quality_reason)")

    # The 8 provenance columns required by the dataset contract.
    provenance = build_provenance_columns(
        source=source,
        city=city,
        snapshot_date=snapshot_date,
        raw_path=source_record["landing_path"],
        run_id=run_id,
        source_file_id=source_record["source_file_id"],
        file_hash_sha256=source_record["file_hash_sha256"],
    )
    bronze_df = quality_df
    for column in PROVENANCE_COLUMNS:
        bronze_df = bronze_df.withColumn(column, F.lit(provenance[column.lstrip("_")]))
    print(f"Run ID: {run_id}")

    # One atomic replaceWhere overwrite of this city/snapshot slice;
    # failures are recorded on the control row before propagating.
    try:
        write_snapshot(
            bronze_df,
            bronze_table,
            city,
            snapshot_date,
            "_city",
            "_snapshot_date",
            merge_schema=True,
        )
        bronze_row_count = (
            spark.table(bronze_table)
            .filter(
                (F.col("_city") == city) & (F.col("_snapshot_date") == snapshot_date)
            )
            .count()
        )
    except Exception as write_error:
        record_control_failure(spark, ingestion_manifest_table, run_id, write_error)
        raise

    completed_at_utc = datetime.now(UTC).isoformat()
    manifest_store.complete_run(
        run_id=run_id,
        source_row_count=raw_row_count,
        loaded_row_count=bronze_row_count,
        rejected_row_count=invalid_count,
        completed_at_utc=completed_at_utc,
    )
    print(f"Target table: {bronze_table}")
    print(f"Bronze rows written for {city} / {snapshot_date}: {bronze_row_count:,}")

    # Reconcile and verify: one run identity, raw == bronze counts, and
    # the retained invalid-row count is auditable in-table.
    verification_df = (
        spark.table(bronze_table)
        .filter(F.col("_source_file_id") == source_record["source_file_id"])
        .agg(
            F.count("*").alias("bronze_row_count"),
            F.countDistinct("_run_id").alias("distinct_run_ids"),
            F.sum(F.when(F.col("_quality_status") == "invalid", 1).otherwise(0)).alias(
                "invalid_rows"
            ),
        )
    )
    identity_counts = verification_df.collect()[0]
    assert identity_counts["distinct_run_ids"] == 1, (
        f"Expected one run identity, found {identity_counts['distinct_run_ids']}"
    )
    assert bronze_row_count == raw_row_count, (
        f"Row-count mismatch: raw={raw_row_count}, bronze={bronze_row_count}"
    )
    assert identity_counts["bronze_row_count"] == raw_row_count, (
        f"Source-identity mismatch: raw={raw_row_count}, "
        f"bronze for this source_file_id={identity_counts['bronze_row_count']}"
    )
    assert identity_counts["invalid_rows"] == invalid_count, (
        "Invalid-row count changed between annotation and the Bronze write"
    )
    print(f"{dataset.capitalize()} Bronze ingestion verification passed.")

    # Post-run summary of every loaded city/snapshot slice, including
    # the retained invalid rows (F06.2-T03).
    snapshot_summary = spark.sql(f"""
        SELECT
            _city,
            _snapshot_date,
            COUNT(*) AS row_count,
            SUM(CASE WHEN _quality_status = 'invalid' THEN 1 ELSE 0 END) AS invalid_rows,
            COUNT(DISTINCT _run_id) AS run_count,
            COUNT(DISTINCT _source_file_id) AS source_file_count,
            MAX(_source_file_id) AS current_source_file_id
        FROM {bronze_table}
        GROUP BY _city, _snapshot_date
    """)

    return {
        "dataset": dataset,
        "city": city,
        "snapshot_date": snapshot_date,
        "source_file_id": source_record["source_file_id"],
        "run_id": run_id,
        "ingestion_action": ingestion_action,
        "raw_row_count": raw_row_count,
        "bronze_row_count": bronze_row_count,
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "manifest_table": manifest_table,
        "bronze_table": bronze_table,
        "ingestion_manifest_table": ingestion_manifest_table,
        "raw_df": raw_df,
        "bronze_df": bronze_df,
        "verification_df": verification_df,
        "snapshot_summary": snapshot_summary,
    }
