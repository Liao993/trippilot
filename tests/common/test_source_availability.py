"""Unit tests for the source-asset availability ledger (F07.3-T01).

Pure-Python tests with stub stores: no Spark session, production table,
network or credentials. The YAML contract in
contracts/ops/source_file_availability.yml is cross-checked against
the module's rules so the two can never drift apart.
"""

import sys
from pathlib import Path

import yaml

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

from src.common.source_availability import (
    ALLOWED_AVAILABILITY_STATES,
    AVAILABILITY_FIELDS,
    AvailabilityStore,
    build_availability_id,
    build_available_record,
    build_create_table_sql,
    build_invalid_record,
    build_not_published_record,
    build_upsert_sql,
    validate_availability_record,
)
from src.common.source_manifest import build_source_file_id

TEST_TABLE = "trippilot_dev.ops.source_file_availability_test"

CHECKED_AT = "2026-11-23T12:00:00Z"
EVIDENCE_URL = "https://insideairbnb.com/get-the-data/"

IDENTITY = {
    "source_family": "insideairbnb",
    "source_entity_id": "hamburg",
    "source_version": "2026-10-18",
    "file_type": "geojson",
    "dataset": "neighbourhood_geometry",
}


def _landed_manifest_row(**overrides):
    row = {
        "source_file_id": "e" * 64,
        "source_family": "insideairbnb",
        "source_entity_id": "hamburg",
        "source_version": "2026-10-18",
        "file_type": "geojson",
        "dataset": "neighbourhood_geometry",
        "processing_state": "landed",
        "landing_path": "/Volumes/dev/bronze/x.geojson",
    }
    row.update(overrides)
    return row


class StubManifestStore:
    """Stub with the two read paths the ledger guards rely on."""

    def __init__(self, landed_by_identity=None, rows_by_id=None):
        self.landed_by_identity = landed_by_identity
        self.rows_by_id = rows_by_id or {}

    def read_landed_by_identity(self, family, entity, version, file_type):
        if self.landed_by_identity is None:
            raise ValueError("no landed record")
        return self.landed_by_identity

    def read(self, source_file_id):
        return self.rows_by_id.get(source_file_id)


class StubResult:
    def __init__(self, rows):
        self._rows = rows

    def collect(self):
        return self._rows


class StubSpark:
    def __init__(self, rows=None):
        self.sql_log = []
        self.rows = rows or []

    def sql(self, statement):
        self.sql_log.append(statement)
        return StubResult(self.rows)


def test_availability_id_is_deterministic_and_identity_scoped():
    first = build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
    )
    second = build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
    )

    assert first == second
    assert first != build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "csv", "listings"
    )
    # F08.3: the dataset completes the identity - two assets sharing a
    # file type (listings/calendar/reviews are all csv.gz) stay distinct.
    assert first != build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhoods"
    )


def test_availability_id_can_never_equal_a_manifest_id():
    # The manifest ID canonical string includes the file hash; the
    # ledger ID canonical string ends with a literal availability tag.
    manifest_id = build_source_file_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "f" * 64
    )
    ledger_id = build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
    )

    assert manifest_id != ledger_id


def test_not_published_record_requires_evidence():
    with pytest.raises(ValueError, match="evidence_url is required"):
        build_not_published_record(
            IDENTITY, "", "listing page shows no geojson", CHECKED_AT, "operator"
        )

    with pytest.raises(ValueError, match="evidence_note is required"):
        build_not_published_record(IDENTITY, EVIDENCE_URL, "", CHECKED_AT, "operator")


def test_not_published_record_builds_a_complete_valid_record():
    record = build_not_published_record(
        IDENTITY,
        EVIDENCE_URL,
        "data page lists no neighbourhood geojson",
        CHECKED_AT,
        "operator",
    )

    assert record["availability_state"] == "not_published"
    assert record["landed_source_file_id"] is None
    assert record["availability_id"] == build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
    )
    assert validate_availability_record(record) == []


def test_not_published_is_refused_when_bytes_have_landed():
    store = StubManifestStore(landed_by_identity=_landed_manifest_row())

    with pytest.raises(ValueError, match="Refusing to record not_published"):
        build_not_published_record(
            IDENTITY, EVIDENCE_URL, "page shows nothing", CHECKED_AT, "operator", store
        )


def test_not_published_is_allowed_when_no_landed_record_exists():
    store = StubManifestStore(landed_by_identity=None)

    record = build_not_published_record(
        IDENTITY, EVIDENCE_URL, "page shows nothing", CHECKED_AT, "operator", store
    )

    assert record["availability_state"] == "not_published"


