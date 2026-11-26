"""Tests for the contract-driven listings Silver transformation (F09.1).

Two layers, mirroring tests for the Bronze flow:

* Pure, CI-safe tests on the real contract file and helpers - the
  100-column accounting against the observed detailed-listings
  header (every source column mapped or excluded, nothing dropped
  silently), the lineage maps, the parse policy, the slice-identity
  resolution (latest successful Bronze run, explicit source_file_id,
  loud failures otherwise), and the contract-structure gate.
* Spark behavior tests, skipped without pyspark (CI has no Spark):
  the normalization is exercised on a synthetic Bronze slice built
  with the exact documented schema - representative values parse
  correctly, malformed values become null plus exact
  normalization_issues entries, blanks become null without issues,
  Bronze-invalid rows survive, schema drift fails loudly, and the
  output schema matches the contract types column for column.
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

start = Path.cwd().resolve()
ROOT = next(
    (
        p
        for p in [start, *start.parents]
        if (p / "src").is_dir() and (p / "config/project.yml").is_file()
    ),
    None,
)
if ROOT is None:
    raise RuntimeError(
        "Cannot locate repository root. Open this notebook inside the Databricks Git folder."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print("Repository root:", ROOT)

import pytest

from src.airbnb.listings_silver import (
    BRONZE_QUALITY_COLUMNS,
    DETAILED_LISTINGS_SOURCE_COLUMNS,
    SILVER_CONTRACT_PATH,
    SILVER_DATASET,
    column_specs,
    expected_bronze_columns,
    load_silver_rules,
    normalize_listings_bronze,
    resolve_silver_slice_identity,
)
from src.common.control_plane import load_city_registry, load_project_config
from src.common.provenance import PROVENANCE_COLUMNS

RULES = load_silver_rules(ROOT)
SPECS = column_specs(RULES)
REGISTRY = load_city_registry(ROOT)
PROJECT_CONFIG = load_project_config(ROOT)


# ---------------------------------------------------------------------
# Pure contract accounting (CI-safe)
# ---------------------------------------------------------------------


def test_silver_contract_file_is_the_expected_one():
    assert SILVER_CONTRACT_PATH == "contracts/airbnb/silver_listings.yml"
    assert (ROOT / SILVER_CONTRACT_PATH).is_file()


def test_contract_declares_100_unique_columns():
    names = [spec["name"] for spec in SPECS]
    assert len(names) == 100
    assert len(set(names)) == 100


def test_expected_bronze_columns_are_the_documented_100():
    columns = expected_bronze_columns()
    assert len(columns) == 100
    assert len(set(columns)) == 100
    assert set(DETAILED_LISTINGS_SOURCE_COLUMNS) == {
        column for column in columns if not column.startswith("_")
    }
    assert set(PROVENANCE_COLUMNS) | set(BRONZE_QUALITY_COLUMNS) == {
        column for column in columns if column.startswith("_")
    }


def test_contract_accounts_for_every_source_column():
    # Every one of the 90 observed source columns is either mapped to
    # a Silver column or explicitly excluded with a reason - nothing
    # is dropped silently. And nothing is mapped from outside the
    # documented Bronze schema.
    header = set(DETAILED_LISTINGS_SOURCE_COLUMNS)
    technical = set(PROVENANCE_COLUMNS) | set(BRONZE_QUALITY_COLUMNS)
    sourced = {spec["source"] for spec in SPECS if "source" in spec}
    excluded = {entry["column"] for entry in RULES["exclusions"]}

    assert excluded <= header
    assert header - excluded <= sourced
    assert (sourced - technical) == (header - excluded)
    assert sourced | excluded == set(expected_bronze_columns())

    for entry in RULES["exclusions"]:
        assert entry["reason"].strip()


def test_deprecated_columns_are_the_only_exclusions():
    assert {entry["column"] for entry in RULES["exclusions"]} == {
        "bathrooms",
        "calendar_updated",
    }


def test_grain_primary_key_and_table():
    assert RULES["version"] == 1
    assert RULES["table"] == "trippilot_dev.silver.airbnb_listings_silver"
    assert RULES["input"] == "bronze_listings"
    assert RULES["write_policy"] == "replace_city_snapshot"
    assert "listing_id" in RULES["grain"]
    assert RULES["primary_key"] == ["city_id", "snapshot_date", "listing_id"]


def test_lineage_maps_are_complete_and_consistent():
    lineage = RULES["lineage"]
    provenance_map = lineage["bronze_provenance_map"]
    quality_map = lineage["bronze_quality_map"]

    assert set(provenance_map) == set(PROVENANCE_COLUMNS)
    assert set(quality_map) == set(BRONZE_QUALITY_COLUMNS)

    spec_by_name = {spec["name"]: spec for spec in SPECS}
    for bronze_column, silver_column in {**provenance_map, **quality_map}.items():
        assert silver_column in spec_by_name
        assert spec_by_name[silver_column]["source"] == bronze_column


def test_identifier_and_count_policy():
    spec_by_source = {spec["source"]: spec for spec in SPECS if "source" in spec}
    for identifier in ("id", "host_id", "scrape_id"):
        assert spec_by_source[identifier]["type"] == "string"
    for count_column in (
        "number_of_reviews",
        "host_listings_count",
        "calculated_host_listings_count",
    ):
        assert spec_by_source[count_column]["type"] == "int"


def test_price_policy_is_cad_decimal_with_money_parse():
    spec_by_name = {spec["name"]: spec for spec in SPECS}
    price = spec_by_name["price"]
    assert price["type"] == "decimal(10,2)"
    assert price["parse"] == "money"

    for rate in ("host_response_rate", "host_acceptance_rate"):
        spec = spec_by_name[rate]
        assert spec["type"] == "int"
        assert spec["parse"] == "percent"

    currency = spec_by_name["currency"]
    assert currency["from"] == "city_registry"
    assert currency["nullable"] is False


def test_quote_fields_stay_verbatim_strings():
    spec_by_name = {spec["name"]: spec for spec in SPECS}
    for name in (
        "price_quote_total_price",
        "price_quote_price_per_night",
        "price_quote_raw",
    ):
        assert spec_by_name[name]["type"] == "string"
        assert "parse" not in spec_by_name[name]


def test_issues_column_is_the_only_normalization_derivation():
    derived = [spec for spec in SPECS if "from" in spec]
    assert {spec["name"] for spec in derived} == {
        "currency",
        "normalization_issues",
    }
    issues = next(spec for spec in derived if spec["name"] == "normalization_issues")
    assert issues["type"] == "array<string>"
    assert issues["nullable"] is False
    assert RULES["normalization"]["issues_column"] == "normalization_issues"


# ---------------------------------------------------------------------
# Contract structure gate (runtime raises, mirrors the validator)
# ---------------------------------------------------------------------


def _minimal_rules():
    return {
        "columns": [
            {"name": "listing_id", "source": "id", "type": "string", "nullable": False},
            {
                "name": "normalization_issues",
                "from": "normalization",
                "type": "array<string>",
                "nullable": False,
            },
        ],
        "normalization": {"issues_column": "normalization_issues"},
    }


def test_column_specs_reject_duplicate_names():
    rules = _minimal_rules()
    rules["columns"].append(dict(rules["columns"][0]))
    with pytest.raises(ValueError, match="twice"):
        column_specs(rules)


def test_column_specs_reject_both_inputs():
    rules = _minimal_rules()
    rules["columns"][0]["from"] = "city_registry"
    with pytest.raises(ValueError, match="exactly one"):
        column_specs(rules)


def test_column_specs_reject_neither_input():
    rules = _minimal_rules()
    del rules["columns"][0]["source"]
    with pytest.raises(ValueError, match="exactly one"):
        column_specs(rules)


def test_column_specs_reject_unknown_from_value():
    rules = _minimal_rules()
    rules["columns"][1]["from"] = "magic"
    with pytest.raises(ValueError, match="'from'"):
        column_specs(rules)


def test_column_specs_reject_unknown_parse_marker():
    rules = _minimal_rules()
    rules["columns"][0]["parse"] = "fraction"
    with pytest.raises(ValueError, match="parse marker"):
        column_specs(rules)


def test_column_specs_reject_unsupported_type():
    rules = _minimal_rules()
    rules["columns"][0]["type"] = "float"
    with pytest.raises(ValueError, match="unsupported type"):
        column_specs(rules)


def test_column_specs_require_nullable_flag():
    rules = _minimal_rules()
    del rules["columns"][0]["nullable"]
    with pytest.raises(TypeError, match="nullable"):
        column_specs(rules)


def test_column_specs_require_declared_issues_column():
    rules = _minimal_rules()
    rules["normalization"]["issues_column"] = "issues"
    with pytest.raises(ValueError, match="issues_column"):
        column_specs(rules)


# ---------------------------------------------------------------------
# Silver slice identity resolution (pure)
# ---------------------------------------------------------------------


def _ingestion_row(**overrides):
    row = {
        "city": "toronto",
        "dataset": SILVER_DATASET,
        "status": "success",
        "source_file_id": "sfid-1",
        "snapshot_date": "2026-09-16",
        "completed_at_utc": "2026-11-24T01:00:00+00:00",
    }
    row.update(overrides)
    return row


def _resolve(rows, **kwargs):
    return resolve_silver_slice_identity(
        PROJECT_CONFIG, REGISTRY, rows, kwargs.pop("city_id", "toronto"), **kwargs
    )


def test_identity_picks_latest_successful_run():
    identity = _resolve(
        [
            _ingestion_row(),
            _ingestion_row(
                source_file_id="sfid-2",
                snapshot_date="2026-10-15",
                completed_at_utc="2026-11-25T02:00:00+00:00",
            ),
            _ingestion_row(
                status="failed",
                source_file_id="sfid-3",
                snapshot_date="2026-10-15",
                completed_at_utc="2026-11-26T03:00:00+00:00",
            ),
        ]
    )
    assert identity == {
        "city_id": "toronto",
        "dataset": "listings",
        "snapshot_date": "2026-10-15",
        "source_file_id": "sfid-2",
    }


def test_identity_explicit_source_file_id_overrides_latest():
    rows = [
        _ingestion_row(),
        _ingestion_row(
            source_file_id="sfid-2",
            snapshot_date="2026-10-15",
            completed_at_utc="2026-11-25T02:00:00+00:00",
        ),
    ]
    identity = _resolve(rows, source_file_id="sfid-1")
    assert identity["source_file_id"] == "sfid-1"
    assert identity["snapshot_date"] == "2026-09-16"


def test_identity_explicit_source_file_id_must_be_a_success():
    rows = [_ingestion_row(status="failed", source_file_id="sfid-9")]
    with pytest.raises(ValueError, match="no successful Bronze run"):
        _resolve(rows, source_file_id="sfid-9")


def test_identity_unknown_source_file_id_raises():
    rows = [_ingestion_row()]
    with pytest.raises(ValueError, match="no successful Bronze run"):
        _resolve(rows, source_file_id="sfid-does-not-exist")


def test_identity_requires_a_successful_run():
    with pytest.raises(ValueError, match="no successful Bronze run"):
        _resolve([])
    with pytest.raises(ValueError, match="no successful Bronze run"):
        _resolve([_ingestion_row(status="failed")])


def test_identity_ignores_incomplete_success_rows():
    rows = [
        _ingestion_row(source_file_id=""),
        _ingestion_row(snapshot_date=None),
        _ingestion_row(
            source_file_id="sfid-2",
            snapshot_date="2026-10-15",
            completed_at_utc="2026-11-25T02:00:00+00:00",
        ),
    ]
    assert _resolve(rows)["source_file_id"] == "sfid-2"


def test_identity_scopes_rows_to_city_and_dataset():
    rows = [
        _ingestion_row(city="montreal", source_file_id="sfid-other"),
        _ingestion_row(dataset="calendar", source_file_id="sfid-other"),
        _ingestion_row(
            source_file_id="sfid-1",
            snapshot_date="2026-09-16",
            completed_at_utc="2026-11-24T01:00:00+00:00",
        ),
    ]
    assert _resolve(rows)["source_file_id"] == "sfid-1"


def test_identity_rejects_unregistered_slice():
    with pytest.raises(ValueError, match="not a registered, enabled city/dataset"):
        _resolve([_ingestion_row()], city_id="nowhere")
    with pytest.raises(ValueError, match="not a registered, enabled city/dataset"):
        _resolve([_ingestion_row()], dataset="not_a_dataset_tag")


def test_identity_requires_city_id():
    with pytest.raises(ValueError, match="city_id"):
        resolve_silver_slice_identity(PROJECT_CONFIG, REGISTRY, [], "")


# ---------------------------------------------------------------------
# Spark behavior (skipped without pyspark; run in-session)
# ---------------------------------------------------------------------


def _spark():
    from pyspark.errors.exceptions.base import PySparkValueError
    from pyspark.sql import SparkSession

    try:
        return SparkSession.builder.getOrCreate()
    except PySparkValueError as exc:
        # No live Spark Connect session in this process (subprocess run
        # or CI): the pyspark wheel is importable but a session needs
        # the in-session REPL. Skip, never fail - the behavior tests run
        # in-session where a session is available.
        pytest.skip(f"no live Spark session: {exc}")


def _bronze_slice(spark, rows):
    from pyspark.sql.types import StringType, StructField, StructType

    columns = list(expected_bronze_columns())
    schema = StructType([StructField(name, StringType(), True) for name in columns])
    data = [tuple(row.get(column) for column in columns) for row in rows]
    return spark.createDataFrame(data, schema)


def _base_row(**overrides):
    row = {column: None for column in expected_bronze_columns()}
    row.update(
        {
            "id": "12345",
            "listing_url": "https://airbnb.com/rooms/12345",
            "scrape_id": "20260916052317",
            "last_scraped": "2026-09-14",
            "source": "previous scrape",
            "name": "Cozy downtown loft",
            "host_id": "98765",
            "host_since": "2018-03-01",
            "host_response_rate": "95%",
            "host_acceptance_rate": "100%",
            "host_is_superhost": "t",
            "host_has_profile_pic": "t",
            "host_identity_verified": "f",
            "latitude": "43.705150",
            "longitude": "-79.407900",
            "accommodates": "4",
            "bedrooms": "2",
            "beds": "3",
            "amenities": '["Wifi", "Kitchen"]',
            "price": "$1,234.50",
            "price_quote_checkin_date": "2026-11-20",
            "price_quote_checkout_date": "2026-11-27",
            "price_quote_total_price": "1234.5000000000001",
            "price_quote_price_per_night": "176.3571428571",
            "price_quote_raw": '{"currency": "CAD"}',
            "minimum_nights": "2",
            "maximum_nights": "1125",
            "minimum_nights_avg_ntm": "2.5",
            "has_availability": "t",
            "availability_30": "20",
            "availability_365": "123",
            "number_of_reviews": "57",
            "first_review": "2024-01-15",
            "last_review": "2026-09-10",
            "review_scores_rating": "4.92",
            "reviews_per_month": "0.75",
            "license": "STR-2024-0001",
            "instant_bookable": "f",
            "calculated_host_listings_count": "2",
            "_source": "insideairbnb",
            "_city": "toronto",
            "_snapshot_date": "2026-09-16",
            "_raw_path": (
                "/Volumes/trippilot_dev/bronze/landed/listings__sfid-1.csv.gz"
            ),
            "_run_id": "run-xyz",
            "_ingested_at_utc": "2026-11-24T00:35:28.959492+00:00",
            "_source_file_id": "sfid-1",
            "_file_hash_sha256": "deadbeef",
            "_quality_status": "valid",
        }
    )
    row.update(overrides)
    return row


def _normalize(spark, rows):
    bronze = _bronze_slice(spark, rows)
    return normalize_listings_bronze(bronze, RULES, currency="CAD")


def test_normalize_preserves_rows_and_column_order():
    pytest.importorskip("pyspark")
    silver = _normalize(_spark(), [_base_row(), _base_row(id="67890")])

    assert silver.count() == 2
    assert silver.columns == [spec["name"] for spec in SPECS]


def test_normalize_schema_matches_contract_types():
    pytest.importorskip("pyspark")
    from pyspark.sql.types import (
        ArrayType,
        BooleanType,
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        TimestampType,
    )

    def spark_type(declared):
        if declared == "string":
            return StringType()
        if declared == "boolean":
            return BooleanType()
        if declared == "date":
            return DateType()
        if declared == "timestamp":
            return TimestampType()
        if declared == "int":
            return IntegerType()
        if declared == "array<string>":
            return ArrayType(StringType())
        precision, scale = declared[len("decimal(") : -1].split(",")
        return DecimalType(int(precision), int(scale))

    silver = _normalize(_spark(), [_base_row()])
    schema = {field.name: field.dataType for field in silver.schema.fields}

    for spec in SPECS:
        assert schema[spec["name"]] == spark_type(spec["type"]), spec["name"]


def test_normalize_parses_representative_values():
    pytest.importorskip("pyspark")
    silver = _normalize(_spark(), [_base_row()])
    row = silver.collect()[0].asDict()

    # money, percent, boolean, date, decimal, int
    assert row["price"] == Decimal("1234.50")
    assert row["host_response_rate"] == 95
    assert row["host_acceptance_rate"] == 100
    assert row["host_is_superhost"] is True
    assert row["host_has_profile_pic"] is True
    assert row["host_identity_verified"] is False
    assert row["instant_bookable"] is False
    assert row["last_scraped"] == date(2026, 9, 14)
    assert row["first_review"] == date(2024, 1, 15)
    assert row["last_review"] == date(2026, 9, 10)
    assert row["latitude"] == Decimal("43.705150")
    assert row["longitude"] == Decimal("-79.407900")
    assert row["review_scores_rating"] == Decimal("4.92")
    assert row["reviews_per_month"] == Decimal("0.75")
    assert row["minimum_nights_avg_ntm"] == Decimal("2.50")
    assert row["accommodates"] == 4
    assert row["number_of_reviews"] == 57

    # registry currency, never parsed from the source
    assert row["currency"] == "CAD"

    # verbatim quote strings
    assert row["price_quote_total_price"] == "1234.5000000000001"
    assert row["price_quote_raw"] == '{"currency": "CAD"}'

    # lineage renames
    assert row["source_name"] == "insideairbnb"
    assert row["city_id"] == "toronto"
    assert row["snapshot_date"] == "2026-09-16"
    assert row["source_run_id"] == "run-xyz"
    assert row["source_file_id"] == "sfid-1"
    assert row["source_file_hash_sha256"] == "deadbeef"
    assert row["source_raw_path"].endswith("listings__sfid-1.csv.gz")
    assert row["source_ingested_at_utc"] is not None
    assert str(row["source_ingested_at_utc"]).startswith("2026-11-24")

    # renamed source-data column
    assert row["scrape_source"] == "previous scrape"

    assert row["normalization_issues"] == []


def test_normalize_malformed_values_become_null_and_issues():
    pytest.importorskip("pyspark")
    silver = _normalize(
        _spark(),
        [
            _base_row(
                id="bad-row",
                host_response_rate="abc%",
                host_is_superhost="x",
                latitude="9.9.9",
                price="$",
                minimum_nights="three",
                last_review="16-09-2026",
            )
        ],
    )
    row = silver.collect()[0].asDict()

    # failed parses become null; the batch does not crash
    assert row["host_response_rate"] is None
    assert row["host_is_superhost"] is None
    assert row["latitude"] is None
    assert row["price"] is None
    assert row["minimum_nights"] is None
    assert row["last_review"] is None

    # issues name exactly the failed columns, in contract order
    assert row["normalization_issues"] == [
        "host_response_rate",
        "host_is_superhost",
        "latitude",
        "price",
        "minimum_nights",
        "last_review",
    ]


def test_normalize_overflow_decimals_null_and_issue():
    pytest.importorskip("pyspark")
    silver = _normalize(
        _spark(),
        [_base_row(id="overflow", price="$99999999999999.99")],
    )
    row = silver.collect()[0].asDict()
    assert row["price"] is None
    assert row["normalization_issues"] == ["price"]


def test_normalize_blank_values_become_null_without_issues():
    pytest.importorskip("pyspark")
    silver = _normalize(
        _spark(),
        [
            _base_row(
                id="blank-row",
                price="",
                host_response_rate="",
                host_is_superhost=" ",
                last_review="",
                latitude="   ",
                description="",
            )
        ],
    )
    row = silver.collect()[0].asDict()

    assert row["price"] is None
    assert row["host_response_rate"] is None
    assert row["host_is_superhost"] is None
    assert row["last_review"] is None
    assert row["latitude"] is None
    assert row["description"] is None
    assert row["normalization_issues"] == []


def test_normalize_preserves_bronze_invalid_rows():
    pytest.importorskip("pyspark")
    silver = _normalize(
        _spark(),
        [
            _base_row(),
            _base_row(
                id="",
                _quality_status="invalid",
                _quality_reason="missing id",
            ),
        ],
    )
    assert silver.count() == 2

    rows = {row["bronze_quality_status"]: row.asDict() for row in silver.collect()}
    invalid = rows["invalid"]
    assert invalid["listing_id"] is None
    assert invalid["bronze_quality_reason"] == "missing id"
    assert invalid["normalization_issues"] == []


def test_normalize_rejects_missing_bronze_column():
    pytest.importorskip("pyspark")
    bronze = _bronze_slice(_spark(), [_base_row()]).drop("beds")
    with pytest.raises(ValueError, match="does not match"):
        normalize_listings_bronze(bronze, RULES, currency="CAD")


def test_normalize_rejects_unexpected_bronze_column():
    pytest.importorskip("pyspark")
    from pyspark.sql import functions as F

    bronze = _bronze_slice(_spark(), [_base_row()]).withColumn("future_col", F.lit("x"))
    with pytest.raises(ValueError, match="does not match"):
        normalize_listings_bronze(bronze, RULES, currency="CAD")


def test_normalize_requires_currency():
    pytest.importorskip("pyspark")
    bronze = _bronze_slice(_spark(), [_base_row()])
    with pytest.raises(ValueError, match="currency"):
        normalize_listings_bronze(bronze, RULES, currency="")
