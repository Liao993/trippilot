"""Reprocessing and failure-isolation tests for acquisition (F04.3).

An InMemoryManifestStore mimics the Delta adapter's MERGE contract
(one row per source_file_id; existing rows update only the permitted
operational fields), so these tests prove reprocessing, controlled
retries and per-file failure isolation without Spark or production
tables.
"""

import gzip
import hashlib
from pathlib import Path

import pytest

from src.common import source_acquisition as acquisition
from src.common.source_acquisition import (
    acquire_source_file,
    reprocess_source_file,
    verify_existing_source_file,
    verify_landed_record,
)
from src.common.source_manifest import validate_source_metadata
from src.common.source_manifest_store import UPDATABLE_FIELDS

CSV_GZ_TEXT = "id,name\n1,alpha\n"


def _write_gzip(path, text=CSV_GZ_TEXT):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write(text)
    return path


def _source_root(tmp_path):
    root = tmp_path / "source_files"
    root.mkdir(exist_ok=True)
    return root


def _staged(tmp_path, name="listings.csv.gz", text=CSV_GZ_TEXT):
    return _write_gzip(
        _source_root(tmp_path) / "_staging" / "insideairbnb" / "toronto" / name,
        text,
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


class InMemoryManifestStore:
    """Mimics the Delta MERGE contract for tests: one row per
    source_file_id; an existing row updates only the operational
    fields, and a duplicate upsert can never append a second row."""

    def __init__(self, landing_path_prefixes):
        self.rows = {}
        self.upserts = []
        self.landing_path_prefixes = tuple(landing_path_prefixes)

    def upsert(self, record):
        errors = validate_source_metadata(
            record, landing_path_prefixes=self.landing_path_prefixes
        )
        if errors:
            raise ValueError(
                "Refusing to store invalid manifest record:\n- " + "\n- ".join(errors)
            )
        self.upserts.append(dict(record))
        key = record["source_file_id"]
        if key in self.rows:
            for field in UPDATABLE_FIELDS:
                self.rows[key][field] = record.get(field)
        else:
            self.rows[key] = dict(record)
        return record

    def read(self, source_file_id):
        row = self.rows.get(source_file_id)
        return dict(row) if row is not None else None

    def read_landed(self, source_file_id):
        record = self.read(source_file_id)
        if record is None:
            raise ValueError(f"{source_file_id}: no manifest record found in the store")
        if record.get("processing_state") != "landed":
            raise ValueError(
                f"{source_file_id}: manifest record state is "
                f"{record.get('processing_state')!r}, not landed"
            )
        if (
            not isinstance(record.get("landing_path"), str)
            or not record["landing_path"].strip()
        ):
            raise ValueError(f"{source_file_id}: landed record has no landing_path")
        return record


def _store(landing_root):
    return InMemoryManifestStore(landing_path_prefixes=(str(landing_root),))


def _acquire(source_file, landing_root, store, metadata=None):
    return acquire_source_file(
        metadata if metadata is not None else _metadata(source_file),
        source_file,
        landing_root,
        landing_path_prefixes=(str(landing_root),),
        manifest_store=store,
    )


def _identity(record):
    return {
        "source_family": record["source_family"],
        "source_entity_id": record["source_entity_id"],
        "source_version": record["source_version"],
        "file_type": record["file_type"],
        "file_hash_sha256": record["file_hash_sha256"],
    }


def test_successful_acquire_persists_a_landed_manifest_row(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)

    record = _acquire(source, landing_root, store)

    assert len(store.rows) == 1
    row = store.read(record["source_file_id"])
    assert row["processing_state"] == "landed"
    assert row["landing_path"] == record["landing_path"]
    assert Path(row["landing_path"]).is_file()
    # The attempt was visible from the registered state onwards.
    assert [r["processing_state"] for r in store.upserts] == ["registered", "landed"]


def test_duplicate_registration_is_idempotent_and_returns_existing(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    first = _acquire(source, landing_root, store)

    second = _acquire(source, landing_root, store)

    assert second["source_file_id"] == first["source_file_id"]
    assert second["run_id"] == first["run_id"]
    assert len(store.rows) == 1
    # The retry verified the landed object instead of copying again.
    assert len(store.upserts) == 2


def test_failed_attempt_is_visible_and_a_controlled_retry_lands(tmp_path, monkeypatch):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)

    def broken_copy(src, dst):
        raise OSError("simulated interruption")

    monkeypatch.setattr(acquisition.shutil, "copyfile", broken_copy)
    with pytest.raises(OSError, match="simulated interruption"):
        _acquire(source, landing_root, store)

    record_id = store.upserts[0]["source_file_id"]
    failed_row = store.read(record_id)
    assert failed_row["processing_state"] == "failed"
    assert "simulated interruption" in failed_row["error_message"]
    # F07.3-T01: a landing-copy interruption is classified acquisition,
    # distinct from a staged-content parse/schema problem.
    assert failed_row["error_type"] == "acquisition"

    monkeypatch.undo()
    retried = _acquire(source, landing_root, store)

    assert retried["source_file_id"] == record_id
    assert retried["processing_state"] == "landed"
    assert Path(retried["landing_path"]).is_file()
    # Controlled retry: failed -> registered -> landed through a full
    # re-validation, never a silent flip.
    assert [r["processing_state"] for r in store.upserts] == [
        "registered",
        "failed",
        "registered",
        "landed",
    ]
    assert len(store.rows) == 1
    # F07.3-T02: a successful retry clears the prior failure diagnostics.
    cleared = store.read(record_id)
    assert cleared["error_type"] is None
    assert cleared["error_message"] is None


def test_reprocess_resolves_the_landing_path_without_the_staged_file(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    landed = _acquire(source, landing_root, store)

    # Recovery scenario: the staged file is gone for good.
    source.unlink()

    record = reprocess_source_file(_identity(landed), store)

    assert record["landing_path"] == landed["landing_path"]
    assert Path(record["landing_path"]).is_file()
    assert record["processing_state"] == "landed"


def test_reprocess_never_copies_or_downloads(tmp_path, monkeypatch):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    landed = _acquire(source, landing_root, store)

    def forbidden_copy(src, dst):
        raise AssertionError("reprocessing must not copy or download files")

    monkeypatch.setattr(acquisition.shutil, "copyfile", forbidden_copy)

    record = reprocess_source_file(_identity(landed), store)

    assert Path(record["landing_path"]).is_file()


def test_verify_existing_checks_the_landed_hash_by_id(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    landed = _acquire(source, landing_root, store)

    verified = verify_existing_source_file(landed["source_file_id"], store)

    assert verified["landing_path"] == landed["landing_path"]

    tampered = Path(landed["landing_path"])
    tampered.write_bytes(b"tampered content")
    with pytest.raises(ValueError, match="does not match"):
        verify_existing_source_file(landed["source_file_id"], store)
    # A hash mismatch never overwrote or re-landed the raw object.
    assert tampered.read_bytes() == b"tampered content"


def test_reprocess_rejects_unknown_identity(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    landed = _acquire(source, landing_root, store)
    identity = _identity(landed)
    identity["file_hash_sha256"] = "d" * 64

    with pytest.raises(ValueError, match="no manifest record found"):
        reprocess_source_file(identity, store)


def test_reprocess_rejects_non_landed_records(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    record = _acquire(source, landing_root, store)
    store.rows[record["source_file_id"]]["processing_state"] = "validated"

    with pytest.raises(ValueError, match="not landed"):
        reprocess_source_file(_identity(record), store)


def test_reprocess_requires_the_full_identity(tmp_path):
    store = _store(_source_root(tmp_path))
    identity = {
        "source_family": "insideairbnb",
        "source_entity_id": "toronto",
        "source_version": "2026-09-16",
        "file_type": "csv.gz",
    }

    with pytest.raises(ValueError, match="file_hash_sha256"):
        reprocess_source_file(identity, store)


def test_verify_landed_record_rejects_size_and_missing_file_problems(tmp_path):
    source = _staged(tmp_path)
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    landed = _acquire(source, landing_root, store)

    wrong_size = dict(landed, byte_size=landed["byte_size"] + 1)
    with pytest.raises(ValueError, match="does not match the"):
        verify_landed_record(wrong_size)

    Path(landed["landing_path"]).unlink()
    with pytest.raises(ValueError, match="landed file not found"):
        verify_landed_record(landed)


def test_one_files_failure_never_changes_another_files_status(tmp_path):
    good = _staged(tmp_path, name="listings.csv.gz")
    bad = _staged(tmp_path, name="reviews.csv.gz")
    bad.write_bytes(b"plain text, not gzip")  # wrong signature
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)

    good_record = _acquire(good, landing_root, store, _metadata(good))
    row_before = store.read(good_record["source_file_id"])

    bad_metadata = _metadata(bad)
    bad_metadata["source_version"] = "2026-09-16"
    with pytest.raises(ValueError, match="file signature"):
        _acquire(bad, landing_root, store, bad_metadata)

    assert store.read(good_record["source_file_id"]) == row_before
    assert store.read(good_record["source_file_id"])["processing_state"] == "landed"
    # The failed file has its own visible row; the good one was untouched.
    bad_rows = [r for r in store.rows.values() if r["source_path"] == str(bad)]
    assert len(bad_rows) == 1
    assert bad_rows[0]["processing_state"] == "failed"
    assert "file signature" in bad_rows[0]["error_message"]
    # F07.3-T01: a staged-content problem is classified parse_or_schema.
    assert bad_rows[0]["error_type"] == "parse_or_schema"


def test_missing_staged_file_produces_no_manifest_row(tmp_path):
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    missing = landing_root / "_staging" / "insideairbnb" / "toronto" / "missing.csv.gz"

    with pytest.raises(ValueError, match="source file not found"):
        _acquire(missing, landing_root, store)

    assert store.rows == {}
    assert store.upserts == []


def test_plain_csv_without_header_fails_as_parse_or_schema(tmp_path):
    landing_root = _source_root(tmp_path)
    staged = (
        landing_root / "_staging" / "insideairbnb" / "toronto" / "neighbourhoods.csv"
    )
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text("\n", encoding="utf-8")
    store = _store(landing_root)
    metadata = _metadata(staged)
    metadata["file_type"] = "csv"

    with pytest.raises(ValueError, match="no header line"):
        _acquire(staged, landing_root, store, metadata)

    rows = [r for r in store.rows.values() if r["source_path"] == str(staged)]
    assert len(rows) == 1
    assert rows[0]["processing_state"] == "failed"
    assert rows[0]["error_type"] == "parse_or_schema"


def test_non_feature_collection_geojson_fails_as_parse_or_schema(tmp_path):
    landing_root = _source_root(tmp_path)
    staged = (
        landing_root
        / "_staging"
        / "insideairbnb"
        / "toronto"
        / "neighbourhoods.geojson"
    )
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text('{"type": "Feature"}', encoding="utf-8")
    store = _store(landing_root)
    metadata = _metadata(staged)
    metadata["file_type"] = "geojson"

    with pytest.raises(ValueError, match="FeatureCollection"):
        _acquire(staged, landing_root, store, metadata)

    rows = [r for r in store.rows.values() if r["source_path"] == str(staged)]
    assert len(rows) == 1
    assert rows[0]["processing_state"] == "failed"
    assert rows[0]["error_type"] == "parse_or_schema"


def test_landing_conflict_is_classified_acquisition(tmp_path):
    landing_root = _source_root(tmp_path)
    store = _store(landing_root)
    corrected = _staged(tmp_path, name="listings.csv.gz", text="id,name\n1,delta\n")

    # Plant stale bytes at the exact hash-versioned landing path this
    # corrected file will resolve to: the immutable-landing protection
    # must refuse to overwrite it and classify the refusal as an
    # acquisition (landing-side) failure, not a staged-content problem.
    corrected_hash = hashlib.sha256(corrected.read_bytes()).hexdigest()
    conflict_path = (
        landing_root
        / "insideairbnb"
        / "toronto"
        / "2026-09-16"
        / f"listings__{corrected_hash[:12]}.csv.gz"
    )
    conflict_path.parent.mkdir(parents=True, exist_ok=True)
    conflict_path.write_bytes(b"stale bytes under a familiar name")

    with pytest.raises(ValueError, match="already exists with different content"):
        _acquire(corrected, landing_root, store, _metadata(corrected))

    rows = [r for r in store.rows.values() if r["source_path"] == str(corrected)]
    assert len(rows) == 1
    assert rows[0]["processing_state"] == "failed"
    assert rows[0]["error_type"] == "acquisition"
