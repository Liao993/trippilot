"""Tests for operational table shapes and idempotent setup helpers.

These tests use a stubbed Spark session (the same pattern as the
ManifestStore tests): SQL statements are recorded, and DESCRIBE answers
come from a fixed schema, so the SQL contracts are checked exactly
without a real Databricks workspace.
"""

import sys
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

from src.common.table_setup import (
    INGESTION_MANIFEST_COLUMNS,
    OPERATIONAL_TABLE_SHAPES,
    build_add_columns_sql,
    build_create_table_sql,
    ensure_catalog,
    ensure_operational_table,
    ensure_operational_tables,
    ensure_reserved_schemas,
    ensure_schemas,
    missing_columns,
)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def collect(self):
        return self._rows


class StubSpark:
    """Records every SQL statement; answers DESCRIBE from a fixed schema."""

    def __init__(self, existing_columns=()):
        self.calls = []
        self.existing = list(existing_columns)

    def sql(self, statement):
        self.calls.append(statement)
        if statement.startswith("DESCRIBE "):
            return _Result([{"col_name": name} for name in self.existing])
        return _Result([])


def test_build_create_table_sql_shape():
    sql = build_create_table_sql("a.b.c", {"city": "STRING", "row_count": "BIGINT"})

    assert sql.startswith("CREATE TABLE IF NOT EXISTS a.b.c (")
    assert "city STRING" in sql
    assert "row_count BIGINT" in sql
    assert sql.endswith(") USING DELTA")


@pytest.mark.parametrize("bad", ["a.b", "A.b.c", "a.b.c; DROP TABLE x", "a b c", ""])
def test_build_create_table_sql_rejects_unsafe_table_names(bad):
    with pytest.raises(ValueError):
        build_create_table_sql(bad, {"city": "STRING"})


def test_build_create_table_sql_rejects_unsafe_columns():
    with pytest.raises(ValueError):
        build_create_table_sql("a.b.c", {"bad name": "STRING"})

    with pytest.raises(ValueError):
        build_create_table_sql("a.b.c", {"city": "STRING; evil"})


def test_ingestion_manifest_shape_is_f07_4_contract():
    # The retired F06.3 control columns, in order, plus the F07.4
    # reconciliation counts and target_table.
    assert list(INGESTION_MANIFEST_COLUMNS) == [
        "city",
        "snapshot_date",
        "run_id",
        "dataset",
        "source_file_id",
        "prior_source_file_id",
        "status",
        "source_row_count",
        "loaded_row_count",
        "rejected_row_count",
        "started_at_utc",
        "completed_at_utc",
        "target_table",
        "error_message",
    ]
    assert INGESTION_MANIFEST_COLUMNS["source_row_count"] == "BIGINT"
    assert INGESTION_MANIFEST_COLUMNS["dataset"] == "STRING"
    assert INGESTION_MANIFEST_COLUMNS["target_table"] == "STRING"


def test_missing_columns_ignores_extra_describe_rows():
    # A migrated legacy control table: all base keys present, the
    # F07.4 reconciliation columns missing.
    existing = [
        "city",
        "snapshot_date",
        "run_id",
        "dataset",
        "source_file_id",
        "prior_source_file_id",
        "status",
        "loaded_row_count",
        "started_at_utc",
        "completed_at_utc",
        "error_message",
        "# Clustering Information",
        "# col_name",
    ]

    assert missing_columns(existing, INGESTION_MANIFEST_COLUMNS) == [
        "source_row_count",
        "rejected_row_count",
        "target_table",
    ]


def test_build_add_columns_sql_is_none_when_shape_complete():
    assert (
        build_add_columns_sql(
            "a.b.c", INGESTION_MANIFEST_COLUMNS, INGESTION_MANIFEST_COLUMNS
        )
        is None
    )


def test_ensure_operational_table_ok_when_shape_complete():
    spark = StubSpark(existing_columns=INGESTION_MANIFEST_COLUMNS)

    action = ensure_operational_table(spark, "a.b.c", INGESTION_MANIFEST_COLUMNS)

    assert action == "ok"
    assert spark.calls[0].startswith("CREATE TABLE IF NOT EXISTS a.b.c")
    assert not [c for c in spark.calls if c.startswith("ALTER")]


def test_ensure_operational_table_evolves_legacy_schema():
    # A migrated control-history table keeps its columns and gains the
    # F07.4 reconciliation columns additively.
    legacy_columns = [
        "city",
        "snapshot_date",
        "run_id",
        "dataset",
        "source_file_id",
        "prior_source_file_id",
        "status",
        "loaded_row_count",
        "started_at_utc",
        "completed_at_utc",
        "error_message",
    ]
    legacy = StubSpark(existing_columns=legacy_columns)
    table = "trippilot_dev.ops.ingestion_manifest"

    action = ensure_operational_table(legacy, table, INGESTION_MANIFEST_COLUMNS)

    assert action == "evolved"
    alters = [c for c in legacy.calls if c.startswith("ALTER")]
    assert len(alters) == 1
    assert alters[0] == (
        f"ALTER TABLE {table} ADD COLUMNS "
        "(source_row_count BIGINT, rejected_row_count BIGINT, target_table STRING)"
    )


def test_ensure_operational_tables_touches_only_operational_keys():
    spark = StubSpark(existing_columns=INGESTION_MANIFEST_COLUMNS)
    tables = {
        "bronze": "x.bronze.listings",
        "ingestion_manifest": "x.ops.ingest",
        "quality_results": "x.ops.q",
        "source_manifest": "x.ops.manifest",
        "source_availability": "x.ops.avail",
    }

    actions = ensure_operational_tables(spark, tables)

    assert set(actions) == {"ingestion_manifest", "quality_results"}
    created = {
        c.split(" IF NOT EXISTS ")[1].split(" (")[0]
        for c in spark.calls
        if c.startswith("CREATE TABLE")
    }
    assert created == {"x.ops.ingest", "x.ops.q"}


def test_ensure_schemas_creates_each_unique_schema_once():
    spark = StubSpark()

    made = ensure_schemas(
        spark, ["t.bronze.a", "t.bronze.b", "t.ops.c", "t.reporting.d"]
    )

    assert made == ["t.bronze", "t.ops", "t.reporting"]
    assert spark.calls == [f"CREATE SCHEMA IF NOT EXISTS {s}" for s in made]


def test_ensure_reserved_schemas_creates_each_schema():
    # F07.4: the empty silver schema is reserved (no tables, no
    # resolver keys) until the F08 rebuild populates it.
    spark = StubSpark()

    ensured = ensure_reserved_schemas(spark, ["t.silver"])

    assert ensured == ["t.silver"]
    assert spark.calls == ["CREATE SCHEMA IF NOT EXISTS t.silver"]


def test_operational_shapes_cover_expected_keys():
    # F07.4: the ONE shared ingestion manifest replaced the seven
    # per-dataset control tables.
    assert set(OPERATIONAL_TABLE_SHAPES) == {
        "ingestion_manifest",
        "quality_results",
    }
    assert OPERATIONAL_TABLE_SHAPES["ingestion_manifest"] is INGESTION_MANIFEST_COLUMNS


def test_ensure_catalog_creates_idempotently():
    spark = StubSpark()

    assert ensure_catalog(spark, "trippilot_test") == "trippilot_test"
    assert spark.calls == ["CREATE CATALOG IF NOT EXISTS trippilot_test"]


@pytest.mark.parametrize("bad", ["A.B", "tri-pilot", "a b", "", "x.y", None])
def test_ensure_catalog_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        ensure_catalog(StubSpark(), bad)
