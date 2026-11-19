"""Tests for the shared per-dataset Bronze ingestion flow.

The orchestration (run_bronze_ingestion) needs a live Spark session and
is verified by the notebook drill (T12); these tests cover the pure,
CI-safe helpers exactly: the control-row SQL builders (including SQL
literal escaping), the provenance-column mapping against the real
build_provenance_columns output, the string-preserving read options, and
the dataset specs' environment-resolver keys.
"""

import sys
from dataclasses import FrozenInstanceError
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

from src.airbnb.bronze_flow import (
    PROVENANCE_COLUMNS,
    READ_OPTIONS,
    BronzeDatasetSpec,
    build_control_insert_sql,
    build_control_success_sql,
    repo_root,
    sql_string_literal,
)
from src.common.environment import resolve_table
from src.common.provenance import build_provenance_columns

CONTROL_TABLE = "trippilot_dev.bronze.airbnb_calendar_ingestion_control_test"


def test_repo_root_contains_project_layout():
    root = repo_root()

    assert (root / "src").is_dir()
    assert (root / "config").is_dir()
    assert (root / "contracts").is_dir()


def test_sql_string_literal_quotes_and_escapes():
    assert sql_string_literal("toronto") == "'toronto'"
    assert sql_string_literal("o'brien") == "'o''brien'"


def test_build_control_insert_sql_with_null_prior():
    sql = build_control_insert_sql(
        CONTROL_TABLE,
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="run-1",
        started_at_utc="2026-11-19T10:00:00+00:00",
        source_file_id="abc123",
        prior_source_file_id=None,
        dataset="calendar",
    )

    assert sql == (
        f"INSERT INTO {CONTROL_TABLE} VALUES ("
        "'toronto', '2026-09-16', 'run-1', 'running', 0, "
        "'2026-11-19T10:00:00+00:00', NULL, NULL, 'abc123', NULL, 'calendar')"
    )


def test_build_control_insert_sql_with_prior_identity():
    sql = build_control_insert_sql(
        CONTROL_TABLE,
        city="toronto",
        snapshot_date="2026-09-16",
        run_id="run-2",
        started_at_utc="2026-11-19T11:00:00+00:00",
        source_file_id="def456",
        prior_source_file_id="abc123",
        dataset="calendar",
    )

    assert sql.endswith("'def456', 'abc123', 'calendar')")


def test_build_control_insert_sql_escapes_quotes():
    sql = build_control_insert_sql(
        CONTROL_TABLE,
        city="o'brien",
        snapshot_date="2026-09-16",
        run_id="run-3",
        started_at_utc="t",
        source_file_id="x",
        prior_source_file_id=None,
        dataset="reviews",
    )

    assert "'o''brien'" in sql


def test_build_control_success_sql_shape():
    sql = build_control_success_sql(
        CONTROL_TABLE,
        run_id="run-1",
        row_count=8048251,
        completed_at_utc="2026-11-19T10:05:00+00:00",
    )

    assert sql == (
        f"UPDATE {CONTROL_TABLE} SET status = 'success', "
        "row_count = 8048251, "
        "completed_at_utc = '2026-11-19T10:05:00+00:00', "
        "error_message = NULL WHERE run_id = 'run-1'"
    )


def test_provenance_columns_match_build_provenance_columns_keys():
    provenance = build_provenance_columns(
        source="insideairbnb",
        city="toronto",
        snapshot_date="2026-09-16",
        raw_path="/Volumes/dev/bronze/landed/calendar__abc.csv.gz",
        run_id="run-1",
        source_file_id="abc123",
        file_hash_sha256="deadbeef",
    )

    assert provenance["raw_path"].endswith("calendar__abc.csv.gz")
    assert {column.lstrip("_") for column in PROVENANCE_COLUMNS} == set(provenance)
    assert len(PROVENANCE_COLUMNS) == 8


def test_read_options_preserve_raw_strings():
    assert READ_OPTIONS == {
        "header": True,
        "inferSchema": False,
        "multiLine": True,
        "escape": '"',
    }


def test_spec_defaults():
    spec = BronzeDatasetSpec(
        dataset="calendar",
        schema_label="calendar",
        contract_path="contracts/airbnb/bronze_calendar.yml",
        rules_key="bronze_calendar",
        bronze_key="calendar_bronze",
        control_key="calendar_control",
    )

    assert spec.manifest_key == "source_manifest"
    assert spec.default_source_file_id == ""

    with pytest.raises(FrozenInstanceError):
        # frozen dataclass: assignment must fail
        spec.dataset = "other"


@pytest.mark.parametrize(
    "spec_kwargs, bronze_suffix, control_suffix",
    [
        (
            {
                "dataset": "calendar",
                "schema_label": "calendar",
                "contract_path": "contracts/airbnb/bronze_calendar.yml",
                "rules_key": "bronze_calendar",
                "bronze_key": "calendar_bronze",
                "control_key": "calendar_control",
            },
            "airbnb_calendar_bronze_test",
            "airbnb_calendar_ingestion_control_test",
        ),
        (
            {
                "dataset": "reviews",
                "schema_label": "reviews",
                "contract_path": "contracts/airbnb/bronze_reviews.yml",
                "rules_key": "bronze_reviews",
                "bronze_key": "reviews_bronze",
                "control_key": "reviews_control",
            },
            "airbnb_reviews_bronze_test",
            "airbnb_reviews_ingestion_control_test",
        ),
    ],
)
def test_spec_resolver_keys_isolate_in_test_mode(
    spec_kwargs, bronze_suffix, control_suffix
):
    spec = BronzeDatasetSpec(**spec_kwargs)

    assert resolve_table(spec.bronze_key, "test").endswith(bronze_suffix)
    assert resolve_table(spec.control_key, "test").endswith(control_suffix)
    assert resolve_table(spec.manifest_key, "test").endswith(
        "source_file_manifest_test"
    )


def test_spec_contract_files_exist():
    for contract_path in (
        "contracts/airbnb/bronze_calendar.yml",
        "contracts/airbnb/bronze_reviews.yml",
    ):
        assert (repo_root() / contract_path).is_file(), contract_path
