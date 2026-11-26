"""Tests for the shared per-dataset Bronze ingestion flow.

The orchestration (run_bronze_ingestion) needs a live Spark session and
is verified by the notebook drill (T12); these tests cover the pure,
CI-safe helpers exactly: the provenance-column mapping against the real
build_provenance_columns output, the string-preserving read options, the
dataset specs' environment-resolver keys (F07.4: physical catalog
separation, no _test suffixes), and the landed-source verification
dispatch. The run-control SQL builders now live in
src/common/ingestion_manifest.py and are covered by
tests/common/test_ingestion_manifest.py.
"""

import gzip
import json
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
    READ_OPTIONS,
    BronzeDatasetSpec,
    verify_and_inspect_source,
)
from src.common.environment import repo_root, resolve_table
from src.common.provenance import PROVENANCE_COLUMNS, build_provenance_columns


def test_repo_root_contains_project_layout():
    root = repo_root()

    assert (root / "src").is_dir()
    assert (root / "config").is_dir()
    assert (root / "contracts").is_dir()


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
    )

    assert spec.manifest_key == "source_manifest"
    assert spec.default_source_file_id == ""

    with pytest.raises(FrozenInstanceError):
        # frozen dataclass: assignment must fail
        spec.dataset = "other"

    # F07.4: the per-dataset control_key is gone - every run records
    # into the ONE shared ingestion manifest.
    with pytest.raises(TypeError):
        BronzeDatasetSpec(
            dataset="calendar",
            schema_label="calendar",
            contract_path="contracts/airbnb/bronze_calendar.yml",
            rules_key="bronze_calendar",
            bronze_key="calendar_bronze",
            control_key="calendar_control",
        )


@pytest.mark.parametrize(
    "spec_kwargs, bronze_table",
    [
        (
            {
                "dataset": "calendar",
                "schema_label": "calendar",
                "contract_path": "contracts/airbnb/bronze_calendar.yml",
                "rules_key": "bronze_calendar",
                "bronze_key": "calendar_bronze",
            },
            "airbnb_calendar_bronze",
        ),
        (
            {
                "dataset": "reviews",
                "schema_label": "reviews",
                "contract_path": "contracts/airbnb/bronze_reviews.yml",
                "rules_key": "bronze_reviews",
                "bronze_key": "reviews_bronze",
            },
            "airbnb_reviews_bronze",
        ),
        (
            {
                "dataset": "listings_summary",
                "schema_label": "summary-listings",
                "contract_path": "contracts/airbnb/bronze_listings_summary.yml",
                "rules_key": "bronze_listings_summary",
                "bronze_key": "listings_summary_bronze",
            },
            "airbnb_listings_summary_bronze",
        ),
        (
            {
                "dataset": "reviews_summary",
                "schema_label": "summary-reviews",
                "contract_path": "contracts/airbnb/bronze_reviews_summary.yml",
                "rules_key": "bronze_reviews_summary",
                "bronze_key": "reviews_summary_bronze",
            },
            "airbnb_reviews_summary_bronze",
        ),
        (
            {
                "dataset": "neighbourhoods",
                "schema_label": "neighbourhoods",
                "contract_path": "contracts/airbnb/bronze_neighbourhoods.yml",
                "rules_key": "bronze_neighbourhoods",
                "bronze_key": "neighbourhoods_bronze",
            },
            "airbnb_neighbourhoods_bronze",
        ),
        (
            {
                "dataset": "neighbourhood_geometry",
                "schema_label": "neighbourhood-geojson",
                "contract_path": "contracts/airbnb/bronze_neighbourhood_geometry.yml",
                "rules_key": "bronze_neighbourhood_geometry",
                "bronze_key": "neighbourhood_geometry_bronze",
            },
            "airbnb_neighbourhood_geometry_bronze",
        ),
    ],
)
def test_spec_destinations_resolve_by_catalog(spec_kwargs, bronze_table):
    """F07.4: test isolation is a separate catalog, same table names."""
    spec = BronzeDatasetSpec(**spec_kwargs)

    assert resolve_table(spec.bronze_key, "test") == (
        f"trippilot_test.bronze.{bronze_table}"
    )
    assert resolve_table(spec.bronze_key, "live") == (
        f"trippilot_dev.bronze.{bronze_table}"
    )
    assert resolve_table(spec.manifest_key, "test") == (
        "trippilot_test.ops.source_file_manifest"
    )
    assert resolve_table(spec.manifest_key, "live") == (
        "trippilot_dev.ops.source_file_manifest"
    )


