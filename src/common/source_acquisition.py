"""Raw source acquisition: safe validation and immutable landing (F04.2).

Takes a source file staged in an approved incoming location (a manual
Databricks UI upload to the source Volume's _incoming folder, or an
explicitly approved local staging path), validates it, hashes it, and
lands it once as an immutable, hash-versioned object beneath the
managed source Volume.

Pure filesystem logic: no Spark, no Bronze parsing, no outbound network.
An exact same-bytes retry is idempotent (it resolves to the existing
object), a corrected file with a different hash lands as a distinct
object, and a landed file is never overwritten. Failure messages are
actionable and redact credential patterns.
"""

import os
import re
import shutil
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.common.source_manifest import (
    DEFAULT_MAX_BYTE_SIZE,
    apply_state_transition,
    build_manifest_record,
    compute_file_hash_sha256,
    sanitize_error_message,
)

# Acquisition supports only file types whose byte signature is verified.
# Other manifest-supported types can be added once their validation
# behaviour is tested.
FILE_SIGNATURES: dict[str, bytes] = {"csv.gz": b"\x1f\x8b"}  # gzip magic
ACQUISITION_FILE_TYPES = tuple(FILE_SIGNATURES)

INCOMING_DIR_NAME = "_incoming"
LANDING_FILENAME_HASH_PREFIX_LENGTH = 12
SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validate_path_segment(value: Any, field: str) -> str:
    text = str(value)
    if not SAFE_SEGMENT_PATTERN.match(text):
        raise ValueError(
            f"{field} must be a safe path segment (letters, digits, dots, hyphens "
            f"or underscores, no separators): {text!r}"
        )
    return text


def _ensure_within(path: Path, roots: Sequence[Path], purpose: str) -> None:
    resolved = path.resolve()
    for root in roots:
        root_resolved = root.resolve()
        if resolved == root_resolved or root_resolved in resolved.parents:
            return
    listed = ", ".join(str(root) for root in roots)
    raise ValueError(
        f"{path}: source file is not within an approved {purpose} location "
        f"(approved: {listed})"
    )


def verify_file_signature(path: str | Path, file_type: str) -> None:
    """Reject a staged file whose leading bytes do not match its type."""
    signature = FILE_SIGNATURES[file_type]
    with Path(path).open("rb") as file:
        head = file.read(len(signature))
    if head != signature:
        raise ValueError(
            f"{path}: content does not match the {file_type} file signature "
            "(expected gzip magic bytes)"
        )


def build_landing_path(
    landing_root: str | Path,
    source_path: str | Path,
    record: dict[str, Any],
) -> Path:
    """Derive the immutable, hash-versioned landing path for one record."""
    file_type = record["file_type"]
    name = Path(source_path).name
    if not name.endswith(file_type):
        raise ValueError(
            f"{name}: filename must end with the declared file type {file_type!r}"
        )
    base = name[: -len(file_type)].rstrip(".")
    if not base:
        raise ValueError(f"{name}: cannot derive a base name for the landing filename")
    family = _validate_path_segment(record["source_family"], "source_family")
    entity = _validate_path_segment(record["source_entity_id"], "source_entity_id")
    version = _validate_path_segment(record["source_version"], "source_version")
    hash_prefix = record["file_hash_sha256"][:LANDING_FILENAME_HASH_PREFIX_LENGTH]
    return (
        Path(landing_root)
        / family
        / entity
        / version
        / f"{base}__{hash_prefix}.{file_type}"
    )


def _land(
    record: dict[str, Any],
    final_path: Path,
    landing_path_prefixes: Sequence[str],
) -> dict[str, Any]:
    validated = apply_state_transition(record, "validated")
    return apply_state_transition(
        validated,
        "landed",
        landing_path=str(final_path),
        landing_path_prefixes=landing_path_prefixes,
    )


def acquire_source_file(
    source_metadata: dict[str, Any],
    source_path: str | Path,
    landing_root: str | Path,
    approved_incoming_roots: Sequence[str | Path] | None = None,
    max_byte_size: int = DEFAULT_MAX_BYTE_SIZE,
    run_id: str | None = None,
    landing_path_prefixes: Sequence[str] = ("/Volumes/",),
) -> dict[str, Any]:
    """Validate a staged source file and land it immutably; return the record.

    The source file must live under an approved incoming location (by
    default <landing_root>/_incoming, the manual UI upload folder).
    Raises ValueError with a sanitized, actionable message on any
    problem, and never overwrites a landed file.
    """
    if not isinstance(source_metadata, dict):
        raise TypeError("source_metadata must be a mapping")
    try:
        source = Path(source_path)
        root = Path(landing_root)

        file_type = source_metadata.get("file_type")
        if file_type not in ACQUISITION_FILE_TYPES:
            listed = ", ".join(ACQUISITION_FILE_TYPES)
            raise ValueError(f"Acquisition currently supports only: {listed}")

        if approved_incoming_roots is None:
            approved_roots: tuple[Path, ...] = (root / INCOMING_DIR_NAME,)
        else:
            approved_roots = tuple(Path(item) for item in approved_incoming_roots)
        _ensure_within(source, approved_roots, "incoming")

        record = build_manifest_record(
            source_metadata, source, run_id=run_id, max_byte_size=max_byte_size
        )
        verify_file_signature(source, file_type)

        final_path = build_landing_path(root, source, record)
        if final_path.exists():
            if not final_path.is_file():
                raise ValueError(
                    f"{final_path}: landing target exists and is not a regular file"
                )
            existing_hash = compute_file_hash_sha256(final_path)
            if existing_hash == record["file_hash_sha256"]:
                return _land(record, final_path, landing_path_prefixes)
            raise ValueError(
                f"{final_path}: already exists with different content (sha256 "
                f"{existing_hash[:12]}...); landed raw files are immutable and are "
                "never overwritten - a corrected file lands under its own hash"
            )

        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = final_path.parent / f".{final_path.name}.tmp-{uuid.uuid4().hex}"
        try:
            shutil.copyfile(source, temp_path)
            if compute_file_hash_sha256(temp_path) != record["file_hash_sha256"]:
                raise ValueError(
                    f"{temp_path}: copied bytes do not match the source hash; "
                    "landing aborted"
                )
            if final_path.exists():
                raise ValueError(
                    f"{final_path}: appeared during landing; aborting without overwrite"
                )
            os.replace(temp_path, final_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return _land(record, final_path, landing_path_prefixes)
    except ValueError as exc:
        raise ValueError(sanitize_error_message(str(exc))) from None
