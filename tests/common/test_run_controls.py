"""
Unit tests for ingestion rerun-control logic.

These tests use small hardcoded inputs on purpose. They check exact rules
without needing Databricks, Spark, a Volume, or real Airbnb data.
"""

import sys
from pathlib import Path

import pytest

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

from src.common.run_controls import (
    build_control_record,
    decide_ingestion_action,
    latest_successful_source_file_id,
    record_control_failure,
    should_load,
)


class _SqlCaptureSpark:
    """Stub Spark session that records the SQL it is asked to run."""

    def __init__(self):
        self.statements = []

    def sql(self, statement):
        self.statements.append(statement)


def _success_control(**overrides):
    control = {
        "city": "toronto",
        "snapshot_date": "2026-09-16",
        "status": "success",
        "source_file_id": "a" * 64,
        "completed_at_utc": "2026-11-14T10:00:00+00:00",
    }
    control.update(overrides)
    return control


def test_should_load_when_no_control_record_exists():
    """
    If we have never loaded this city/snapshot, the pipeline should load it.
    """
    existing_controls = []

    result = should_load(
        existing_controls=existing_controls,
        city="toronto",
        snapshot_date="2026-09-16",
    )

    assert result is True


def test_should_skip_successful_city_snapshot():
    """
    If the same city and snapshot already loaded successfully,
    rerunning it should be skipped to prevent duplicate Bronze rows.
    """
    existing_controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "success",
            "row_count": 100,
            "run_id": "run-1",
            "error_message": None,
        }
    ]

    result = should_load(
        existing_controls=existing_controls,
        city="toronto",
        snapshot_date="2026-09-16",
    )

    assert result is False


def test_should_retry_failed_city_snapshot():
    """
    A failed load should not block a retry.
    The pipeline should try again because no successful load exists.
    """
    existing_controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "failed",
            "row_count": 0,
            "run_id": "run-1",
            "error_message": "Raw file read failed",
        }
    ]

    result = should_load(
        existing_controls=existing_controls,
        city="toronto",
        snapshot_date="2026-09-16",
    )

    assert result is True


def test_should_load_new_snapshot_for_same_city():
    """
    A new snapshot date is new source data, even for a city
    that was successfully loaded before.
    """
    existing_controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "success",
            "row_count": 100,
            "run_id": "run-1",
            "error_message": None,
        }
    ]

    result = should_load(
        existing_controls=existing_controls,
        city="toronto",
        snapshot_date="2026-10-01",
    )

    assert result is True


def test_build_control_record_returns_expected_fields():
    """
    The control record should contain the minimum fields needed
    to audit an ingestion attempt.
    """
    record = build_control_record(
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="run-123",
        status="success",
        row_count=250,
    )

    assert record["city"] == "toronto"
    assert record["snapshot_date"] == "2026-09-16"
    assert record["run_id"] == "run-123"
    assert record["status"] == "success"
    assert record["row_count"] == 250
    assert record["error_message"] is None


# --- F05.3: identity-aware ingestion decisions -------------------------


def test_decide_action_loads_first_time_or_new_snapshot():
    controls = [_success_control(city="toronto", snapshot_date="2026-09-16")]

    action = decide_ingestion_action(controls, "toronto", "2026-12-15", "b" * 64)

    assert action == "load"


def test_decide_action_skips_exact_same_file_retry():
    controls = [_success_control()]

    action = decide_ingestion_action(
        controls, "toronto", "2026-09-16", "a" * 64, force_reload=False
    )

    assert action == "skip"


def test_decide_action_authorizes_exact_retry_with_force():
    controls = [_success_control()]

    action = decide_ingestion_action(
        controls, "toronto", "2026-09-16", "a" * 64, force_reload=True
    )

    assert action == "load"


def test_decide_action_blocks_corrected_file_without_force():
    controls = [_success_control()]

    with pytest.raises(ValueError, match="Corrected or replaced source file"):
        decide_ingestion_action(
            controls, "toronto", "2026-09-16", "b" * 64, force_reload=False
        )


def test_decide_action_allows_controlled_reprocess_with_force():
    controls = [_success_control()]

    action = decide_ingestion_action(
        controls, "toronto", "2026-09-16", "b" * 64, force_reload=True
    )

    assert action == "load"


def test_decide_action_treats_legacy_success_without_identity_as_reprocess():
    controls = [_success_control(source_file_id=None)]

    with pytest.raises(ValueError, match="legacy, no identity"):
        decide_ingestion_action(
            controls, "toronto", "2026-09-16", "a" * 64, force_reload=False
        )

    assert (
        decide_ingestion_action(
            controls, "toronto", "2026-09-16", "a" * 64, force_reload=True
        )
        == "load"
    )


def test_decide_action_ignores_failures_when_deciding():
    controls = [
        {"city": "toronto", "snapshot_date": "2026-09-16", "status": "failed"},
        _success_control(city="vancouver"),
    ]

    assert (
        decide_ingestion_action(controls, "toronto", "2026-09-16", "a" * 64) == "load"
    )


def test_decide_action_requires_a_source_file_id():
    with pytest.raises(ValueError, match="source_file_id is required"):
        decide_ingestion_action([], "toronto", "2026-09-16", "  ")


# --- F06.3: dataset-scoped ingestion decisions -------------------------


