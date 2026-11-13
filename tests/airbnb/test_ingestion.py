"""Service-contract tests for the Bronze snapshot writer.

These tests use a recording stand-in instead of a real Spark
DataFrame, so they verify how write_snapshot validates its arguments
and drives the write API without a cluster or Databricks access.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

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

from src.airbnb.ingestion import write_snapshot

VALID_TABLE = "trippilot_dev.bronze.airbnb_listings_bronze"
VALID_CITY = "toronto"
VALID_DATE = "2026-09-16"


class _RecordingWriter:
    """Chainable stand-in for a Spark DataFrameWriter."""

    def __init__(self):
        self.calls = []

    def format(self, fmt):
        self.calls.append(("format", fmt))
        return self

    def mode(self, mode):
        self.calls.append(("mode", mode))
        return self

    def option(self, key, value):
        self.calls.append(("option", key, value))
        return self

    def saveAsTable(self, table):
        self.calls.append(("saveAsTable", table))
        return self


def _stub_df():
    return SimpleNamespace(write=_RecordingWriter())


def test_valid_arguments_drive_delta_replace_write():
    df = _stub_df()

    write_snapshot(df, VALID_TABLE, VALID_CITY, VALID_DATE, "_city", "_snapshot_date")

    calls = df.write.calls
    assert ("format", "delta") in calls
    assert ("mode", "overwrite") in calls
    assert (
        "option",
        "replaceWhere",
        "_city = 'toronto' AND _snapshot_date = '2026-09-16'",
    ) in calls
    assert calls[-1] == ("saveAsTable", VALID_TABLE)


def test_city_with_uppercase_is_rejected():
    with pytest.raises(ValueError, match="Unsafe city value"):
        write_snapshot(
            _stub_df(), VALID_TABLE, "Toronto", VALID_DATE, "_city", "_snapshot_date"
        )


def test_city_with_sql_injection_is_rejected():
    with pytest.raises(ValueError, match="Unsafe city value"):
        write_snapshot(
            _stub_df(),
            VALID_TABLE,
            "toronto' OR '1'='1",
            VALID_DATE,
            "_city",
            "_snapshot_date",
        )


def test_non_iso_date_is_rejected():
    with pytest.raises(ValueError):
        write_snapshot(
            _stub_df(), VALID_TABLE, VALID_CITY, "2026/09/16", "_city", "_snapshot_date"
        )


def test_two_part_table_is_rejected():
    with pytest.raises(ValueError, match="Expected catalog.schema.table"):
        write_snapshot(
            _stub_df(),
            "bronze.table",
            VALID_CITY,
            VALID_DATE,
            "_city",
            "_snapshot_date",
        )


def test_four_part_table_is_rejected():
    with pytest.raises(ValueError, match="Expected catalog.schema.table"):
        write_snapshot(
            _stub_df(), "a.b.c.d", VALID_CITY, VALID_DATE, "_city", "_snapshot_date"
        )


def test_table_with_unsafe_identifier_is_rejected():
    with pytest.raises(ValueError, match="Expected catalog.schema.table"):
        write_snapshot(
            _stub_df(),
            "trip-pilot.bronze.table",
            VALID_CITY,
            VALID_DATE,
            "_city",
            "_snapshot_date",
        )


def test_unsafe_city_column_is_rejected():
    with pytest.raises(ValueError, match="Unsafe column name"):
        write_snapshot(
            _stub_df(),
            VALID_TABLE,
            VALID_CITY,
            VALID_DATE,
            "city name",
            "_snapshot_date",
        )


def test_unsafe_snapshot_column_is_rejected():
    with pytest.raises(ValueError, match="Unsafe column name"):
        write_snapshot(
            _stub_df(), VALID_TABLE, VALID_CITY, VALID_DATE, "_city", "1_date"
        )


def test_hyphenated_city_is_allowed():
    # The city pattern deliberately accepts lowercase hyphens and
    # underscores, so future multi-word city slugs stay valid.
    df = _stub_df()

    write_snapshot(
        df, VALID_TABLE, "toronto-west", VALID_DATE, "_city", "_snapshot_date"
    )

    assert df.write.calls[-1] == ("saveAsTable", VALID_TABLE)
