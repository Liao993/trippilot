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


def test_manifest_backed_fields_are_optional():
    base = build_provenance_columns(
        source="insideairbnb",
        city="toronto",
        snapshot_date="2026-09-16",
        raw_path="/Volumes/dev/bronze/insideairbnb/landed/listings__abc.csv.gz",
        run_id="run-1",
    )
    assert set(base) == {
        "source",
        "city",
        "snapshot_date",
        "raw_path",
        "run_id",
        "ingested_at_utc",
    }

    extended = build_provenance_columns(
        source="insideairbnb",
        city="toronto",
        snapshot_date="2026-09-16",
        raw_path="/Volumes/dev/bronze/insideairbnb/landed/listings__abc.csv.gz",
        run_id="run-1",
        source_file_id="a" * 64,
        file_hash_sha256="b" * 64,
    )
    assert extended["source_file_id"] == "a" * 64
    assert extended["file_hash_sha256"] == "b" * 64
    assert set(extended) - set(base) == {"source_file_id", "file_hash_sha256"}
