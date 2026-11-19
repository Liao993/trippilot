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
    LISTINGS_CONTROL_COLUMNS,
    OPERATIONAL_TABLE_SHAPES,
    PER_DATASET_CONTROL_COLUMNS,
    build_add_columns_sql,
    build_create_table_sql,
    ensure_operational_table,
    ensure_operational_tables,
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


def test_listings_control_shape_matches_runtime_evolution():
    # The 8 legacy F02 columns plus the two F05.3 identity columns.
    assert list(LISTINGS_CONTROL_COLUMNS)[:8] == [
        "city",
        "snapshot_date",
        "run_id",
        "status",
        "row_count",
        "started_at_utc",
        "completed_at_utc",
        "error_message",
    ]
    assert list(LISTINGS_CONTROL_COLUMNS)[8:] == [
        "source_file_id",
        "prior_source_file_id",
    ]


def test_per_dataset_shape_is_listings_plus_dataset_tag():
    assert set(PER_DATASET_CONTROL_COLUMNS) - set(LISTINGS_CONTROL_COLUMNS) == {
        "dataset"
    }
    assert set(PER_DATASET_CONTROL_COLUMNS) == set(LISTINGS_CONTROL_COLUMNS) | {
        "dataset"
    }


def test_missing_columns_ignores_extra_describe_rows():
    existing = list(LISTINGS_CONTROL_COLUMNS)[:8] + [
        "# Clustering Information",
        "# col_name",
    ]

    assert missing_columns(existing, LISTINGS_CONTROL_COLUMNS) == [
        "source_file_id",
        "prior_source_file_id",
    ]


def test_build_add_columns_sql_is_none_when_shape_complete():
    assert (
        build_add_columns_sql(
            "a.b.c", LISTINGS_CONTROL_COLUMNS, LISTINGS_CONTROL_COLUMNS
        )
        is None
    )


def test_ensure_operational_table_ok_when_shape_complete():
    spark = StubSpark(existing_columns=LISTINGS_CONTROL_COLUMNS)

    action = ensure_operational_table(spark, "a.b.c", LISTINGS_CONTROL_COLUMNS)

    assert action == "ok"
    assert spark.calls[0].startswith("CREATE TABLE IF NOT EXISTS a.b.c")
    assert not [c for c in spark.calls if c.startswith("ALTER")]


def test_ensure_operational_table_evolves_legacy_schema():
    legacy = StubSpark(existing_columns=list(LISTINGS_CONTROL_COLUMNS)[:8])
    table = "trippilot_dev.bronze.airbnb_ingestion_control"

    action = ensure_operational_table(legacy, table, LISTINGS_CONTROL_COLUMNS)

    assert action == "evolved"
    alters = [c for c in legacy.calls if c.startswith("ALTER")]
    assert len(alters) == 1
    assert alters[0] == (
        f"ALTER TABLE {table} ADD COLUMNS "
        "(source_file_id STRING, prior_source_file_id STRING)"
    )


def test_ensure_operational_tables_touches_only_operational_keys():
    spark = StubSpark(existing_columns=PER_DATASET_CONTROL_COLUMNS)
    tables = {
        "bronze": "x.bronze.listings",
        "bronze_control": "x.bronze.ctrl",
        "calendar_control": "x.bronze.ccal",
        "reviews_control": "x.bronze.crev",
        "quality_results": "x.ops.q",
        "source_manifest": "x.ops.manifest",
    }

    actions = ensure_operational_tables(spark, tables)

    assert set(actions) == {
        "bronze_control",
        "calendar_control",
        "reviews_control",
        "quality_results",
    }
    created = {
        c.split(" IF NOT EXISTS ")[1].split(" (")[0]
        for c in spark.calls
        if c.startswith("CREATE TABLE")
    }
    assert created == {"x.bronze.ctrl", "x.bronze.ccal", "x.bronze.crev", "x.ops.q"}


def test_ensure_schemas_creates_each_unique_schema_once():
    spark = StubSpark()

    made = ensure_schemas(spark, ["t.bronze.a", "t.bronze.b", "t.ops.c", "t.silver.d"])

    assert made == ["t.bronze", "t.ops", "t.silver"]
    assert spark.calls == [f"CREATE SCHEMA IF NOT EXISTS {s}" for s in made]


def test_operational_shapes_cover_expected_keys():
    assert set(OPERATIONAL_TABLE_SHAPES) == {
        "bronze_control",
        "calendar_control",
        "reviews_control",
        "quality_results",
    }
