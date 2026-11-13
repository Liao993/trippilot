"""Fixture-based tests for the source-file manifest (F04.1).

Uses small synthetic files written to pytest's tmp_path. No Spark,
Volume, network or credentials are needed. The YAML contract in
contracts/ops/source_file_manifest.yml is cross-checked against the
module's rules so the two can never drift apart.
"""

import hashlib
import sys
from pathlib import Path

import yaml

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

from src.common.source_manifest import (
    ALLOWED_PROCESSING_STATES,
    REQUIRED_RECORD_FIELDS,
    SUPPORTED_FILE_TYPES,
    VALID_TRANSITIONS,
    apply_state_transition,
    build_manifest_record,
    build_source_file_id,
    validate_source_metadata,
    validate_state_transition,
)

FILE_CONTENT = b"id,name\n1,alpha\n2,beta\n"


def _write_file(tmp_path, name="listings.csv.gz", content=FILE_CONTENT):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _valid_metadata():
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
        "source_path": (
            "/Volumes/trippilot_dev/bronze/source_files/insideairbnb/"
            "toronto/listings.csv.gz"
        ),
    }


def _built_record():
    return {
        **_valid_metadata(),
        "source_file_id": "a" * 64,
        "file_hash_sha256": "b" * 64,
        "byte_size": 21,
        "run_id": "run-1",
        "processing_state": "registered",
    }


def test_valid_source_file_produces_complete_manifest_record(tmp_path):
    path = _write_file(tmp_path)

    record = build_manifest_record(_valid_metadata(), path, run_id="run-1")

    assert record["processing_state"] == "registered"
    assert record["run_id"] == "run-1"
    assert record["byte_size"] == len(FILE_CONTENT)
    assert record["file_hash_sha256"] == hashlib.sha256(FILE_CONTENT).hexdigest()


def test_manifest_record_contains_exactly_the_contract_fields(tmp_path):
    path = _write_file(tmp_path)

    record = build_manifest_record(_valid_metadata(), path)

    # Optional fields (landing_path, error_message) are deliberately not
    # set on a fresh registered record; they appear only on transition.
    assert set(record) == set(REQUIRED_RECORD_FIELDS)
    assert "landing_path" not in record
    assert "error_message" not in record


def test_run_id_defaults_to_the_provenance_helper(tmp_path):
    path = _write_file(tmp_path)

    record = build_manifest_record(_valid_metadata(), path)

    assert isinstance(record["run_id"], str) and record["run_id"] != ""


def test_hash_is_repeatable_for_identical_bytes(tmp_path):
    first = _write_file(tmp_path / "a", "one.csv.gz")
    second = _write_file(tmp_path / "b", "two.csv.gz")

    record_a = build_manifest_record(_valid_metadata(), first)
    record_b = build_manifest_record(_valid_metadata(), second)

    assert record_a["file_hash_sha256"] == record_b["file_hash_sha256"]
    assert record_a["source_file_id"] == record_b["source_file_id"]


def test_hash_changes_when_bytes_change(tmp_path):
    path = _write_file(tmp_path, content=b"id,name\n1,alpha\n")

    record = build_manifest_record(_valid_metadata(), path)

    assert record["file_hash_sha256"] != hashlib.sha256(FILE_CONTENT).hexdigest()
    assert (
        record["file_hash_sha256"] == hashlib.sha256(b"id,name\n1,alpha\n").hexdigest()
    )


def test_same_identity_version_type_and_hash_produce_same_id():
    args = ("insideairbnb", "toronto", "2026-09-16", "csv.gz", "b" * 64)

    assert build_source_file_id(*args) == build_source_file_id(*args)


def test_different_hash_produces_a_separate_id():
    base = ("insideairbnb", "toronto", "2026-09-16", "csv.gz")

    assert build_source_file_id(*base, "b" * 64) != build_source_file_id(
        *base, "c" * 64
    )


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="source file not found"):
        build_manifest_record(_valid_metadata(), tmp_path / "missing.csv.gz")


def test_directory_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="not a regular file"):
        build_manifest_record(_valid_metadata(), tmp_path)


def test_empty_file_is_rejected(tmp_path):
    path = _write_file(tmp_path, content=b"")

    with pytest.raises(ValueError, match="source file is empty"):
        build_manifest_record(_valid_metadata(), path)


def test_oversized_file_is_rejected(tmp_path):
    path = _write_file(tmp_path)

    with pytest.raises(ValueError, match="bytes exceeds the"):
        build_manifest_record(_valid_metadata(), path, max_byte_size=4)


def test_unsupported_file_type_is_rejected(tmp_path):
    path = _write_file(tmp_path, name="payload.exe")
    metadata = _valid_metadata()
    metadata["file_type"] = "exe"

    with pytest.raises(ValueError, match="Unsupported file type"):
        build_manifest_record(metadata, path)


