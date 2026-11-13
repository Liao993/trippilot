"""Temporary-directory tests for raw source acquisition (F04.2).

Uses small synthetic CSV.GZ fixtures under pytest's tmp_path. No Spark,
Volume, network or credentials are needed. Landing roots are temporary
directories approved via landing_path_prefixes, mirroring the /Volumes/
rule the manifest contract enforces in production.
"""

import gzip
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

import src.common.source_acquisition as acquisition
from src.common.source_acquisition import acquire_source_file

CSV_GZ_TEXT = "id,name\n1,alpha\n2,beta\n"


def _write_gzip(path, text=CSV_GZ_TEXT):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write(text)
    return path


def _source_root(tmp_path):
    # Mirror the production Volume layout: _incoming and the landed
    # family folders are siblings beneath one source root.
    root = tmp_path / "source_files"
    root.mkdir(exist_ok=True)
    return root


def _incoming(tmp_path, name="listings.csv.gz", text=CSV_GZ_TEXT):
    return _write_gzip(
        _source_root(tmp_path) / "_incoming" / "insideairbnb" / "toronto" / name, text
    )


def _metadata(source_file):
    return {
        "source_family": "insideairbnb",
        "source_entity_id": "toronto",
        "source_version": "2026-09-16",
        "file_type": "csv.gz",
        "source_url": "https://insideairbnb.com/get-the-data/",
        "retrieved_at_utc": "2026-11-13T18:00:00Z",
        "schema_version": "pending",
        "license": "CC0-1.0",
        "attribution": "Inside Airbnb (insideairbnb.com), CC0 1.0",
        "source_path": str(source_file),
    }


def _acquire(source_file, landing_root, metadata=None, **kwargs):
    return acquire_source_file(
        metadata if metadata is not None else _metadata(source_file),
        source_file,
        landing_root,
        landing_path_prefixes=(str(landing_root),),
        **kwargs,
    )


