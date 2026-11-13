"""
Unit tests for ingestion rerun-control logic.

These tests use small hardcoded inputs on purpose. They check exact rules
without needing Databricks, Spark, a Volume, or real Airbnb data.
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

from src.common.run_controls import build_control_record, should_load


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
