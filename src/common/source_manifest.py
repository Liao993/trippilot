"""Source-file manifest: identity, metadata validation and state rules.

F04.1. Pure Python: no Spark, Databricks, network access or credentials
are needed. Every acquired source file gets one immutable manifest
record keyed by a deterministic source_file_id - the SHA-256 over the
source identity, version, file type and content hash - so an exact
same-file retry resolves to the same record (idempotent), while a
corrected file (different SHA-256) becomes a new record; existing
records are never overwritten.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.provenance import build_run_id

ALLOWED_PROCESSING_STATES = ("registered", "validated", "landed", "failed")
VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "registered": ("validated", "failed"),
    "validated": ("landed", "failed"),
    "landed": (),
    "failed": (),
}
SUPPORTED_FILE_TYPES = ("csv", "csv.gz", "tsv", "json", "geojson", "zip", "parquet")
DEFAULT_MAX_BYTE_SIZE = 2 * 1024**3  # 2 GiB
MAX_ERROR_MESSAGE_LENGTH = 500

SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"dapi[0-9a-f]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"shpat_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
)

REQUIRED_RECORD_FIELDS = (
    "source_file_id",
    "source_family",
    "source_entity_id",
    "source_version",
    "file_type",
    "source_url",
    "retrieved_at_utc",
    "file_hash_sha256",
    "byte_size",
    "schema_version",
    "license",
    "attribution",
    "source_path",
    "run_id",
    "processing_state",
)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_valid_utc_timestamp(value: str) -> bool:
    if not UTC_TIMESTAMP_PATTERN.match(value):
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def sanitize_error_message(message: str) -> str:
    """Redact common credential patterns and cap the message length."""
    sanitized = str(message)
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("***REDACTED***", sanitized)
    return sanitized[:MAX_ERROR_MESSAGE_LENGTH]


def build_source_file_id(
    source_family: str,
    source_entity_id: str,
    source_version: str,
    file_type: str,
    file_hash_sha256: str,
) -> str:
    """Return the deterministic manifest ID for one source file identity."""
    canonical = f"{source_family}|{source_entity_id}|{source_version}|{file_type}|{file_hash_sha256}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_file_hash_sha256(path: str | Path) -> str:
    """Return the SHA-256 hex digest of the exact file bytes (streamed)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_source_file(
    path: str | Path,
    file_type: str,
    max_byte_size: int = DEFAULT_MAX_BYTE_SIZE,
) -> dict[str, Any]:
    """Verify a source file is acquirable; return its hash and byte size.

    Checks that the file exists, is a regular file, is non-empty, is
    within the byte limit, and has a supported file type. Raises
    ValueError with an actionable message on any problem.
    """
    source = Path(path)
    if not _is_nonempty_string(file_type):
        raise ValueError("file_type is required to inspect a source file")
    if file_type not in SUPPORTED_FILE_TYPES:
        raise ValueError(
            f"Unsupported file type {file_type!r}; expected one of: "
            + ", ".join(SUPPORTED_FILE_TYPES)
        )
    if not source.exists():
        raise ValueError(f"{source}: source file not found")
    if not source.is_file():
        raise ValueError(f"{source}: not a regular file")
    byte_size = source.stat().st_size
    if byte_size == 0:
        raise ValueError(f"{source}: source file is empty")
    if byte_size > max_byte_size:
        raise ValueError(
            f"{source}: {byte_size} bytes exceeds the {max_byte_size}-byte limit"
        )
    return {
        "file_hash_sha256": compute_file_hash_sha256(source),
        "byte_size": byte_size,
    }


