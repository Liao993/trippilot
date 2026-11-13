"""Unit tests for the manifest-store Delta adapter (F04.3).

The Spark session is stubbed: these tests assert the SQL contracts
(creation, idempotent MERGE keyed by source_file_id, operational-
fields-only updates) and the adapter's validation behaviour. No
production table and no real Spark session is used; the Databricks
runtime tests exercise the real Delta MERGE against an isolated
*_test table.
"""

import pytest

from src.common.source_manifest import apply_state_transition
from src.common.source_manifest_store import (
    MANIFEST_FIELDS,
    UPDATABLE_FIELDS,
    ManifestStore,
    build_create_table_sql,
    build_upsert_sql,
)

TEST_TABLE = "trippilot_dev.ops.source_file_manifest_test"


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


def _record(**overrides):
    record = {
        "source_file_id": "a" * 64,
        "source_family": "insideairbnb",
        "source_entity_id": "toronto",
        "source_version": "2026-09-16",
        "file_type": "csv.gz",
        "source_url": "https://insideairbnb.com/get-the-data/",
        "retrieved_at_utc": "2026-11-13T18:00:00Z",
        "file_hash_sha256": "b" * 64,
        "byte_size": 75,
        "schema_version": "pending",
        "license": "CC0-1.0",
        "attribution": "Inside Airbnb (insideairbnb.com), CC0 1.0",
        "source_path": "/some/incoming/listings.csv.gz",
        "run_id": "c" * 32,
        "processing_state": "registered",
    }
    record.update(overrides)
    return record


def _update_set_section(sql):
    return sql.split("WHEN MATCHED THEN UPDATE SET", 1)[1].split("WHEN NOT MATCHED", 1)[
        0
    ]


def test_create_table_sql_matches_the_contract():
    sql = build_create_table_sql(TEST_TABLE)

    assert sql.startswith(f"CREATE TABLE IF NOT EXISTS {TEST_TABLE} (")
    assert "USING DELTA" in sql
    for field in MANIFEST_FIELDS:
        assert f"{field} " in sql
    assert "byte_size BIGINT NOT NULL" in sql
    assert "source_file_id STRING NOT NULL" in sql
    assert "landing_path STRING" in sql
    assert "error_message STRING" in sql
    assert "landing_path STRING NOT NULL" not in sql
    assert "error_message STRING NOT NULL" not in sql


def test_invalid_table_names_are_rejected():
    for bad_name in (
        "trippilot_dev.ops.source_file_manifest; DROP TABLE x",
        "trippilot dev.ops.source_file_manifest",
        "",
        "trippilot_dev",
    ):
        with pytest.raises(ValueError, match="Invalid manifest table name"):
            ManifestStore(table_name=bad_name)


def test_upsert_merges_on_source_file_id_with_operational_updates_only():
    sql = build_upsert_sql(TEST_TABLE, _record())

    assert "MERGE INTO" in sql
    assert "ON target.source_file_id = source.source_file_id" in sql
    assert "WHEN MATCHED THEN UPDATE SET" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql

    update_section = _update_set_section(sql)
    for field in UPDATABLE_FIELDS:
        assert f"target.{field} = source.{field}" in update_section
    # Identity and source metadata must never be overwritten in place.
    for immutable in (
        "source_family",
        "source_entity_id",
        "source_version",
        "file_type",
        "source_url",
        "retrieved_at_utc",
        "file_hash_sha256",
        "byte_size",
        "schema_version",
        "license",
        "attribution",
        "source_path",
        "source_file_id",
    ):
        assert f"target.{immutable} = source.{immutable}" not in update_section


def test_upsert_inserts_every_contract_field_on_miss():
    sql = build_upsert_sql(TEST_TABLE, _record())
    insert_section = sql.split("WHEN NOT MATCHED THEN INSERT", 1)[1]

    for field in MANIFEST_FIELDS:
        assert field in insert_section


def test_upsert_escapes_single_quotes_in_literals():
    record = _record(attribution="O'Brien's dataset")
    sql = build_upsert_sql(TEST_TABLE, record)

    assert "'O''Brien''s dataset'" in sql


def test_upsert_renders_null_for_absent_optional_fields():
    sql = build_upsert_sql(TEST_TABLE, _record())

    assert "NULL AS landing_path" in sql
    assert "NULL AS error_message" in sql


