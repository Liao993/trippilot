"""
Unit tests for run-mode isolation and table-name resolution.

These tests check exact rules: test mode must never resolve a development
table, live mode must resolve the development tables, and run-control
decisions must combine force reload with the skip-if-successful rule.
"""
import sys
from pathlib import Path

start = Path.cwd().resolve()
ROOT = next(
    (p for p in [start, *start.parents]
     if (p / 'src').is_dir() and (p / 'config/project.yml').is_file()),
    None,
)
if ROOT is None:
    raise RuntimeError('Cannot locate repository root. Open this notebook inside the Databricks Git folder.')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print('Repository root:', ROOT)

import pytest

from src.common.environment import (
    LIVE_TABLES,
    decide_should_run,
    resolve_table,
    resolve_tables,
    validate_force_reload,
    validate_run_mode,
)


def test_run_mode_accepts_test_and_live():
    assert validate_run_mode("test") == "test"
    assert validate_run_mode("live") == "live"


def test_run_mode_rejects_unknown_values():
    with pytest.raises(ValueError):
        validate_run_mode("prod")

    with pytest.raises(ValueError):
        validate_run_mode("")


def test_test_mode_resolves_isolated_tables():
    tables = resolve_tables("test")

    for name, table in tables.items():
        assert table.endswith("_test"), f"{name} resolved to {table}"
        assert table != LIVE_TABLES[name]


def test_test_mode_never_returns_a_development_table():
    tables = resolve_tables("test")

    for table in tables.values():
        assert table not in LIVE_TABLES.values()


def test_live_mode_resolves_development_tables():
    assert resolve_tables("live") == LIVE_TABLES


def test_tables_resolve_individually_per_mode():
    assert resolve_table("bronze", "test") == (
        "trippilot_dev.bronze.airbnb_listings_bronze_test"
    )
    assert resolve_table("bronze_control", "test") == (
        "trippilot_dev.bronze.airbnb_ingestion_control_test"
    )
    assert resolve_table("silver", "test") == (
        "trippilot_dev.silver.airbnb_listings_silver_test"
    )
    assert resolve_table("silver_rejected", "test") == (
        "trippilot_dev.silver.airbnb_listings_rejected_test"
    )
    assert resolve_table("quality_results", "test") == (
        "trippilot_dev.ops.quality_results_test"
    )
    assert resolve_table("exclusion", "test") == (
        "trippilot_dev.ops.exclusion_test"
    )

    assert resolve_table("bronze", "live") == (
        "trippilot_dev.bronze.airbnb_listings_bronze"
    )


def test_unknown_logical_table_raises():
    with pytest.raises(ValueError):
        resolve_table("gold", "test")


def test_force_reload_accepts_bools_and_widget_strings():
    assert validate_force_reload(True) is True
    assert validate_force_reload(False) is False
    assert validate_force_reload("true") is True
    assert validate_force_reload("false") is False


def test_force_reload_rejects_unknown_values():
    with pytest.raises(ValueError):
        validate_force_reload("yes")


def test_decide_should_run_without_controls():
    assert decide_should_run(False, [], "toronto", "2026-09-16") is True
    assert decide_should_run("false", [], "toronto", "2026-09-16") is True


def test_decide_should_run_skips_after_successful_load():
    controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "success",
        }
    ]

    assert decide_should_run(False, controls, "toronto", "2026-09-16") is False


def test_decide_should_run_force_reload_overrides_success():
    controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "success",
        }
    ]

    assert decide_should_run(True, controls, "toronto", "2026-09-16") is True
    assert decide_should_run("true", controls, "toronto", "2026-09-16") is True


def test_decide_should_run_runs_again_after_failure():
    controls = [
        {
            "city": "toronto",
            "snapshot_date": "2026-09-16",
            "status": "failed",
        }
    ]

    assert decide_should_run(False, controls, "toronto", "2026-09-16") is True
