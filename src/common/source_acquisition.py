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
    build_source_file_id,
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


def verify_landed_record(record: dict[str, Any]) -> dict[str, Any]:
    """Verify the immutable landed object matches the manifest record.

    Checks that the landing path exists, is a regular file, its
    SHA-256 equals the stored file_hash_sha256 and its byte size
    equals the stored byte_size. Returns the record unchanged; raises
    a sanitized ValueError when the landed object is missing or does
    not match. A mismatch is an integrity incident, not something to
    re-land: landed raw files are immutable.
    """
    try:
        landing_path = record.get("landing_path")
        if not isinstance(landing_path, str) or not landing_path.strip():
            raise ValueError("landed manifest record has no landing_path")
        path = Path(landing_path)
        if not path.exists():
            raise ValueError(
                f"{path}: landed file not found "
                f"(source_file_id {record.get('source_file_id')})"
            )
        if not path.is_file():
            raise ValueError(f"{path}: landed object is not a regular file")
        actual_hash = compute_file_hash_sha256(path)
        expected_hash = str(record.get("file_hash_sha256"))
        if actual_hash != expected_hash:
            raise ValueError(
                f"{path}: landed file hash {actual_hash[:12]}... does not match "
                f"the manifest hash {expected_hash[:12]}...; landed raw files are "
                "immutable - investigate instead of re-landing"
            )
        actual_size = path.stat().st_size
        expected_size = record.get("byte_size")
        if actual_size != expected_size:
            raise ValueError(
                f"{path}: landed file size {actual_size} does not match the "
                f"manifest byte_size {expected_size}"
            )
        return record
    except ValueError as exc:
        raise ValueError(sanitize_error_message(str(exc))) from None


def verify_existing_source_file(
    source_file_id: str,
    manifest_store: Any,
) -> dict[str, Any]:
    """Verify the landed object for a stored manifest ID (no incoming file).

    Reads the landed manifest record from the store and hash-verifies
    the immutable landed object. Raises a clear ValueError when the ID
    is unknown, the record is not landed, or the object no longer
    matches. Never touches the incoming staging area.
    """
    return verify_landed_record(manifest_store.read_landed(source_file_id))


def reprocess_source_file(
    source_identity: dict[str, Any],
    manifest_store: Any,
) -> dict[str, Any]:
    """Resolve the landed path for a source identity without re-acquiring.

    source_identity is a mapping with source_family, source_entity_id,
    source_version, file_type and file_hash_sha256. The deterministic
    source_file_id is recomputed, the landed manifest record is read
    from the store, and the immutable landed object is hash-verified.
    This never reads the incoming file and never copies or downloads
    anything: use the returned landing_path for downstream processing.
    """
    if not isinstance(source_identity, dict):
        raise TypeError("source_identity must be a mapping")
    try:
        required = (
            "source_family",
            "source_entity_id",
            "source_version",
            "file_type",
            "file_hash_sha256",
        )
        missing = [
            field
            for field in required
            if not isinstance(source_identity.get(field), str)
            or not source_identity[field].strip()
        ]
        if missing:
            raise ValueError(
                "source_identity requires non-empty: " + ", ".join(missing)
            )
        source_file_id = build_source_file_id(
            source_identity["source_family"],
            source_identity["source_entity_id"],
            source_identity["source_version"],
            source_identity["file_type"],
            source_identity["file_hash_sha256"],
        )
        return verify_existing_source_file(source_file_id, manifest_store)
    except ValueError as exc:
        raise ValueError(sanitize_error_message(str(exc))) from None


def acquire_source_file(
    source_metadata: dict[str, Any],
    source_path: str | Path,
    landing_root: str | Path,
    approved_incoming_roots: Sequence[str | Path] | None = None,
    max_byte_size: int = DEFAULT_MAX_BYTE_SIZE,
    run_id: str | None = None,
    landing_path_prefixes: Sequence[str] = ("/Volumes/",),
    manifest_store: Any = None,
) -> dict[str, Any]:
    """Validate a staged source file and land it immutably; return the record.

    The source file must live under an approved incoming location (by
    default <landing_root>/_incoming, the manual UI upload folder).
    Raises ValueError with a sanitized, actionable message on any
    problem, and never overwrites a landed file.

    When manifest_store is provided (a ManifestStore or any adapter
    with read/upsert), acquisition also becomes manifest-driven:
    - The attempt is visible in the manifest table from the registered
      state onwards, and a failure stores a failed record carrying the
      sanitized reason (registered -> failed).
    - An idempotent retry of bytes that are already landed resolves to
      the EXISTING landed record after hash-verifying the landed
      object, without copying again.
    - A controlled retry of a failed record re-runs the full
      validation and landing; only then do the operational fields move
      to the new attempt's run_id and state. Failed runs are never
      silently converted to successful ones.

    Failures before the file facts are known (missing, empty or
    oversized incoming files) cannot produce a manifest row because
    the deterministic ID requires the content hash; they surface
    directly to the operator. This module never parses source data:
    Bronze ingestion stays a separate concern.
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

        if manifest_store is not None:
            existing = manifest_store.read(record["source_file_id"])
            if existing is not None and existing.get("processing_state") == "landed":
                return verify_landed_record(existing)
            manifest_store.upsert(record)

        try:
            verify_file_signature(source, file_type)
            final_path = build_landing_path(root, source, record)
            if final_path.exists():
                if not final_path.is_file():
                    raise ValueError(
                        f"{final_path}: landing target exists and is not a regular file"
                    )
                existing_hash = compute_file_hash_sha256(final_path)
                if existing_hash == record["file_hash_sha256"]:
                    landed = _land(record, final_path, landing_path_prefixes)
                    if manifest_store is not None:
                        manifest_store.upsert(landed)
                    return landed
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
            landed = _land(record, final_path, landing_path_prefixes)
            if manifest_store is not None:
                manifest_store.upsert(landed)
            return landed
        except (ValueError, OSError) as exc:
            # Record the visible failure (registered -> failed) with the
            # sanitized reason, then re-raise: the attempt stays
            # auditable and a controlled retry can re-run it.
            if manifest_store is not None:
                manifest_store.upsert(
                    apply_state_transition(record, "failed", error_message=str(exc))
                )
            raise
    except ValueError as exc:
        raise ValueError(sanitize_error_message(str(exc))) from None