def test_missing_license_is_rejected(tmp_path):
    path = _write_file(tmp_path)
    metadata = _valid_metadata()
    del metadata["license"]

    with pytest.raises(ValueError) as excinfo:
        build_manifest_record(metadata, path)
    assert "license" in str(excinfo.value)


def test_missing_attribution_is_rejected(tmp_path):
    path = _write_file(tmp_path)
    metadata = _valid_metadata()
    del metadata["attribution"]

    with pytest.raises(ValueError) as excinfo:
        build_manifest_record(metadata, path)
    assert "attribution" in str(excinfo.value)


def test_missing_source_entity_id_is_rejected(tmp_path):
    path = _write_file(tmp_path)
    metadata = _valid_metadata()
    del metadata["source_entity_id"]

    with pytest.raises(ValueError) as excinfo:
        build_manifest_record(metadata, path)
    assert "source_entity_id" in str(excinfo.value)


def test_invalid_timestamp_is_rejected():
    for bad in ["2026-11-13 18:00", "2026-11-13T18:00:00", "not-a-date", "2026-11-13"]:
        record = _built_record()
        record["retrieved_at_utc"] = bad
        assert any("retrieved_at_utc" in e for e in validate_source_metadata(record))


def test_invalid_hash_format_is_rejected():
    record = _built_record()
    record["file_hash_sha256"] = "zz" * 32

    errors = validate_source_metadata(record)

    assert any("file_hash_sha256" in e for e in errors)


def test_non_http_source_url_is_rejected():
    record = _built_record()
    record["source_url"] = "ftp://example.com/data.csv.gz"

    errors = validate_source_metadata(record)

    assert any("source_url" in e for e in errors)


def test_valid_transition_chain_lands_the_record():
    record = _built_record()

    validated = apply_state_transition(record, "validated")
    landed = apply_state_transition(
        validated,
        "landed",
        landing_path="/Volumes/trippilot_dev/bronze/raw/file.csv.gz",
    )

    assert record["processing_state"] == "registered"  # original is unchanged
    assert landed["processing_state"] == "landed"
    assert landed["landing_path"] == "/Volumes/trippilot_dev/bronze/raw/file.csv.gz"


def test_skip_transition_is_rejected():
    record = _built_record()

    with pytest.raises(ValueError, match="Unsupported transition"):
        apply_state_transition(record, "landed", landing_path="/Volumes/x/y")


def test_terminal_states_reject_all_transitions():
    record = _built_record()
    validated = apply_state_transition(record, "validated")
    landed = apply_state_transition(
        validated, "landed", landing_path="/Volumes/trippilot_dev/bronze/raw/f"
    )
    failed = apply_state_transition(record, "failed", error_message="boom")

    for source_record, to_state in [(landed, "validated"), (failed, "registered")]:
        with pytest.raises(ValueError, match="Unsupported transition"):
            apply_state_transition(source_record, to_state)


def test_failed_transition_requires_error_message():
    record = _built_record()

    with pytest.raises(ValueError, match="error_message is required"):
        apply_state_transition(record, "failed")


def test_failed_transition_sanitizes_secrets():
    record = _built_record()

    failed = apply_state_transition(
        record,
        "failed",
        error_message="download failed after token dapi0123456789abcdef0123456789abcd expired",
    )

    assert "dapi0123456789abcdef0123456789abcd" not in failed["error_message"]
    assert "***REDACTED***" in failed["error_message"]


def test_error_message_is_only_allowed_in_failed_state():
    record = _built_record()
    record["error_message"] = "stale message"

    errors = validate_source_metadata(record)

    assert any("error_message is only allowed" in e for e in errors)


def test_landing_path_must_be_a_volume_path():
    record = _built_record()
    record["landing_path"] = "/tmp/not-a-volume.csv.gz"

    errors = validate_source_metadata(record)

    assert any("landing_path" in e for e in errors)


def test_landed_state_requires_landing_path():
    record = _built_record()
    record["processing_state"] = "landed"

    errors = validate_source_metadata(record)

    assert any("landing_path is required" in e for e in errors)


def test_new_record_must_start_registered():
    validate_state_transition(None, "registered")

    with pytest.raises(ValueError, match="must start in the registered state"):
        validate_state_transition(None, "validated")


def test_yaml_contract_matches_the_module_rules():
    with (ROOT / "contracts/ops/source_file_manifest.yml").open() as file:
        contract = yaml.safe_load(file)

    assert contract["states"] == list(ALLOWED_PROCESSING_STATES)
    assert contract["supported_file_types"] == list(SUPPORTED_FILE_TYPES)
    assert contract["valid_transitions"] == {
        state: list(targets) for state, targets in VALID_TRANSITIONS.items()
    }
    for field in REQUIRED_RECORD_FIELDS:
        assert contract["fields"][field]["required"] is True
    for optional in ["landing_path", "error_message"]:
        assert contract["fields"][optional]["required"] is False
