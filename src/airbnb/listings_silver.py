"""Normalized detailed-listings Silver transformation (F09.1).

Bronze is source-faithful on purpose: every value is a raw string so
audit needs no interpreter. This module owns the OTHER half of that
contract - the deterministic, contract-driven projection into the
Silver analytical interface described by
``contracts/airbnb/silver_listings.yml`` (grain, composite key,
standardized names, explicit types, retained lineage).

F09.1 scope, enforced here:

* EVERY input row is preserved. There is no business filtering, no
  deduplication and no accepted/rejected split - those belong to
  F09.2/F09.3.
* Parsing is null-safe and deterministic: values are trimmed,
  blanks become null, and typed columns parse through ``try_cast``
  (never a bare cast), so a malformed value becomes null plus an
  entry in ``normalization_issues`` instead of a failed run.
* ``normalization_issues`` names every Silver column whose non-blank
  raw value failed conversion, so F09.2 can classify records later;
  the raw values stay queryable in Bronze through the preserved
  lineage columns (source_file_id, listing_id, snapshot_date).
* The Bronze slice is selected by landed identity - registry bounds
  plus the latest successful Bronze run recorded in the unified
  ingestion manifest, or an explicit source_file_id - never a guessed
  path. Legacy source-manifest rows carry no dataset tag (immutable
  history), so F08's dataset-based landed resolution cannot see the
  real slices; the ingestion manifest can and does.
* The write replaces exactly one city/snapshot slice, the same
  boundary Bronze uses (``write_snapshot`` replaceWhere).

The pyspark imports stay inside the functions so CI can import this
module for the pure helpers without pyspark - the bronze_flow.py
pattern.
"""

from typing import Any

from src.airbnb.ingestion import write_snapshot
from src.common.city_registry import get_city
from src.common.control_plane import (
    list_city_datasets,
    load_city_registry,
    load_project_config,
)
from src.common.environment import (
    repo_root,
    resolve_table,
    validate_destination,
    validate_run_mode,
)
from src.common.ingestion_manifest import IngestionManifestStore
from src.common.provenance import PROVENANCE_COLUMNS
from src.common.source_acquisition import verify_landed_record
from src.common.source_manifest_store import ManifestStore
from src.quality.contract_loader import get_table_rules, load_contract

SILVER_CONTRACT_PATH = "contracts/airbnb/silver_listings.yml"
SILVER_RULES_KEY = "silver_listings"
SILVER_DATASET = "listings"
SILVER_TABLE_KEY = "listings_silver"
BRONZE_TABLE_KEY = "bronze"

# Bronze row-quality annotations carried into Silver under their
# documented names (the policy itself stays Bronze's; F09.2 interprets).
BRONZE_QUALITY_COLUMNS = ("_quality_status", "_quality_reason")

# The observed landed detailed-listings header (90 columns, Toronto
# 2026-09-16), verified column-by-column against both the source-file
# manifest fingerprint and the Bronze table schema. A Bronze slice
# must carry exactly these source columns plus the quality and
# provenance annotations; a future source file that evolves the header
# fails loudly here instead of being silently projected away - the
# contract accounting is then updated deliberately.
DETAILED_LISTINGS_SOURCE_COLUMNS = (
    "id",
    "listing_url",
    "scrape_id",
    "last_scraped",
    "source",
    "name",
    "description",
    "neighborhood_overview",
    "picture_url",
    "host_id",
    "host_url",
    "host_profile_id",
    "host_profile_url",
    "host_name",
    "host_since",
    "hosts_time_as_user_years",
    "hosts_time_as_user_months",
    "hosts_time_as_host_years",
    "hosts_time_as_host_months",
    "host_location",
    "host_about",
    "host_response_time",
    "host_response_rate",
    "host_acceptance_rate",
    "host_is_superhost",
    "host_thumbnail_url",
    "host_picture_url",
    "host_neighbourhood",
    "host_listings_count",
    "host_total_listings_count",
    "host_verifications",
    "host_has_profile_pic",
    "host_identity_verified",
    "neighbourhood",
    "neighbourhood_cleansed",
    "neighbourhood_group_cleansed",
    "latitude",
    "longitude",
    "property_type",
    "room_type",
    "accommodates",
    "bathrooms",
    "bathrooms_text",
    "bedrooms",
    "beds",
    "amenities",
    "price",
    "price_quote_checkin_date",
    "price_quote_checkout_date",
    "price_quote_total_price",
    "price_quote_price_per_night",
    "price_quote_raw",
    "minimum_nights",
    "maximum_nights",
    "minimum_minimum_nights",
    "maximum_minimum_nights",
    "minimum_maximum_nights",
    "maximum_maximum_nights",
    "minimum_nights_avg_ntm",
    "maximum_nights_avg_ntm",
    "calendar_updated",
    "has_availability",
    "availability_30",
    "availability_60",
    "availability_90",
    "availability_365",
    "calendar_last_scraped",
    "number_of_reviews",
    "number_of_reviews_ltm",
    "number_of_reviews_l30d",
    "availability_eoy",
    "number_of_reviews_ly",
    "estimated_occupancy_l365d",
    "estimated_revenue_l365d",
    "first_review",
    "last_review",
    "review_scores_rating",
    "review_scores_accuracy",
    "review_scores_cleanliness",
    "review_scores_checkin",
    "review_scores_communication",
    "review_scores_location",
    "review_scores_value",
    "license",
    "instant_bookable",
    "calculated_host_listings_count",
    "calculated_host_listings_count_entire_homes",
    "calculated_host_listings_count_private_rooms",
    "calculated_host_listings_count_shared_rooms",
    "reviews_per_month",
)

