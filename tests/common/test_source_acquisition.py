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
    # Mirror the production Volume layout: _staging and the landed
    # family folders are siblings beneath one source root.
    root = tmp_path / "source_files"
    root.mkdir(exist_ok=True)
    return root


def _staged(tmp_path, name="listings.csv.gz", text=CSV_GZ_TEXT):
    return _write_gzip(
        _source_root(tmp_path) / "_staging" / "insideairbnb" / "toronto" / name, text
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
    source = _staged(tmp_path)
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
    source = _staged(tmp_path)
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
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    assert record["source_path"] == str(source)
    assert record["landing_path"].startswith(str(landing_root))
    assert len(record["file_hash_sha256"]) == 64
    assert record["byte_size"] == source.stat().st_size
    assert record["run_id"]
    assert record["processing_state"] == "landed"
    assert record["source_file_id"]


def test_original_staged_file_is_left_untouched(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    before = source.read_bytes()

    _acquire(source, landing_root)

    assert source.is_file()
    assert source.read_bytes() == before


def test_same_content_retry_is_idempotent(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    second = _acquire(source, landing_root)

    version_dir = Path(first["landing_path"]).parent
    assert second["landing_path"] == first["landing_path"]
    assert second["source_file_id"] == first["source_file_id"]
    assert second["processing_state"] == "landed"
    assert len(list(version_dir.iterdir())) == 1


def test_changed_content_lands_as_a_distinct_file(tmp_path):
    source = _staged(tmp_path, text=CSV_GZ_TEXT)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    # A corrected file replaces the staged copy with new bytes.
    _write_gzip(source, text="id,name\n1,gamma\n")
    second = _acquire(source, landing_root)

    assert second["landing_path"] != first["landing_path"]
    assert Path(first["landing_path"]).is_file()
    assert Path(second["landing_path"]).is_file()
    assert len(list(Path(first["landing_path"]).parent.iterdir())) == 2


def test_landed_file_is_never_overwritten(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    first = _acquire(source, landing_root)

    tampered = Path(first["landing_path"])
    tampered.write_bytes(b"tampered content")
    with pytest.raises(ValueError, match="never overwritten"):
        _acquire(source, landing_root)

    assert tampered.read_bytes() == b"tampered content"


def test_interrupted_copy_leaves_no_final_or_temp_file(tmp_path, monkeypatch):
    source = _staged(tmp_path)
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
    source = _staged(tmp_path)
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
    missing = landing_root / "_staging" / "insideairbnb" / "toronto" / "missing.csv.gz"

    with pytest.raises(ValueError, match="source file not found"):
        _acquire(missing, landing_root)


def test_empty_source_file_is_rejected(tmp_path):
    source = _staged(tmp_path)
    source.write_bytes(b"")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="source file is empty"):
        _acquire(source, landing_root)


def test_oversized_source_file_is_rejected(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="bytes exceeds the"):
        _acquire(source, landing_root, max_byte_size=4)


def test_file_type_without_acquisition_support_is_rejected(tmp_path):
    source = _staged(tmp_path, name="listings.tsv")
    source.write_bytes(b"id\tname\n1\talpha\n")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "tsv"

    with pytest.raises(ValueError, match="Acquisition currently supports only"):
        _acquire(source, landing_root, metadata=metadata)


def test_signature_mismatch_is_rejected(tmp_path):
    source = _staged(tmp_path)
    source.write_bytes(b"not gzip at all")  # plain text inside a .csv.gz name
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="file signature"):
        _acquire(source, landing_root)


# ---------------------------------------------------------------------------
# Plain csv and geojson acquisition (F07.1 D3)
# ---------------------------------------------------------------------------

GEOJSON_TEXT = (
    '{"type": "FeatureCollection", "features": ['
    '{"type": "Feature", "properties": {"neighbourhood": "Agincourt", '
    '"neighbourhood_group": ""}, "geometry": {"type": "MultiPolygon", '
    '"coordinates": [[[[0.0, 0.0]]]]}}'
    "]}"
)


def _staged_text(tmp_path, name, text):
    path = _source_root(tmp_path) / "_staging" / "insideairbnb" / "toronto" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_plain_csv_lands_with_hash_versioned_name(tmp_path):
    source = _staged_text(
        tmp_path,
        "neighbourhoods.csv",
        "neighbourhood_group,neighbourhood\n,Agincourt\n",
    )
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "csv"

    record = _acquire(source, landing_root, metadata=metadata)

    expected = (
        landing_root
        / "insideairbnb"
        / "toronto"
        / "2026-09-16"
        / f"neighbourhoods__{record['file_hash_sha256'][:12]}.csv"
    )
    assert record["landing_path"] == str(expected)
    assert record["processing_state"] == "landed"
    assert (
        Path(record["landing_path"])
        .read_text(encoding="utf-8")
        .startswith("neighbourhood_group")
    )


def test_plain_csv_retry_is_idempotent(tmp_path):
    source = _staged_text(tmp_path, "listings.csv", "id,name\n1,alpha\n")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "csv"

    first = _acquire(source, landing_root, metadata=metadata)
    second = _acquire(source, landing_root, metadata=metadata)

    assert second["source_file_id"] == first["source_file_id"]
    assert second["landing_path"] == first["landing_path"]
    assert second["processing_state"] == "landed"
    assert len(list(Path(first["landing_path"]).parent.iterdir())) == 1


def test_gzip_bytes_declared_as_csv_are_rejected(tmp_path):
    # A gzip fixture under a .csv name: the plain-csv validator must
    # catch the mislabeled compression instead of landing it.
    source = _staged(tmp_path, name="listings.csv")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "csv"

    with pytest.raises(ValueError, match="gzip-compressed"):
        _acquire(source, landing_root, metadata=metadata)


def test_headerless_plain_csv_is_rejected(tmp_path):
    source = _staged_text(tmp_path, "listings.csv", "\n1,alpha\n")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "csv"

    with pytest.raises(ValueError, match="no header line"):
        _acquire(source, landing_root, metadata=metadata)


def test_geojson_lands_and_retries_idempotently(tmp_path):
    source = _staged_text(tmp_path, "neighbourhoods.geojson", GEOJSON_TEXT)
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "geojson"

    first = _acquire(source, landing_root, metadata=metadata)
    second = _acquire(source, landing_root, metadata=metadata)

    expected = (
        landing_root
        / "insideairbnb"
        / "toronto"
        / "2026-09-16"
        / f"neighbourhoods__{first['file_hash_sha256'][:12]}.geojson"
    )
    assert first["landing_path"] == str(expected)
    assert second["source_file_id"] == first["source_file_id"]
    assert second["landing_path"] == first["landing_path"]
    assert second["processing_state"] == "landed"
    assert len(list(Path(first["landing_path"]).parent.iterdir())) == 1


def test_invalid_json_geojson_is_rejected(tmp_path):
    source = _staged_text(tmp_path, "neighbourhoods.geojson", "{not json")
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "geojson"

    with pytest.raises(ValueError, match="not readable as JSON"):
        _acquire(source, landing_root, metadata=metadata)


def test_non_feature_collection_geojson_is_rejected(tmp_path):
    source = _staged_text(
        tmp_path, "neighbourhoods.geojson", '{"type": "Polygon", "coordinates": []}'
    )
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "geojson"

    with pytest.raises(ValueError, match="FeatureCollection"):
        _acquire(source, landing_root, metadata=metadata)


def test_features_not_a_list_is_rejected(tmp_path):
    source = _staged_text(
        tmp_path,
        "neighbourhoods.geojson",
        '{"type": "FeatureCollection", "features": {}}',
    )
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["file_type"] = "geojson"

    with pytest.raises(ValueError, match="features"):
        _acquire(source, landing_root, metadata=metadata)


def test_source_outside_approved_roots_is_rejected(tmp_path):
    source = _write_gzip(tmp_path / "elsewhere" / "listings.csv.gz")
    landing_root = _source_root(tmp_path)

    with pytest.raises(ValueError, match="not within an approved staging location"):
        _acquire(source, landing_root)


def test_explicitly_approved_local_path_is_accepted(tmp_path):
    source = _write_gzip(tmp_path / "approved-local" / "listings.csv.gz")
    landing_root = _source_root(tmp_path)

    record = _acquire(
        source, landing_root, approved_staging_roots=[tmp_path / "approved-local"]
    )

    assert Path(record["landing_path"]).is_file()


def test_unsafe_source_family_is_rejected(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    metadata = _metadata(source)
    metadata["source_family"] = "../evil"

    with pytest.raises(ValueError, match="safe path segment"):
        _acquire(source, landing_root, metadata=metadata)


def test_filename_must_match_the_declared_file_type(tmp_path):
    source = _staged(tmp_path, name="listings.zip")
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


# ---------------------------------------------------------------------------
# Post-landing staging cleanup (pre-F07 T09)
# ---------------------------------------------------------------------------


def test_cleanup_staged_removes_staged_copy_after_landing(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root, cleanup_staged=True)

    assert record["processing_state"] == "landed"
    assert not source.exists()
    assert Path(record["landing_path"]).is_file()


def test_cleanup_staged_is_opt_in_by_default(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    assert record["processing_state"] == "landed"
    assert source.is_file()


def test_cleanup_staged_removes_staged_copy_on_idempotent_retry(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    first = _acquire(source, landing_root)
    second = _acquire(source, landing_root, cleanup_staged=True)

    assert second["source_file_id"] == first["source_file_id"]
    assert second["processing_state"] == "landed"
    assert not source.exists()


def test_cleanup_keeps_staged_copy_when_landed_object_is_corrupted(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)
    Path(record["landing_path"]).write_bytes(b"corrupted")

    with pytest.raises(ValueError) as excinfo:
        acquisition.cleanup_staged_source_file(
            source, record, (landing_root / "_staging",)
        )

    assert "does not match" in str(excinfo.value)
    assert source.is_file()


def test_cleanup_rejects_paths_outside_approved_staging_roots(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)

    record = _acquire(source, landing_root)

    with pytest.raises(ValueError) as excinfo:
        acquisition.cleanup_staged_source_file(
            source, record, (tmp_path / "other_staging",)
        )

    assert "staging" in str(excinfo.value)
    assert source.is_file()