def test_not_published_note_redacts_credentials():
    record = build_not_published_record(
        IDENTITY,
        EVIDENCE_URL,
        "download attempt used token dapi0123456789abcdef0123456789abcd and failed",
        CHECKED_AT,
        "operator",
    )

    assert "dapi0123456789abcdef0123456789abcd" not in record["evidence_note"]
    assert "***REDACTED***" in record["evidence_note"]


def test_invalid_record_requires_evidence():
    with pytest.raises(ValueError, match="evidence_url is required"):
        build_invalid_record(
            IDENTITY, "", "header check failed", CHECKED_AT, "operator"
        )

    with pytest.raises(ValueError, match="evidence_note is required"):
        build_invalid_record(IDENTITY, EVIDENCE_URL, "", CHECKED_AT, "operator")


def test_invalid_record_builds_a_complete_valid_record():
    record = build_invalid_record(
        IDENTITY,
        EVIDENCE_URL,
        "downloaded geojson is not a FeatureCollection; the manifest records "
        "the parse_or_schema failure",
        CHECKED_AT,
        "operator",
    )

    assert record["availability_state"] == "invalid"
    assert record["landed_source_file_id"] is None
    assert record["availability_id"] == build_availability_id(
        "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
    )
    assert validate_availability_record(record) == []


def test_invalid_record_is_allowed_when_bytes_exist():
    # Unlike not_published, an invalid claim is not contradicted by
    # acquired or failed bytes; the failed attempt's history stays in
    # the source manifest, so no landed-refusal guard applies.
    store = StubManifestStore(landed_by_identity=_landed_manifest_row())

    record = build_invalid_record(
        IDENTITY, EVIDENCE_URL, "header check failed", CHECKED_AT, "operator", store
    )

    assert record["availability_state"] == "invalid"


def test_invalid_record_cannot_carry_a_landed_id():
    record = build_invalid_record(
        IDENTITY, EVIDENCE_URL, "header check failed", CHECKED_AT, "operator"
    )
    record["landed_source_file_id"] = "e" * 64

    errors = validate_availability_record(record)

    assert any(
        "landed_source_file_id is not allowed when availability_state is invalid"
        in error
        for error in errors
    )


def test_invalid_is_an_allowed_availability_state():
    assert "invalid" in ALLOWED_AVAILABILITY_STATES


def test_available_record_requires_a_landed_manifest_id():
    with pytest.raises(ValueError, match="landed_source_file_id is required"):
        build_available_record(IDENTITY, "", CHECKED_AT, "operator")


def test_available_record_verifies_the_landed_identity():
    store = StubManifestStore(rows_by_id={"e" * 64: _landed_manifest_row()})

    record = build_available_record(IDENTITY, "e" * 64, CHECKED_AT, "operator", store)

    assert record["availability_state"] == "available"
    assert record["landed_source_file_id"] == "e" * 64
    assert validate_availability_record(record) == []


def test_available_record_rejects_an_unknown_landed_id():
    store = StubManifestStore(rows_by_id={})

    with pytest.raises(ValueError, match="No manifest record found"):
        build_available_record(IDENTITY, "e" * 64, CHECKED_AT, "operator", store)


def test_available_record_rejects_a_non_landed_manifest_row():
    store = StubManifestStore(
        rows_by_id={"e" * 64: _landed_manifest_row(processing_state="failed")}
    )

    with pytest.raises(ValueError, match="not landed"):
        build_available_record(IDENTITY, "e" * 64, CHECKED_AT, "operator", store)


def test_available_record_rejects_an_identity_mismatch():
    wrong_identity = dict(IDENTITY, file_type="csv")
    store = StubManifestStore(rows_by_id={"e" * 64: _landed_manifest_row()})

    with pytest.raises(ValueError, match="identity does not match"):
        build_available_record(wrong_identity, "e" * 64, CHECKED_AT, "operator", store)


def test_available_record_accepts_an_untagged_legacy_landed_row():
    # A pre-F08.4 landed manifest row carries no dataset tag; the
    # identity comparison must skip the dataset only for that legacy
    # shape, not weaken the other identity fields.
    store = StubManifestStore(rows_by_id={"e" * 64: _landed_manifest_row(dataset=None)})

    record = build_available_record(IDENTITY, "e" * 64, CHECKED_AT, "operator", store)

    assert record["availability_state"] == "available"