# Contract keys a column entry may use to name its input: `source`
# names a Bronze column; `from` marks a transformation-derived column
# (registry currency, the normalization-issues outcome). The shared
# value sets live in src.quality.config_validation so the validator
# and this module enforce one definition.


def load_silver_rules(repo_root_dir: Any = None) -> dict[str, Any]:
    """Load and structurally check the listings Silver contract rules."""
    contract = load_contract((repo_root_dir or repo_root()) / SILVER_CONTRACT_PATH)
    rules = get_table_rules(contract, SILVER_RULES_KEY)
    column_specs(rules)
    return rules


def column_specs(rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the contract's column list in declared order, validated.

    Pure and CI-safe: every entry must declare a unique name, exactly
    one input (``source`` Bronze column or ``from`` derivation), a
    supported type and a nullable flag. Fails loudly on a malformed
    contract instead of at Spark time.
    """
    from src.quality.config_validation import (
        SILVER_COLUMN_FROM_VALUES,
        SILVER_COLUMN_PARSE_VALUES,
        SILVER_REGISTRY_KEY_VALUES,
        is_supported_column_type,
    )

    raw_columns = rules.get("columns")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise ValueError("silver contract: 'columns' must be a non-empty list")

    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in raw_columns:
        if not isinstance(entry, dict):
            raise TypeError(
                f"silver contract column entry must be a mapping: {entry!r}"
            )
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"silver contract column needs a non-empty name: {entry!r}"
            )
        if name in seen:
            raise ValueError(f"silver contract column declared twice: {name!r}")
        seen.add(name)

        has_source = isinstance(entry.get("source"), str) and bool(
            entry["source"].strip()
        )
        has_from = isinstance(entry.get("from"), str) and bool(entry["from"].strip())
        if has_source == has_from:  # exactly one input
            raise ValueError(
                f"silver contract column {name!r} must declare exactly one of "
                "'source' (Bronze column) or 'from' (derived input)"
            )
        if has_from and entry["from"] not in SILVER_COLUMN_FROM_VALUES:
            raise ValueError(
                f"silver contract column {name!r}: unknown 'from' value "
                f"{entry['from']!r}; expected one of "
                f"{sorted(SILVER_COLUMN_FROM_VALUES)}"
            )
        if (
            has_from
            and entry["from"] == "city_registry"
            and entry.get("registry_key") not in SILVER_REGISTRY_KEY_VALUES
        ):
            raise ValueError(
                f"silver contract column {name!r}: city_registry columns "
                "must declare registry_key one of "
                f"{sorted(SILVER_REGISTRY_KEY_VALUES)}"
            )
        if has_from and entry["from"] == "amenity_search":
            if entry.get("type") != "boolean":
                raise ValueError(
                    f"silver contract column {name!r}: amenity_search "
                    "columns must be boolean"
                )
            patterns = entry.get("patterns")
            if (
                not isinstance(patterns, list)
                or not patterns
                or any(
                    not isinstance(pattern, str) or not pattern.strip()
                    for pattern in patterns
                )
            ):
                raise ValueError(
                    f"silver contract column {name!r}: amenity_search "
                    "columns need a non-empty 'patterns' list of non-blank "
                    "strings"
                )

        column_type = entry.get("type")
        if not isinstance(column_type, str) or not is_supported_column_type(
            column_type
        ):
            raise ValueError(
                f"silver contract column {name!r}: unsupported type {column_type!r}"
            )

        parse = entry.get("parse")
        if parse is not None and (
            not isinstance(parse, str) or parse not in SILVER_COLUMN_PARSE_VALUES
        ):
            raise ValueError(
                f"silver contract column {name!r}: unknown parse marker {parse!r}; "
                f"expected one of {sorted(SILVER_COLUMN_PARSE_VALUES)}"
            )

        if not isinstance(entry.get("nullable"), bool):
            raise TypeError(
                f"silver contract column {name!r}: 'nullable' must be boolean"
            )

        specs.append(entry)

    issues_column = rules.get("normalization", {}).get("issues_column")
    if issues_column not in seen:
        raise ValueError(
            f"silver contract: normalization.issues_column {issues_column!r} "
            "must be declared among the columns"
        )
    return specs


def expected_bronze_columns() -> tuple[str, ...]:
    """The exact column set a detailed-listings Bronze slice must carry."""
    return (
        *DETAILED_LISTINGS_SOURCE_COLUMNS,
        *BRONZE_QUALITY_COLUMNS,
        *PROVENANCE_COLUMNS,
    )


def _sql_string_literal(value: str) -> str:
    """Escape a value for a single-quoted SQL string literal."""
    return value.replace("'", "''")


def _sql_value(source_column: str, parse: str | None) -> str:
    """Return the SQL expression cleaning one raw Bronze value.

    Trimmed, blank-to-null; `money` strips the currency symbol and
    thousands separators; `percent` strips the '%'.
    """
    ref = f"`{source_column}`"
    cleaned = f"nullif(trim({ref}), '')"
    if parse == "money":
        # '[$]' (character class) avoids backslash escaping: a bare '$'
        # in a SQL string literal is the regex end-of-string anchor, and
        # a '\\$' literal is fragile across SQL escape handling.
        return (
            f"nullif(regexp_replace(regexp_replace(trim({ref}), '[$]', ''), "
            "',', ''), '')"
        )
    if parse == "percent":
        return f"nullif(regexp_replace(trim({ref}), '%', ''), '')"
    return cleaned


def normalize_listings_bronze(
    bronze_df,
    rules: dict[str, Any],
    currency: str,
    country_code: str = "",
):
    """Project one Bronze slice into the documented Silver shape.

    Contract-driven: every column expression comes from the Silver
    contract (name, source, type, parse marker), never a hard-coded
    list. Rows are never filtered or dropped; conversion failures
    become null values plus ``normalization_issues`` entries for
    F09.2 to classify.
    """
    from pyspark.sql import functions as F

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency is required to normalize listings Silver")
    if not isinstance(country_code, str) or not country_code.strip():
        raise ValueError("country_code is required to normalize listings Silver")

    specs = column_specs(rules)

    expected = set(expected_bronze_columns())
    actual = set(bronze_df.columns)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            "Bronze slice does not match the documented detailed-listings "
            f"schema; missing: {missing}; unexpected: {extra}. Update the "
            "Silver contract accounting deliberately, never silently."
        )

    selects = []
    issue_whens = []
    for spec in specs:
        name = spec["name"]
        column_type = spec["type"]
        parse = spec.get("parse")
        derived_from = spec.get("from")

        if derived_from == "city_registry":
            registry_values = {
                "currency": currency,
                "country_code": country_code,
            }
            registry_key = spec["registry_key"]
            value = registry_values[registry_key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"registry value {registry_key!r} is required to "
                    "normalize listings Silver"
                )
            selects.append(F.lit(value).alias(name))
            continue
        if derived_from == "normalization":
            # The issues column is appended after every real column.
            continue

        if derived_from == "amenity_search":
            # Recall-oriented fuzzy search over the amenities JSON array
            # and the free-text description: lowercased substring match
            # against the contract-declared patterns, after stripping
            # the contract-declared substring traps (e.g. 'washer'
            # hiding inside 'Dishwasher'). true on any match; false when
            # at least one input was searched and nothing matched; null
            # only when both inputs are null/blank.
            haystacks = [
                "lower(coalesce(`amenities`, ''))",
                "lower(coalesce(`description`, ''))",
            ]
            for trap in spec.get("remove_patterns", []):
                escaped = _sql_string_literal(trap)
                haystacks = [
                    f"replace({haystack}, '{escaped}', '')" for haystack in haystacks
                ]
            searched = " or ".join(
                f"nullif({haystack}, '') is not null" for haystack in haystacks
            )
            matched = " or ".join(
                f"instr({haystack}, '{_sql_string_literal(pattern)}') > 0"
                for haystack in haystacks
                for pattern in spec["patterns"]
            )
            selects.append(
                F.expr(
                    f"case when not ({searched}) then null "
                    f"when {matched} then true else false end"
                ).alias(name)
            )
            continue

        source_column = spec["source"]
        raw = F.col(source_column)
        raw_nonblank = raw.isNotNull() & (F.trim(raw) != "")

        if column_type == "string":
            selects.append(F.expr(f"{_sql_value(source_column, parse)}").alias(name))
            continue

        if column_type == "boolean":
            parsed = (
                F.when(F.trim(raw) == "t", F.lit(True))
                .when(F.trim(raw) == "f", F.lit(False))
                .otherwise(F.lit(None).cast("boolean"))
            )
        else:
            # try_cast: null on malformed values or overflow, never an
            # ANSI-mode cast failure - the F09.1 no-crash guarantee.
            selects_expr = _sql_value(source_column, parse)
            parsed = F.expr(f"try_cast({selects_expr} as {column_type})")

        selects.append(parsed.alias(name))
        issue_whens.append(
            F.when(raw_nonblank & parsed.isNull(), F.lit(name)).otherwise(
                F.lit(None).cast("string")
            )
        )

    issues_column = rules["normalization"]["issues_column"]
    selects.append(
        F.filter(F.array(*issue_whens), lambda issue: issue.isNotNull()).alias(
            issues_column
        )
    )

    return bronze_df.select(*selects)


def resolve_silver_slice_identity(
    project_config: Any,
    registry: Any,
    ingestion_rows: list[dict[str, Any]],
    city_id: str,
    dataset: str = SILVER_DATASET,
    source_file_id: str | None = None,
) -> dict[str, str]:
    """Return the exact Bronze slice identity for a Silver run (pure).

    Bounds first: the city/dataset slice must be part of the bounded
    registry grid (enabled city, registered dataset). The identity
    then comes from the unified ingestion manifest's successful Bronze
    runs - the latest by completed_at_utc, or the explicit
    ``source_file_id`` override (the Bronze notebook convention for
    selecting exact landed bytes). Legacy source-manifest rows carry no
    dataset tag, so the manifest's run history is the evidence-backed
    path that can see the real slices (F09.1 design decision).
    """
    if not isinstance(city_id, str) or not city_id.strip():
        raise ValueError("city_id is required to resolve the Silver slice")

    grid = {
        (row["city_id"], row["dataset"])
        for row in list_city_datasets(project_config, registry)
    }
    if (city_id, dataset) not in grid:
        raise ValueError(
            f"{city_id}/{dataset} is not a registered, enabled city/dataset "
            "slice; register it in the city registry and project.yml first"
        )

    matching = [
        row
        for row in ingestion_rows
        if row.get("city") == city_id and row.get("dataset") == dataset
    ]
    successful = [
        row
        for row in matching
        if row.get("status") == "success"
        and isinstance(row.get("source_file_id"), str)
        and row["source_file_id"].strip()
        and isinstance(row.get("snapshot_date"), str)
        and row["snapshot_date"].strip()
    ]
    if source_file_id is not None:
        if not isinstance(source_file_id, str) or not source_file_id.strip():
            raise ValueError("source_file_id must be a non-empty string when given")
        successful = [
            row for row in successful if row["source_file_id"] == source_file_id
        ]
        if not successful:
            raise ValueError(
                f"{city_id}/{dataset}: no successful Bronze run recorded for "
                f"source_file_id {source_file_id!r}; run the Bronze flow first"
            )
    if not successful:
        raise ValueError(
            f"{city_id}/{dataset}: no successful Bronze run recorded in the "
            "ingestion manifest; run the Bronze flow first"
        )

    latest = max(successful, key=lambda row: row.get("completed_at_utc") or "")
    return {
        "city_id": city_id,
        "dataset": dataset,
        "snapshot_date": latest["snapshot_date"],
        "source_file_id": latest["source_file_id"],
    }


def run_listings_silver_transform(
    spark,
    run_mode: str = "test",
    city_id: str = "toronto",
    source_file_id: str | None = None,
) -> dict[str, Any]:
    """Run the complete listings Bronze-to-Silver normalization (F09.1).

    Resolves every destination through the environment resolver
    (test mode can only touch ``trippilot_test``), selects the Bronze
    slice by landed identity, normalizes it under the Silver contract
    and atomically replaces the matching city/snapshot Silver slice.
    Returns a summary dict with the resolved identity, destinations,
    currency and row counts. Rerunning the same slice replaces it with
    identical data - the output is deterministic (no new timestamps).
    """
    from pyspark.sql import functions as F

    run_mode = validate_run_mode(run_mode)
    silver_table = validate_destination(
        resolve_table(SILVER_TABLE_KEY, run_mode), run_mode
    )
    bronze_table = resolve_table(BRONZE_TABLE_KEY, run_mode)
    ingestion_manifest_table = resolve_table("ingestion_manifest", run_mode)
    source_manifest_table = resolve_table("source_manifest", run_mode)

    root = repo_root()
    rules = load_silver_rules(root)

    registry = load_city_registry(root)
    project_config = load_project_config(root)
    city = get_city(registry, city_id)
    if city is None or city.get("enabled") is not True:
        raise ValueError(
            f"city {city_id!r} is not registered and enabled in the city registry"
        )
    currency = city.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError(f"city registry entry {city_id!r} has no currency")
    country_code = city.get("country_code")
    if not isinstance(country_code, str) or not country_code.strip():
        raise ValueError(f"city registry entry {city_id!r} has no country_code")

    ingestion_store = IngestionManifestStore(ingestion_manifest_table, spark=spark)
    ingestion_rows = ingestion_store.list_for_city_dataset(city_id, SILVER_DATASET)
    identity = resolve_silver_slice_identity(
        project_config,
        registry,
        ingestion_rows,
        city_id,
        SILVER_DATASET,
        source_file_id,
    )

    # Tie the slice to the immutable landed bytes before reading it.
    source_record = ManifestStore(source_manifest_table, spark=spark).read_landed(
        identity["source_file_id"]
    )
    verify_landed_record(source_record)

    print(f"Bronze source:   {bronze_table}")
    print(
        f"Selected slice:  {identity['city_id']} / {identity['snapshot_date']} "
        f"/ {identity['source_file_id']}"
    )
    print(f"Silver target:   {silver_table}")
    print(f"Currency:        {currency} (city registry; no conversion)")
    print(f"Country:         {country_code} (city registry)")

    bronze_df = (
        spark.table(bronze_table)
        .where(F.col("_city") == identity["city_id"])
        .where(F.col("_snapshot_date") == identity["snapshot_date"])
        .where(F.col("_source_file_id") == identity["source_file_id"])
    )
    silver_df = normalize_listings_bronze(
        bronze_df, rules, currency=currency, country_code=country_code
    )

    bronze_rows = bronze_df.count()
    if bronze_rows == 0:
        raise ValueError(
            "The selected Bronze slice contains no rows; the ingestion "
            "manifest and the Bronze table disagree - investigate before "
            "replacing any Silver slice."
        )
    silver_rows = silver_df.count()
    if silver_rows != bronze_rows:
        raise AssertionError(
            f"Normalization must preserve every row ({bronze_rows} in, "
            f"{silver_rows} out) - F09.1 never filters or drops rows."
        )

    write_snapshot(
        silver_df,
        silver_table,
        identity["city_id"],
        identity["snapshot_date"],
        "city_id",
        "snapshot_date",
    )

    print(f"Wrote {silver_rows} rows to {silver_table} (slice replaced atomically).")

    return {
        "run_mode": run_mode,
        "bronze_table": bronze_table,
        "silver_table": silver_table,
        **identity,
        "currency": currency,
        "bronze_rows": bronze_rows,
        "silver_rows": silver_rows,
        "silver_df": silver_df,
    }