def test_every_run_records_into_one_shared_ingestion_manifest():
    """F07.4: ONE shared manifest table per environment, no suffixes."""
    assert resolve_table("ingestion_manifest", "test") == (
        "trippilot_test.ops.ingestion_manifest"
    )
    assert resolve_table("ingestion_manifest", "live") == (
        "trippilot_dev.ops.ingestion_manifest"
    )


def test_spec_contract_files_exist():
    for contract_path in (
        "contracts/airbnb/bronze_calendar.yml",
        "contracts/airbnb/bronze_reviews.yml",
        "contracts/airbnb/bronze_listings_summary.yml",
        "contracts/airbnb/bronze_reviews_summary.yml",
        "contracts/airbnb/bronze_neighbourhoods.yml",
        "contracts/airbnb/bronze_neighbourhood_geometry.yml",
    ):
        assert (repo_root() / contract_path).is_file(), contract_path


# ---------------------------------------------------------------------------
# F07.2: landed-source verification and inspection dispatch by file type
# ---------------------------------------------------------------------------


def _record(path, file_type):
    return {"landing_path": str(path), "file_type": file_type}


def _write_gzip_csv(path, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as file:
        file.write(header + "\n1,alpha\n")
    return path


def _write_plain_csv(path, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n1,alpha\n", encoding="utf-8")
    return path


def _write_geojson(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"neighbourhood": "A", "neighbourhood_group": ""},
                        "geometry": {"type": "MultiPolygon", "coordinates": []},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_verify_and_inspect_source_dispatches_by_file_type(tmp_path):
    gz = _write_gzip_csv(tmp_path / "a.csv.gz", "id,name")
    plain = _write_plain_csv(tmp_path / "b.csv", "neighbourhood_group,neighbourhood")
    geo = _write_geojson(tmp_path / "c.geojson")

    gz_facts = verify_and_inspect_source(_record(gz, "csv.gz"), "calendar")
    plain_facts = verify_and_inspect_source(_record(plain, "csv"), "neighbourhoods")
    geo_facts = verify_and_inspect_source(
        _record(geo, "geojson"), "neighbourhood-geojson"
    )

    assert gz_facts["columns"] == ["id", "name"]
    assert plain_facts["columns"] == ["neighbourhood_group", "neighbourhood"]
    assert geo_facts["feature_count"] == 1
    assert geo_facts["columns"] == ["neighbourhood", "neighbourhood_group"]
    assert geo_facts["geometry_types"] == ["MultiPolygon"]


def test_verify_and_inspect_source_rejects_unsupported_file_types(tmp_path):
    plain = _write_plain_csv(tmp_path / "d.csv", "id,name")

    with pytest.raises(ValueError, match="Unsupported Bronze source file type"):
        verify_and_inspect_source(_record(plain, "parquet"), "listings")


def test_verify_and_inspect_source_rejects_corrupt_gzip(tmp_path):
    source = _write_gzip_csv(tmp_path / "a.csv.gz", "id,name")
    compressed = bytearray(source.read_bytes())
    compressed[-6] ^= 0xFF
    corrupted = tmp_path / "corrupt.csv.gz"
    corrupted.write_bytes(bytes(compressed))

    with pytest.raises(ValueError, match="not readable end-to-end"):
        verify_and_inspect_source(_record(corrupted, "csv.gz"), "calendar")