def test_available_record_rejects_a_dataset_mismatch():
    store = StubManifestStore(
        rows_by_id={"e" * 64: _landed_manifest_row(dataset="neighbourhoods")}
    )

    with pytest.raises(ValueError, match="identity does not match"):
        build_available_record(IDENTITY, "e" * 64, CHECKED_AT, "operator", store)


def test_validation_rejects_bad_states_types_and_timestamps():
    base = {
        "availability_id": build_availability_id(
            "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
        ),
        "source_family": "insideairbnb",
        "source_entity_id": "hamburg",
        "source_version": "2026-10-18",
        "file_type": "geojson",
        "dataset": "neighbourhood_geometry",
        "availability_state": "not_published",
        "evidence_url": EVIDENCE_URL,
        "evidence_note": "checked manually",
        "landed_source_file_id": None,
        "checked_at_utc": CHECKED_AT,
        "recorded_by": "operator",
        "run_id": "run-1",
    }

    assert validate_availability_record(base) == []

    for field, bad, message in (
        ("file_type", "exe", "Unsupported file type"),
        ("availability_state", "maybe", "Invalid availability_state"),
        ("checked_at_utc", "2026-11-23 12:00", "checked_at_utc"),
        ("evidence_url", "ftp://example.com", "evidence_url must start with"),
        ("availability_id", "f" * 64, "availability_id must equal"),
        ("landed_source_file_id", "zz" * 32, "landed_source_file_id must be"),
        ("dataset", "", "Missing required availability field: dataset"),
    ):
        record = dict(base)
        record[field] = bad
        errors = validate_availability_record(record)
        assert any(message in e for e in errors), (field, errors)


def test_not_published_cannot_carry_a_landed_id():
    record = {
        "availability_id": build_availability_id(
            "insideairbnb", "hamburg", "2026-10-18", "geojson", "neighbourhood_geometry"
        ),
        "source_family": "insideairbnb",
        "source_entity_id": "hamburg",
        "source_version": "2026-10-18",
        "file_type": "geojson",
        "dataset": "neighbourhood_geometry",
        "availability_state": "not_published",
        "evidence_url": EVIDENCE_URL,
        "evidence_note": "checked manually",
        "landed_source_file_id": "e" * 64,
        "checked_at_utc": CHECKED_AT,
        "recorded_by": "operator",
        "run_id": "run-1",
    }

    errors = validate_availability_record(record)

    assert any("landed_source_file_id is not allowed" in e for e in errors)


def test_create_table_sql_matches_the_contract_shape():
    sql = build_create_table_sql(TEST_TABLE)

    assert sql.startswith(f"CREATE TABLE IF NOT EXISTS {TEST_TABLE} (")
    assert "USING DELTA" in sql
    for field in AVAILABILITY_FIELDS:
        assert f"{field} STRING" in sql
    assert "availability_id STRING NOT NULL" in sql
    assert "dataset STRING NOT NULL" in sql
    assert "evidence_url STRING" in sql
    assert "evidence_url STRING NOT NULL" not in sql
    assert "evidence_note STRING NOT NULL" not in sql
    assert "landed_source_file_id STRING NOT NULL" not in sql


def test_upsert_merges_on_availability_id_updating_only_evidence():
    record = build_not_published_record(
        IDENTITY, EVIDENCE_URL, "checked manually", CHECKED_AT, "operator"
    )
    sql = build_upsert_sql(TEST_TABLE, record)

    assert "MERGE INTO" in sql
    assert "ON target.availability_id = source.availability_id" in sql

    update_section = sql.split("WHEN MATCHED THEN UPDATE SET", 1)[1].split(
        "WHEN NOT MATCHED", 1
    )[0]
    assert "target.availability_state = source.availability_state" in update_section
    # The identity is the merge key and is never rewritten.
    assert "target.availability_id = source.availability_id" not in update_section
    assert "target.source_family = source.source_family" not in update_section
    assert "target.file_type = source.file_type" not in update_section


def test_upsert_is_idempotent_for_the_same_asset():
    first = build_not_published_record(
        IDENTITY,
        EVIDENCE_URL,
        "checked manually",
        CHECKED_AT,
        "operator",
        run_id="run-1",
    )
    second = build_not_published_record(
        IDENTITY,
        EVIDENCE_URL,
        "checked manually",
        CHECKED_AT,
        "operator",
        run_id="run-1",
    )

    assert first["availability_id"] == second["availability_id"]
    assert build_upsert_sql(TEST_TABLE, first) == build_upsert_sql(TEST_TABLE, second)