def test_valid_file_lands_under_a_hash_versioned_path(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    expected = (
        landing_root
        / "insideairbnb"
        / "toronto"
        / "2026-09-16"
        / f"listings__{record['file_hash_sha256'][:12]}.csv.gz"
    )
    assert record["landing_path"] == str(expected)
    assert expected.is_file()
    assert Path(record["landing_path"]).stat().st_size == source.stat().st_size
    assert record["processing_state"] == "landed"


def test_landed_bytes_match_the_source_exactly(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    with Path(record["landing_path"]).open("rb") as landed:
        landed_bytes = landed.read()
    with source.open("rb") as staged:
        staged_bytes = staged.read()
    assert landed_bytes == staged_bytes
    with gzip.open(record["landing_path"], "rt", encoding="utf-8") as landed:
        assert landed.read() == CSV_GZ_TEXT


def test_landed_record_carries_the_required_facts(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    assert record["source_path"] == str(source)
    assert record["landing_path"].startswith(str(landing_root))
    assert len(record["file_hash_sha256"]) == 64
    assert record["byte_size"] == source.stat().st_size
    assert record["run_id"]
    assert record["processing_state"] == "landed"
    assert record["source_file_id"]


def test_original_incoming_file_is_left_untouched(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)
    before = source.read_bytes()

    _acquire(source, landing_root)

    assert source.is_file()
    assert source.read_bytes() == before


def test_same_content_retry_is_idempotent(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    second = _acquire(source, landing_root)

    version_dir = Path(first["landing_path"]).parent
    assert second["landing_path"] == first["landing_path"]
    assert second["source_file_id"] == first["source_file_id"]
    assert second["processing_state"] == "landed"
    assert len(list(version_dir.iterdir())) == 1


def test_changed_content_lands_as_a_distinct_file(tmp_path):
    source = _incoming(tmp_path, text=CSV_GZ_TEXT)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    # A corrected file replaces the staged incoming copy with new bytes.
    _write_gzip(source, text="id,name\n1,gamma\n")
    second = _acquire(source, landing_root)

    assert second["landing_path"] != first["landing_path"]
    assert Path(first["landing_path"]).is_file()
    assert Path(second["landing_path"]).is_file()
    assert len(list(Path(first["landing_path"]).parent.iterdir())) == 2


def test_landed_file_is_never_overwritten(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    tampered = Path(first["landing_path"])
    tampered.write_bytes(b"tampered content")
    with pytest.raises(ValueError, match="never overwritten"):
        _acquire(source, landing_root)

    assert tampered.read_bytes() == b"tampered content"


def test_interrupted_copy_leaves_no_final_or_temp_file(tmp_path, monkeypatch):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)

    def broken_copy(src, dst):
        raise OSError("simulated interruption")

    monkeypatch.setattr(acquisition.shutil, "copyfile", broken_copy)
    with pytest.raises(OSError, match="simulated interruption"):
        _acquire(source, landing_root)

    version_dir = landing_root / "insideairbnb" / "toronto" / "2026-09-16"
    leftovers = list(version_dir.iterdir()) if version_dir.exists() else []
    assert leftovers == []

    monkeypatch.undo()
    record = _acquire(source, landing_root)
    assert Path(record["landing_path"]).is_file()


def test_stale_temp_file_from_a_crashed_run_does_not_block_landing(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)
    version_dir = landing_root / "insideairbnb" / "toronto" / "2026-09-16"
    version_dir.mkdir(parents=True)
    stale = version_dir / ".listings__deadbeefdead.csv.gz.tmp-abandoned"
    stale.write_bytes(b"partial")

    record = _acquire(source, landing_root)

    assert Path(record["landing_path"]).is_file()
    assert stale.is_file()  # untouched; acquisition uses its own temp file


def test_missing_source_file_is_rejected(tmp_path):
    landing_root = _source_root(tmp_path)
    missing = landing_root / "_incoming" / "insideairbnb" / "toronto" / "missing.csv.gz"

    with pytest.raises(ValueError, match="source file not found"):
        _acquire(missing, landing_root)


def test_empty_source_file_is_rejected(tmp_path):
    source = _incoming(tmp_path)
    source.write_bytes(b"")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="source file is empty"):
        _acquire(source, landing_root)


def test_oversized_source_file_is_rejected(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="bytes exceeds the"):
        _acquire(source, landing_root, max_byte_size=4)


def test_file_type_without_acquisition_support_is_rejected(tmp_path):
    source = _incoming(tmp_path, name="listings.csv")
    source.write_bytes(b"id,name\n1,alpha\n")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "csv"

    with pytest.raises(ValueError, match="Acquisition currently supports only"):
        _acquire(source, landing_root, metadata=metadata)


def test_signature_mismatch_is_rejected(tmp_path):
    source = _incoming(tmp_path)
    source.write_bytes(b"not gzip at all")  # plain text inside a .csv.gz name
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="file signature"):
        _acquire(source, landing_root)


def test_source_outside_approved_roots_is_rejected(tmp_path):
    source = _write_gzip(tmp_path / "elsewhere" / "listings.csv.gz")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="not within an approved incoming location"):
        _acquire(source, landing_root)


def test_explicitly_approved_local_path_is_accepted(tmp_path):
    source = _write_gzip(tmp_path / "approved-local" / "listings.csv.gz")
    landing_root = _source_root(tmp_path)

    record = _acquire(
        source, landing_root, approved_incoming_roots=[tmp_path / "approved-local"]
    )

    assert Path(record["landing_path"]).is_file()


def test_unsafe_source_family_is_rejected(tmp_path):
    source = _incoming(tmp_path)
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["source_family"] = "../evil"

    with pytest.raises(ValueError, match="safe path segment"):
        _acquire(source, landing_root, metadata=metadata)


def test_filename_must_match_the_declared_file_type(tmp_path):
    source = _incoming(tmp_path, name="listings.zip")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="must end with the declared file type"):
        _acquire(source, landing_root)


def test_failure_messages_redact_credential_patterns(tmp_path):
    # A synthetic credential, assembled at runtime from short fragments
    # so no token-shaped literal exists in the repository source:
    # secret scanners flag keyword-adjacent quoted values on sight.
    fake_credential = "dapi" + "0123" + "456789abcdef" + "0123456789abcd"
    source = _write_gzip(tmp_path / "elsewhere" / f"{fake_credential}.csv.gz")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError) as excinfo:
        _acquire(source, landing_root)

    assert fake_credential not in str(excinfo.value)
    assert "***REDACTED***" in str(excinfo.value)
