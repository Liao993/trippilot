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


from src.common.provenance import build_provenance_columns, build_run_id


def test_build_run_id_is_unique():
    assert build_run_id() != build_run_id()


def test_build_provenance_columns():
    result = build_provenance_columns(
        source="insideairbnb",
        city="toronto",
        snapshot_date="2026-09-16",
        raw_path="/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz",
        run_id="test-run",
    )

    assert result["source"] == "insideairbnb"
    assert result["city"] == "toronto"
    assert result["snapshot_date"] == "2026-09-16"
    assert result["run_id"] == "test-run"
    assert result["raw_path"].endswith("listings.csv.gz")
    assert "ingested_at_utc" in result