def test_store_upsert_refuses_invalid_records_and_executes_nothing():
    spark = StubSpark()
    store = AvailabilityStore(table_name=TEST_TABLE, spark=spark)
    record = build_not_published_record(
        IDENTITY, EVIDENCE_URL, "checked manually", CHECKED_AT, "operator"
    )
    record.pop("evidence_note")

    with pytest.raises(
        ValueError, match="Refusing to store invalid availability record"
    ):
        store.upsert(record)

    assert spark.sql_log == []


def test_store_upsert_requires_a_spark_session():
    store = AvailabilityStore(table_name=TEST_TABLE)
    record = build_not_published_record(
        IDENTITY, EVIDENCE_URL, "checked manually", CHECKED_AT, "operator"
    )

    with pytest.raises(ValueError, match="Spark session is required"):
        store.upsert(record)

    with pytest.raises(ValueError, match="Spark session is required"):
        store.read("a" * 64)


def test_store_read_returns_the_stored_row_or_none():
    record = build_not_published_record(
        IDENTITY, EVIDENCE_URL, "checked manually", CHECKED_AT, "operator"
    )
    store = AvailabilityStore(table_name=TEST_TABLE, spark=StubSpark(rows=[record]))

    assert store.read(record["availability_id"]) == record
    assert (
        store.read_by_identity(
            "insideairbnb",
            "hamburg",
            "2026-10-18",
            "geojson",
            "neighbourhood_geometry",
        )
        == record
    )

    empty = AvailabilityStore(table_name=TEST_TABLE, spark=StubSpark(rows=[]))
    assert empty.read(record["availability_id"]) is None


def test_store_read_rejects_non_string_ids():
    store = AvailabilityStore(table_name=TEST_TABLE, spark=StubSpark())

    with pytest.raises(ValueError, match="availability_id is required"):
        store.read(123)


def test_store_ensure_table_creates_and_only_evolves_when_columns_are_missing():
    full_shape = [{"col_name": field} for field in AVAILABILITY_FIELDS]
    spark = StubSpark(rows=full_shape)
    store = AvailabilityStore(table_name=TEST_TABLE, spark=spark)

    store.ensure_table()

    assert spark.sql_log[0].startswith("CREATE TABLE IF NOT EXISTS")
    assert not any(sql.startswith("ALTER") for sql in spark.sql_log)

    legacy = [
        {"col_name": field} for field in AVAILABILITY_FIELDS if field != "recorded_by"
    ]
    spark = StubSpark(rows=legacy)
    store = AvailabilityStore(table_name=TEST_TABLE, spark=spark)

    store.ensure_table()

    alter_statements = [sql for sql in spark.sql_log if sql.startswith("ALTER")]
    assert len(alter_statements) == 1
    assert "recorded_by STRING" in alter_statements[0]


def test_list_by_city_dataset_scopes_the_slice_and_returns_row_dicts():
    spark = StubSpark(
        rows=[
            {
                "availability_id": build_availability_id(
                    "insideairbnb",
                    "toronto",
                    "2026-09-16",
                    "csv.gz",
                    "listings",
                ),
                "availability_state": "available",
                "dataset": "listings",
            }
        ]
    )
    store = AvailabilityStore(table_name=TEST_TABLE, spark=spark)

    rows = store.list_by_city_dataset("toronto", "listings")

    assert rows == [
        {
            "availability_id": build_availability_id(
                "insideairbnb", "toronto", "2026-09-16", "csv.gz", "listings"
            ),
            "availability_state": "available",
            "dataset": "listings",
        }
    ]
    assert "WHERE source_entity_id = 'toronto'" in spark.sql_log[0]
    assert "AND dataset = 'listings'" in spark.sql_log[0]


def test_list_by_city_dataset_requires_both_scope_arguments():
    store = AvailabilityStore(table_name=TEST_TABLE, spark=StubSpark(rows=[]))

    with pytest.raises(ValueError, match="source_entity_id is required"):
        store.list_by_city_dataset("", "listings")

    with pytest.raises(ValueError, match="dataset is required"):
        store.list_by_city_dataset("toronto", " ")


def test_yaml_contract_matches_the_module_rules():
    with (ROOT / "contracts/ops/source_file_availability.yml").open() as file:
        contract = yaml.safe_load(file)

    assert contract["states"] == list(ALLOWED_AVAILABILITY_STATES)
    assert list(contract["fields"]) == list(AVAILABILITY_FIELDS)
    nullable = {"evidence_url", "evidence_note", "landed_source_file_id"}
    for field in contract["fields"]:
        expected = field not in nullable
        assert contract["fields"][field]["required"] is expected, field