def test_decide_action_same_dataset_same_file_skips():
    controls = [_success_control(dataset="calendar", source_file_id="a" * 64)]

    action = decide_ingestion_action(
        controls, "toronto", "2026-09-16", "a" * 64, dataset="calendar"
    )

    assert action == "skip"


def test_decide_action_same_dataset_corrected_file_blocked():
    controls = [_success_control(dataset="calendar", source_file_id="a" * 64)]

    with pytest.raises(ValueError, match="calendar/toronto/2026-09-16"):
        decide_ingestion_action(
            controls, "toronto", "2026-09-16", "b" * 64, dataset="calendar"
        )


def test_decide_action_same_dataset_force_allows_reprocess():
    controls = [_success_control(dataset="reviews", source_file_id="a" * 64)]

    action = decide_ingestion_action(
        controls,
        "toronto",
        "2026-09-16",
        "b" * 64,
        force_reload=True,
        dataset="reviews",
    )

    assert action == "load"


def test_decide_action_new_snapshot_loads_for_scoped_dataset():
    controls = [_success_control(dataset="calendar", source_file_id="a" * 64)]

    action = decide_ingestion_action(
        controls, "toronto", "2026-12-15", "b" * 64, dataset="calendar"
    )

    assert action == "load"


def test_decide_action_ignores_other_datasets_rows():
    """A calendar success must never block or skip the reviews dataset."""
    controls = [
        _success_control(dataset="calendar", source_file_id="a" * 64),
        _success_control(dataset="listings", source_file_id="a" * 64),
    ]

    action = decide_ingestion_action(
        controls, "toronto", "2026-09-16", "b" * 64, dataset="reviews"
    )

    assert action == "load"


def test_default_scope_includes_legacy_untagged_rows():
    """Untagged rows are pre-F06.3 listings history: the default scope
    must keep reading them exactly as F05 did."""
    controls = [_success_control(source_file_id="a" * 64)]  # no dataset tag

    assert (
        decide_ingestion_action(controls, "toronto", "2026-09-16", "a" * 64) == "skip"
    )
    with pytest.raises(ValueError, match="Corrected or replaced source file"):
        decide_ingestion_action(controls, "toronto", "2026-09-16", "b" * 64)


def test_default_scope_excludes_tagged_rows():
    """A tagged calendar success is invisible to the listings scope."""
    controls = [_success_control(dataset="calendar", source_file_id="a" * 64)]

    action = decide_ingestion_action(controls, "toronto", "2026-09-16", "a" * 64)

    assert action == "load"


def test_untagged_rows_never_leak_into_other_datasets():
    """Legacy listings rows must not block a calendar/reviews decision."""
    controls = [
        _success_control(source_file_id="a" * 64),  # legacy listings row
    ]

    assert (
        decide_ingestion_action(
            controls, "toronto", "2026-09-16", "b" * 64, dataset="reviews"
        )
        == "load"
    )


def test_build_control_record_carries_dataset_tag():
    record = build_control_record(
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="run-123",
        status="success",
        row_count=10,
        dataset="reviews",
    )

    assert record["dataset"] == "reviews"

    legacy = build_control_record(
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="run-124",
        status="success",
        row_count=10,
    )
    assert legacy["dataset"] is None


def test_latest_successful_source_file_id_picks_newest_completed():
    controls = [
        _success_control(source_file_id="a" * 64, completed_at_utc="2026-11-13"),
        _success_control(source_file_id="b" * 64, completed_at_utc="2026-11-14"),
        {"city": "toronto", "status": "failed", "source_file_id": "c" * 64},
    ]

    assert latest_successful_source_file_id(controls) == "b" * 64


def test_latest_successful_source_file_id_returns_none_without_success():
    assert latest_successful_source_file_id([]) is None
    assert (
        latest_successful_source_file_id([{"city": "toronto", "status": "failed"}])
        is None
    )


# --- F05.3: auditable failure recording -------------------------------


def test_record_control_failure_updates_the_run_row():
    spark = _SqlCaptureSpark()

    record_control_failure(
        spark,
        "trippilot_dev.bronze.airbnb_listings_ingestion_control_test",
        "a" * 32,
        ValueError("gzip stream is not readable"),
    )

    sql = spark.statements[0]
    assert sql.startswith(
        "UPDATE trippilot_dev.bronze.airbnb_listings_ingestion_control_test"
    )
    assert "status = 'failed'" in sql
    assert "WHERE run_id = '" + "a" * 32 + "'" in sql
    assert "gzip stream is not readable" in sql


def test_record_control_failure_sanitizes_and_truncates():
    spark = _SqlCaptureSpark()

    record_control_failure(
        spark, "a.b.c", "b" * 32, "boom 'quotes'\n\tnewlines " + "x" * 600
    )

    sql = spark.statements[0]
    message = sql.split("error_message = '")[1].split("' WHERE")[0]
    assert "'" not in message
    assert "x" * 600 not in message  # truncated to the 500-char cap


def test_record_control_failure_rejects_unsafe_inputs():
    with pytest.raises(ValueError, match="run_id"):
        record_control_failure(
            _SqlCaptureSpark(), "a.b.c", "toronto' OR '1'='1", "boom"
        )
    with pytest.raises(ValueError, match="catalog.schema.table"):
        record_control_failure(_SqlCaptureSpark(), "not a table", "a" * 32, "boom")
