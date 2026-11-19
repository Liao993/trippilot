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
  size against the manifest, full gzip decompression, header
  fingerprint against the registered schema_version (schema-drift
  gate), and every contract-required column present.
* Every value stays a raw string - no casting of dates, prices or
  availability (that is Silver, F09.1).
* Rows failing the contract's required-field/date checks are RETAINED
  with an explicit ``_quality_status`` / ``_quality_reason``, never
  dropped, quarantined or coerced.
* The dataset's own ingestion-control table (dataset-tagged, F06.3)
  records the run: an exact rerun skips, a corrected file is blocked
  unless ``force_reload`` authorizes the replacement, and read/write
  failures are recorded on the control row before the exception
  propagates.
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
from pathlib import Path

from src.airbnb.ingestion import write_snapshot
from src.airbnb.row_quality import (
    annotate_row_quality,
    extract_row_validation_policy,
)
from src.airbnb.source_inspection import (
    check_required_columns,
    inspect_csv_gz_header,
    verify_gzip_integrity,
)
from src.common.environment import (
    resolve_table,
    validate_force_reload,
    validate_run_mode,
)
from src.common.provenance import build_provenance_columns, build_run_id
from src.common.run_controls import (
    decide_ingestion_action,
    latest_successful_source_file_id,
    record_control_failure,
)
from src.common.source_acquisition import verify_landed_record
from src.common.source_manifest_store import ManifestStore
from src.common.table_setup import (
    PER_DATASET_CONTROL_COLUMNS,
    ensure_operational_table,
)
from src.quality.contract_loader import get_table_rules, load_contract

PROVENANCE_COLUMNS = (
    "_source",
    "_city",
    "_snapshot_date",
    "_raw_path",
    "_run_id",
    "_ingested_at_utc",
    "_source_file_id",
    "_file_hash_sha256",
)

READ_OPTIONS = {
    "header": True,
    "inferSchema": False,
    "multiLine": True,
    "escape": '"',
}