def validate_source_metadata(record: Any) -> list[str]:
    """Return every manifest metadata problem; each message names the field."""
    if not isinstance(record, dict):
        return ["Manifest record must be a mapping"]

    errors: list[str] = []
    for field in REQUIRED_RECORD_FIELDS:
        if field == "byte_size":
            continue
        if not _is_nonempty_string(record.get(field)):
            errors.append(f"Missing required manifest field: {field}")

    file_type = record.get("file_type")
    if _is_nonempty_string(file_type) and file_type not in SUPPORTED_FILE_TYPES:
        errors.append(
            f"Unsupported file type {file_type!r}; expected one of: "
            + ", ".join(SUPPORTED_FILE_TYPES)
        )

    source_url = record.get("source_url")
    if _is_nonempty_string(source_url) and not str(source_url).startswith(
        ("https://", "http://")
    ):
        errors.append("source_url must start with https:// or http://")

    retrieved = record.get("retrieved_at_utc")
    if _is_nonempty_string(retrieved) and not _is_valid_utc_timestamp(str(retrieved)):
        errors.append(
            "retrieved_at_utc must be an ISO-8601 UTC timestamp like 2026-11-13T18:00:00Z"
        )

    file_hash = record.get("file_hash_sha256")
    if _is_nonempty_string(file_hash) and not SHA256_HEX_PATTERN.match(str(file_hash)):
        errors.append(
            "file_hash_sha256 must be a 64-character lowercase SHA-256 hex digest"
        )

    byte_size = record.get("byte_size")
    if byte_size is None:
        errors.append("Missing required manifest field: byte_size")
    elif (
        isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size <= 0
    ):
        errors.append("byte_size must be a positive integer")

    state = record.get("processing_state")
    if _is_nonempty_string(state) and state not in ALLOWED_PROCESSING_STATES:
        errors.append(
            f"Invalid processing_state {state!r}; expected one of: "
            + ", ".join(ALLOWED_PROCESSING_STATES)
        )

    landing_path = record.get("landing_path")
    if _is_nonempty_string(landing_path) and not str(landing_path).startswith(
        "/Volumes/"
    ):
        errors.append(
            "landing_path must be a Unity Catalog Volume path starting with /Volumes/"
        )
    if state == "landed" and not _is_nonempty_string(landing_path):
        errors.append("landing_path is required when processing_state is landed")

    error_message = record.get("error_message")
    if state == "failed" and not _is_nonempty_string(error_message):
        errors.append("error_message is required when processing_state is failed")
    if _is_nonempty_string(error_message):
        if state != "failed":
            errors.append(
                "error_message is only allowed when processing_state is failed"
            )
        if any(pattern.search(str(error_message)) for pattern in SECRET_PATTERNS):
            errors.append(
                "error_message appears to contain a credential; sanitize it first"
            )

    return errors


def validate_state_transition(from_state: str | None, to_state: str) -> None:
    """Raise ValueError when a processing-state transition is unsupported."""
    if to_state not in ALLOWED_PROCESSING_STATES:
        raise ValueError(f"Unknown processing_state: {to_state!r}")
    if from_state is None:
        if to_state != "registered":
            raise ValueError("A new manifest record must start in the registered state")
        return
    if from_state not in ALLOWED_PROCESSING_STATES:
        raise ValueError(f"Unknown processing_state: {from_state!r}")
    allowed = VALID_TRANSITIONS[from_state]
    if to_state not in allowed:
        raise ValueError(
            f"Unsupported transition: {from_state} -> {to_state}; allowed from "
            f"{from_state!r}: "
            + (", ".join(allowed) if allowed else "none (terminal state)")
        )


def apply_state_transition(
    record: dict[str, Any],
    to_state: str,
    error_message: str | None = None,
    landing_path: str | None = None,
) -> dict[str, Any]:
    """Return a NEW record copy in to_state; the original stays unchanged."""
    validate_state_transition(record.get("processing_state"), to_state)

    updated = dict(record)
    if to_state == "failed":
        if not _is_nonempty_string(error_message):
            raise ValueError(
                "error_message is required when transitioning to the failed state"
            )
        updated["error_message"] = sanitize_error_message(str(error_message))
    else:
        updated.pop("error_message", None)
    if to_state == "landed":
        if not _is_nonempty_string(landing_path):
            raise ValueError(
                "landing_path is required when transitioning to the landed state"
            )
        updated["landing_path"] = str(landing_path)
    updated["processing_state"] = to_state

    errors = validate_source_metadata(updated)
    if errors:
        raise ValueError("Invalid source manifest metadata:\n- " + "\n- ".join(errors))
    return updated


def build_manifest_record(
    source_metadata: dict[str, Any],
    file_path: str | Path,
    run_id: str | None = None,
    max_byte_size: int = DEFAULT_MAX_BYTE_SIZE,
) -> dict[str, Any]:
    """Validate a source file and its metadata; return a registered record.

    source_metadata supplies the caller-known fields (source_family,
    source_entity_id, source_version, file_type, source_url,
    retrieved_at_utc, schema_version, license, attribution,
    source_path). The file facts (SHA-256, byte size), the deterministic
    source_file_id, the run_id (reusing the provenance helper when not
    supplied) and processing_state=registered are added here. Raises
    ValueError listing every problem found.
    """
    if not isinstance(source_metadata, dict):
        raise TypeError("source_metadata must be a mapping")

    facts = inspect_source_file(
        file_path, source_metadata.get("file_type"), max_byte_size=max_byte_size
    )

    record = dict(source_metadata)
    record.update(facts)
    record["run_id"] = run_id if _is_nonempty_string(run_id) else build_run_id()
    record["processing_state"] = "registered"
    record["source_file_id"] = build_source_file_id(
        str(record.get("source_family", "")),
        str(record.get("source_entity_id", "")),
        str(record.get("source_version", "")),
        str(record.get("file_type", "")),
        str(record.get("file_hash_sha256", "")),
    )

    errors = validate_source_metadata(record)
    if errors:
        raise ValueError("Invalid source manifest metadata:\n- " + "\n- ".join(errors))
    return record