def test_upsert_rejects_boolean_values():
    record = _record(processing_state=True)

    with pytest.raises(TypeError, match="Boolean values"):
        build_upsert_sql(TEST_TABLE, record)


def test_store_upsert_refuses_invalid_records_and_executes_nothing():
    spark = StubSpark()
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)
    record = _record()
    record.pop("license")

    with pytest.raises(ValueError, match="Refusing to store invalid manifest record"):
        store.upsert(record)

    assert spark.sql_log == []


def test_store_upsert_requires_a_spark_session():
    store = ManifestStore(table_name=TEST_TABLE)

    with pytest.raises(ValueError, match="Spark session is required"):
        store.upsert(_record())

    with pytest.raises(ValueError, match="Spark session is required"):
        store.read("a" * 64)


def test_store_upsert_executes_the_merge_sql():
    spark = StubSpark()
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)

    record = store.upsert(_record())

    assert record["processing_state"] == "registered"
    assert len(spark.sql_log) == 1
    assert "MERGE INTO" in spark.sql_log[0]


def test_store_ensure_table_executes_create_sql():
    spark = StubSpark()
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)

    store.ensure_table()

    assert len(spark.sql_log) == 1
    assert spark.sql_log[0].startswith("CREATE TABLE IF NOT EXISTS")


def test_read_returns_the_stored_row():
    spark = StubSpark(rows=[_record(processing_state="landed")])
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)

    record = store.read("a" * 64)

    assert record is not None
    assert record["processing_state"] == "landed"
    assert "WHERE source_file_id = 'aaaaaaaa" in spark.sql_log[0]


def test_read_returns_none_when_no_row_exists():
    store = ManifestStore(table_name=TEST_TABLE, spark=StubSpark(rows=[]))

    assert store.read("a" * 64) is None


def test_read_rejects_non_string_ids():
    store = ManifestStore(table_name=TEST_TABLE, spark=StubSpark())

    with pytest.raises(ValueError, match="source_file_id is required"):
        store.read(123)


def test_read_landed_raises_for_missing_record():
    store = ManifestStore(table_name=TEST_TABLE, spark=StubSpark(rows=[]))

    with pytest.raises(ValueError, match="no manifest record found"):
        store.read_landed("a" * 64)


def test_read_landed_raises_for_non_landed_state():
    spark = StubSpark(rows=[_record(processing_state="registered")])
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)

    with pytest.raises(ValueError, match="not landed"):
        store.read_landed("a" * 64)


def test_read_landed_requires_a_landing_path():
    spark = StubSpark(rows=[_record(processing_state="landed", landing_path=None)])
    store = ManifestStore(table_name=TEST_TABLE, spark=spark)

    with pytest.raises(ValueError, match="no landing_path"):
        store.read_landed("a" * 64)


def test_read_landed_returns_the_landed_row():
    validated = apply_state_transition(_record(), "validated")
    landed = apply_state_transition(
        validated, "landed", landing_path="/Volumes/dev/bronze/insideairbnb/x.csv.gz"
    )
    store = ManifestStore(table_name=TEST_TABLE, spark=StubSpark(rows=[landed]))

    assert store.read_landed("a" * 64)["landing_path"].endswith("x.csv.gz")


def test_state_transition_updates_only_operational_fields_in_sql():
    validated = apply_state_transition(_record(), "validated")
    landed = apply_state_transition(
        validated,
        "landed",
        landing_path="/Volumes/dev/bronze/insideairbnb/listings__abc.csv.gz",
    )
    sql = build_upsert_sql(TEST_TABLE, landed)

    assert "'landed' AS processing_state" in sql
    assert (
        "'/Volumes/dev/bronze/insideairbnb/listings__abc.csv.gz' AS landing_path" in sql
    )
    assert "NULL AS error_message" in sql


def test_duplicate_upserts_produce_the_same_merge_and_cannot_append_rows():
    record = _record()
    first = build_upsert_sql(TEST_TABLE, record)
    second = build_upsert_sql(TEST_TABLE, dict(record))

    # Same deterministic identity -> the same keyed MERGE, never a plain
    # INSERT INTO that could append a duplicate row.
    assert first == second
    assert "INSERT INTO" not in first
    assert first.count("MERGE INTO") == 1