def repo_root() -> Path:
    """Locate the repository root from this module's own location."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src").is_dir() and (parent / "config").is_dir():
            return parent
    raise RuntimeError("Cannot locate the TripPilot repository root.")


@dataclass(frozen=True)
class BronzeDatasetSpec:
    """Everything the shared flow needs to know about one dataset.

    Attributes:
        dataset: dataset tag for control rows and log messages
            (``calendar``, ``reviews``, ...).
        schema_label: label for header-inspection errors.
        contract_path: repo-relative Bronze contract YAML path.
        rules_key: rules key inside that contract.
        bronze_key / control_key / manifest_key: environment-resolver
            keys for the run-mode-resolved destinations.
        default_source_file_id: notebook widget default.
    """

    dataset: str
    schema_label: str
    contract_path: str
    rules_key: str
    bronze_key: str
    control_key: str
    manifest_key: str = "source_manifest"
    default_source_file_id: str = ""


def sql_string_literal(value: str) -> str:
    """Quote a value as a single-quoted SQL string literal."""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def build_control_insert_sql(
    control_table: str,
    *,
    city: str,
    snapshot_date: str,
    run_id: str,
    started_at_utc: str,
    source_file_id: str,
    prior_source_file_id: str | None,
    dataset: str,
) -> str:
    """Return the control-row INSERT that starts a run (F06.3-T02)."""
    prior = (
        "NULL"
        if prior_source_file_id is None
        else sql_string_literal(prior_source_file_id)
    )
    return (
        f"INSERT INTO {control_table} VALUES ("
        f"{sql_string_literal(city)}, "
        f"{sql_string_literal(snapshot_date)}, "
        f"{sql_string_literal(run_id)}, "
        "'running', 0, "
        f"{sql_string_literal(started_at_utc)}, NULL, NULL, "
        f"{sql_string_literal(source_file_id)}, {prior}, "
        f"{sql_string_literal(dataset)})"
    )


def build_control_success_sql(
    control_table: str,
    *,
    run_id: str,
    row_count: int,
    completed_at_utc: str,
) -> str:
    """Return the control-row UPDATE that records a successful run."""
    return (
        f"UPDATE {control_table} SET status = 'success', "
        f"row_count = {int(row_count)}, "
        f"completed_at_utc = {sql_string_literal(completed_at_utc)}, "
        f"error_message = NULL WHERE run_id = {sql_string_literal(run_id)}"
    )


def run_bronze_ingestion(
    spec: BronzeDatasetSpec,
    spark,
    source_file_id: str,
    run_mode: str = "test",
    force_reload: str | bool = False,
) -> dict:
    """Run the complete shared Bronze ingestion flow for one dataset.

    Returns a summary dict with the run identity, row counts and the
    verification/snapshot DataFrames for display. Raises
    AssertionError when the run must be skipped, and propagates
    read/write exceptions only after recording them on the control row.
    """
    # The pyspark import stays inside the function so CI (which has no
    # Databricks-provided libraries) can import this module for the
    # pure helpers without pyspark - the row_quality.py pattern.
    from pyspark.sql import functions as F

    run_mode = validate_run_mode(run_mode)
    force_reload = validate_force_reload(force_reload)

    manifest_table = resolve_table(spec.manifest_key, run_mode)
    bronze_table = resolve_table(spec.bronze_key, run_mode)
    control_table = resolve_table(spec.control_key, run_mode)

    contract = load_contract(repo_root() / spec.contract_path)
    rules = get_table_rules(contract, spec.rules_key)
    required_columns = list(rules["required_columns"])
    row_required_fields, row_date_fields = extract_row_validation_policy(
        contract, spec.rules_key
    )

    print(f"Manifest table: {manifest_table}")
    print(f"Bronze target:  {bronze_table}")
    print(f"Control table:  {control_table}")
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
    verify_gzip_integrity(source_record["landing_path"])
    inspection = inspect_csv_gz_header(
        source_record["landing_path"], schema_label=spec.schema_label
    )
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

    # Dataset identity comes from the landed record itself (F06.1).
    city = source_record["source_entity_id"]
    snapshot_date = source_record["source_version"]
    source = source_record["source_family"]
    dataset = spec.dataset

    # F06.3-T01: dataset-scoped ingestion-control decision. The control
    # table is created/repaired from the shared canonical shape.
    ensure_operational_table(spark, control_table, PER_DATASET_CONTROL_COLUMNS)
    existing_controls = [
        row.asDict()
        for row in spark.table(control_table)
        .filter((F.col("city") == city) & (F.col("snapshot_date") == snapshot_date))
        .collect()
    ]
    ingestion_action = decide_ingestion_action(
        existing_controls=existing_controls,
        city=city,
        snapshot_date=snapshot_date,
        source_file_id=source_record["source_file_id"],
        force_reload=force_reload,
        dataset=dataset,
    )
    print(
        f"Existing control records for {dataset}/{city}/{snapshot_date}: "
        f"{len(existing_controls)}"
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

    # Start the control record, linked to its exact source-file identity
    # and - when reprocessing a corrected file - the identity it replaced.
    run_id = build_run_id()
    prior_source_file_id = latest_successful_source_file_id(existing_controls)
    started_at_utc = datetime.now(UTC).isoformat()
    spark.sql(
        build_control_insert_sql(
            control_table,
            city=city,
            snapshot_date=snapshot_date,
            run_id=run_id,
            started_at_utc=started_at_utc,
            source_file_id=source_record["source_file_id"],
            prior_source_file_id=prior_source_file_id,
            dataset=dataset,
        )
    )
    print(f"Started ingestion run: {run_id}")
    if prior_source_file_id and prior_source_file_id != source_record["source_file_id"]:
        print(f"Controlled reprocess: replacing source_file_id {prior_source_file_id}")

    # Read the landed source file: all values stay STRINGS (F06.2-T01).
    try:
        reader = spark.read
        for key, value in READ_OPTIONS.items():
            reader = reader.option(key, value)
        raw_df = reader.csv(source_record["landing_path"])
        raw_row_count = raw_df.count()
    except Exception as read_error:
        record_control_failure(spark, control_table, run_id, read_error)
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
        record_control_failure(spark, control_table, run_id, write_error)
        raise

    completed_at_utc = datetime.now(UTC).isoformat()
    spark.sql(
        build_control_success_sql(
            control_table,
            run_id=run_id,
            row_count=bronze_row_count,
            completed_at_utc=completed_at_utc,
        )
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
        "control_table": control_table,
        "raw_df": raw_df,
        "bronze_df": bronze_df,
        "verification_df": verification_df,
        "snapshot_summary": snapshot_summary,
    }
