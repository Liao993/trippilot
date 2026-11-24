"""Tests for the unified ingestion manifest (F07.4).

Pure, CI-safe checks of the SQL builders, the controlled dataset/status
vocabularies, and the thin Spark-injected store, plus a cross-check that
the documented YAML contract (contracts/ops/ingestion_manifest.yml)
cannot drift from the module rules. No real Databricks workspace is
needed: SQL statements are recorded against a stub Spark session.
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
import yaml

from src.common.ingestion_manifest import (
    INGESTION_DATASETS,
    INGESTION_STATUSES,
    VALID_STATUS_TRANSITIONS,
    IngestionManifestStore,
    build_ingestion_start_sql,
    build_ingestion_success_sql,
    build_manifest_list_city_dataset_sql,
    build_manifest_read_sql,
    sql_string_literal,
    validate_dataset,
    validate_status,
    validate_status_transition,
)
from src.common.table_setup import INGESTION_MANIFEST_COLUMNS

MANIFEST_TABLE = "trippilot_test.ops.ingestion_manifest"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def collect(self):
        return self._rows


class StubSpark:
    """Records every SQL statement; answers collect with fixed rows."""

    def __init__(self):
        self.calls = []

    def sql(self, statement):
        self.calls.append(statement)
        return _Result([])


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------


def test_dataset_tags_are_the_seven_bronze_assets():
    assert INGESTION_DATASETS == (
        "listings",
        "calendar",
        "reviews",
        "listings_summary",
        "reviews_summary",
        "neighbourhoods",
        "neighbourhood_geometry",
    )


def test_statuses_are_the_load_lifecycle_only():
    assert INGESTION_STATUSES == ("running", "success", "failed")


def test_validate_dataset_rejects_arbitrary_tags():
    with pytest.raises(ValueError):
        validate_dataset("holidays")


def test_validate_status_rejects_source_availability_states():
    # not_published is a SOURCE property (F07.3 ledger), never a load status.
    with pytest.raises(ValueError):
        validate_status("not_published")


def test_status_transitions_allow_only_running_to_terminal():
    validate_status_transition("running", "success")
    validate_status_transition("running", "failed")
    for from_status, to_status in (
        ("success", "failed"),
        ("failed", "success"),
        ("success", "running"),
    ):
        with pytest.raises(ValueError):
            validate_status_transition(from_status, to_status)


# ---------------------------------------------------------------------------
# SQL builders
# ---------------------------------------------------------------------------


def test_build_ingestion_start_sql_with_null_prior():
    sql = build_ingestion_start_sql(
        MANIFEST_TABLE,
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="a" * 32,
        dataset="neighbourhoods",
        source_file_id="b" * 64,
        prior_source_file_id=None,
        started_at_utc="2026-11-23T10:00:00+00:00",
        target_table="trippilot_test.bronze.airbnb_neighbourhoods_bronze",
    )

    # One row per source file per run: positional values follow the
    # canonical column order (city .. error_message) - 14 values.
    assert sql.startswith(f"INSERT INTO {MANIFEST_TABLE} VALUES (")
    assert sql.count(",") == 13
    assert "'running'" in sql
    assert sql.endswith(
        ", NULL, NULL, NULL, '2026-11-23T10:00:00+00:00', NULL, "
        "'trippilot_test.bronze.airbnb_neighbourhoods_bronze', NULL)"
    )


def test_build_ingestion_start_sql_with_prior_identity():
    sql = build_ingestion_start_sql(
        MANIFEST_TABLE,
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="a" * 32,
        dataset="calendar",
        source_file_id="def456",
        prior_source_file_id="abc123",
        started_at_utc="t",
        target_table="trippilot_test.bronze.airbnb_calendar_bronze",
    )

    assert "'abc123'" in sql


def test_build_ingestion_start_sql_escapes_quotes():
    sql = build_ingestion_start_sql(
        MANIFEST_TABLE,
        city="o'brien",
        snapshot_date="2026-09-16",
        run_id="a" * 32,
        dataset="reviews",
        source_file_id="x",
        prior_source_file_id=None,
        started_at_utc="t",
        target_table="trippilot_test.bronze.airbnb_reviews_bronze",
    )

    assert "'o''brien'" in sql


def test_build_ingestion_start_sql_requires_hex_run_id():
    with pytest.raises(ValueError, match="run_id"):
        build_ingestion_start_sql(
            MANIFEST_TABLE,
            city="toronto",
            snapshot_date="2026-09-16",
            run_id="run-1",
            dataset="calendar",
            source_file_id="x",
            prior_source_file_id=None,
            started_at_utc="t",
            target_table="t.b.c",
        )


def test_build_ingestion_start_sql_rejects_blank_required_fields():
    with pytest.raises(ValueError, match="city"):
        build_ingestion_start_sql(
            MANIFEST_TABLE,
            city="  ",
            snapshot_date="2026-09-16",
            run_id="a" * 32,
            dataset="calendar",
            source_file_id="x",
            prior_source_file_id=None,
            started_at_utc="t",
            target_table="t.b.c",
        )


def test_build_ingestion_success_sql_shape():
    sql = build_ingestion_success_sql(
        MANIFEST_TABLE,
        run_id="a" * 32,
        source_row_count=8048251,
        loaded_row_count=8048251,
        rejected_row_count=0,
        completed_at_utc="2026-11-23T10:05:00+00:00",
    )

    assert sql == (
        f"UPDATE {MANIFEST_TABLE} SET status = 'success', "
        "source_row_count = 8048251, loaded_row_count = 8048251, "
        "rejected_row_count = 0, "
        "completed_at_utc = '2026-11-23T10:05:00+00:00', "
        f"error_message = NULL WHERE run_id = '{'a' * 32}'"
    )


def test_build_ingestion_success_sql_keeps_null_counts():
    # Migrated legacy paths (listings) record loaded counts only.
    sql = build_ingestion_success_sql(
        MANIFEST_TABLE,
        run_id="a" * 32,
        source_row_count=None,
        loaded_row_count=7,
        rejected_row_count=None,
        completed_at_utc="t",
    )

    assert "source_row_count = NULL" in sql
    assert "rejected_row_count = NULL" in sql
    assert "loaded_row_count = 7" in sql


@pytest.mark.parametrize(
    "counts",
    [
        (-1, 0, 0),
        (0, -1, 0),
        (0, 0, -1),
        (True, 0, 0),
        ("x", 0, 0),
    ],
)
def test_build_ingestion_success_sql_rejects_bad_counts(counts):
    with pytest.raises(ValueError):
        build_ingestion_success_sql(
            MANIFEST_TABLE,
            run_id="a" * 32,
            source_row_count=counts[0],
            loaded_row_count=counts[1],
            rejected_row_count=counts[2],
            completed_at_utc="t",
        )


def test_build_manifest_read_sql_scopes_city_snapshot():
    sql = build_manifest_read_sql(
        MANIFEST_TABLE, city="toronto", snapshot_date="2026-09-16"
    )

    assert sql == (
        f"SELECT * FROM {MANIFEST_TABLE} "
        "WHERE city = 'toronto' AND snapshot_date = '2026-09-16'"
    )


def test_sql_string_literal_escapes_and_rejects_none():
    assert sql_string_literal("o'brien") == "'o''brien'"
    with pytest.raises(ValueError):
        sql_string_literal(None)


# ---------------------------------------------------------------------------
# Store (thin Spark-injected)
# ---------------------------------------------------------------------------


def test_store_requires_spark_for_sql_work():
    store = IngestionManifestStore(MANIFEST_TABLE)

    with pytest.raises(ValueError):
        store.ensure_table()
    with pytest.raises(ValueError):
        store.start_run(
            {
                "city": "toronto",
                "snapshot_date": "2026-09-16",
                "run_id": "a" * 32,
                "dataset": "calendar",
                "source_file_id": "x",
                "prior_source_file_id": None,
                "started_at_utc": "t",
                "target_table": "t.b.c",
            }
        )


def test_store_start_and_complete_execute_the_builders():
    spark = StubSpark()
    store = IngestionManifestStore(MANIFEST_TABLE, spark=spark)

    store.start_run(
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "run_id": "a" * 32,
            "dataset": "calendar",
            "source_file_id": "b" * 64,
            "prior_source_file_id": None,
            "started_at_utc": "t",
            "target_table": "trippilot_test.bronze.airbnb_calendar_bronze",
        }
    )
    store.complete_run(
        run_id="a" * 32,
        source_row_count=5,
        loaded_row_count=5,
        rejected_row_count=0,
        completed_at_utc="t2",
    )

    assert spark.calls[0].startswith(f"INSERT INTO {MANIFEST_TABLE} VALUES (")
    assert spark.calls[1].startswith(f"UPDATE {MANIFEST_TABLE} SET status = 'success'")


def test_store_ensure_table_delegates_to_shape_setup():
    spark = StubSpark()
    store = IngestionManifestStore(MANIFEST_TABLE, spark=spark)

    action = store.ensure_table()

    # StubSpark answers DESCRIBE with no columns, so the missing shape
    # evolves forward: one CREATE followed by one ALTER.
    assert action == "evolved"
    assert spark.calls[0].startswith("CREATE TABLE IF NOT EXISTS ")
    assert spark.calls[1].startswith("DESCRIBE ")
    assert spark.calls[2].startswith("ALTER TABLE ")


def test_store_read_for_slice_returns_row_dicts():
    class _Row:
        def __init__(self, values):
            self._values = values

        def asDict(self):
            return dict(self._values)

    class RowsSpark(StubSpark):
        def sql(self, statement):
            self.calls.append(statement)
            if statement.startswith("SELECT"):
                return _Result(
                    [
                        _Row(
                            {
                                "dataset": "calendar",
                                "run_id": "a" * 32,
                                "status": "success",
                            }
                        )
                    ]
                )
            return _Result([])

    rows = IngestionManifestStore(MANIFEST_TABLE, spark=RowsSpark()).read_for_slice(
        "toronto", "2026-09-16"
    )

    assert rows == [{"dataset": "calendar", "run_id": "a" * 32, "status": "success"}]


@pytest.mark.parametrize("bad", ["nope", "a.b.c; DROP TABLE x", "", None])
def test_store_rejects_unsafe_table_names(bad):
    with pytest.raises(ValueError):
        IngestionManifestStore(bad)


# ---------------------------------------------------------------------------
# YAML contract cross-check
# ---------------------------------------------------------------------------


def test_build_manifest_list_city_dataset_sql_scopes_city_and_dataset():
    sql = build_manifest_list_city_dataset_sql(
        "trippilot_test.ops.ingestion_manifest_test",
        city="toronto",
        dataset="listings",
    )

    assert sql == (
        "SELECT * FROM trippilot_test.ops.ingestion_manifest_test "
        "WHERE city = 'toronto' "
        "AND dataset = 'listings'"
    )


def test_build_manifest_list_city_dataset_sql_requires_a_controlled_tag():
    with pytest.raises(ValueError, match="Unknown dataset"):
        build_manifest_list_city_dataset_sql(
            "trippilot_test.ops.ingestion_manifest_test",
            city="toronto",
            dataset="misc",
        )

    with pytest.raises(ValueError, match="city is required"):
        build_manifest_list_city_dataset_sql(
            "trippilot_test.ops.ingestion_manifest_test",
            city=" ",
            dataset="listings",
        )


def test_store_list_for_city_dataset_executes_and_returns_row_dicts():
    class _Row:
        def __init__(self, values):
            self._values = values

        def asDict(self):
            return dict(self._values)

    class RowsSpark(StubSpark):
        def sql(self, statement):
            self.calls.append(statement)
            if statement.startswith("SELECT"):
                return _Result(
                    [
                        _Row(
                            {
                                "city": "toronto",
                                "dataset": "listings",
                                "status": "success",
                            }
                        )
                    ]
                )
            return _Result([])

    spark = RowsSpark()
    store = IngestionManifestStore(MANIFEST_TABLE, spark=spark)

    rows = store.list_for_city_dataset("toronto", "listings")

    assert rows == [{"city": "toronto", "dataset": "listings", "status": "success"}]
    assert "WHERE city = 'toronto'" in spark.calls[0]
    assert "AND dataset = 'listings'" in spark.calls[0]


def test_yaml_contract_matches_the_module_rules():
    contract = yaml.safe_load(
        (ROOT / "contracts" / "ops" / "ingestion_manifest.yml").read_text()
    )

    assert contract["datasets"] == list(INGESTION_DATASETS)
    assert contract["statuses"] == list(INGESTION_STATUSES)
    assert contract["valid_transitions"] == {
        key: list(value) for key, value in VALID_STATUS_TRANSITIONS.items()
    }
    assert list(contract["fields"]) == list(INGESTION_MANIFEST_COLUMNS)

    optional = {
        "prior_source_file_id",
        "source_row_count",
        "loaded_row_count",
        "rejected_row_count",
        "completed_at_utc",
        "error_message",
    }
    for field, entry in contract["fields"].items():
        assert entry["required"] is (field not in optional), field
        assert isinstance(entry["type"], str) and entry["type"], field
