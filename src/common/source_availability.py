"""Source-asset availability ledger (F07.3-T01).

The source manifest records one immutable row per ACQUIRED file: its
deterministic source_file_id and NOT NULL content fields require real
bytes, so the manifest can never represent an expected asset that the
source simply did not publish for a snapshot. This ledger records
exactly that missing piece, keeping truth about acquired bytes solely
in the manifest (no duplication):

- not_published: the source's own evidence confirms the asset was not
  published for this snapshot. Recording it REQUIRES the evidence URL
  and a note describing what was checked, and is REFUSED when a landed
  manifest record exists for the same asset identity and file type -
  bytes exist, so an absence claim would contradict the manifest.
  A download failure or timeout must never be recorded as not
  published; only confirmed evidence of absence qualifies.
- available: supersedes a prior not_published claim once bytes have
  landed. Recording it REQUIRES the landed source_file_id, which is
  verified against the manifest store and must match the identity.

One row per expected asset identity (source_family, source_entity_id,
source_version, file_type), keyed by a deterministic availability_id
computed over the identity WITHOUT any content hash, so it can never
collide with manifest record IDs. Upserts are idempotent MERGEs on
availability_id that update only the availability/evidence fields;
the identity is the key and is never rewritten.

Pure Python validation + SQL builders (ManifestStore pattern): no
Spark needed for unit tests, injected Spark for table operations.
"""

import hashlib
import re
from datetime import datetime
from typing import Any

from src.common.provenance import build_run_id
from src.common.source_manifest import (
    SECRET_PATTERNS,
    SHA256_HEX_PATTERN,
    SUPPORTED_FILE_TYPES,
    UTC_TIMESTAMP_PATTERN,
    sanitize_error_message,
)
from src.common.table_setup import build_add_columns_sql

# Declared by contracts/ops/source_file_availability.yml.
AVAILABILITY_TABLE = "trippilot_dev.ops.source_file_availability"

ALLOWED_AVAILABILITY_STATES = ("not_published", "available")

# Identity first, then the availability/evidence fields. The MERGE
# updates only the fields after availability_id; the identity is
# carried by the deterministic key and is never rewritten.
AVAILABILITY_FIELDS: tuple[str, ...] = (
    "availability_id",
    "source_family",
    "source_entity_id",
    "source_version",
    "file_type",
    "availability_state",
    "evidence_url",
    "evidence_note",
    "landed_source_file_id",
    "checked_at_utc",
    "recorded_by",
    "run_id",
)
AVAILABILITY_COLUMN_TYPES: dict[str, str] = {
    field: "STRING" for field in AVAILABILITY_FIELDS
}

# Nullable evidence fields: a not_published record has no landed ID, an
# available record carries the landed ID instead of listing evidence.
NULLABLE_FIELDS = ("evidence_url", "evidence_note", "landed_source_file_id")
REQUIRED_FIELDS = tuple(
    field for field in AVAILABILITY_FIELDS if field not in NULLABLE_FIELDS
)

IDENTITY_FIELDS = ("source_family", "source_entity_id", "source_version", "file_type")

# Fields the MERGE may update on a match. The identity is carried by
# the deterministic key and is never rewritten; only the current
# availability/evidence fields move.
UPDATABLE_FIELDS: tuple[str, ...] = (
    "availability_state",
    "evidence_url",
    "evidence_note",
    "landed_source_file_id",
    "checked_at_utc",
    "recorded_by",
    "run_id",
)

MAX_EVIDENCE_NOTE_LENGTH = 500

_TABLE_NAME_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){1,2}$"
)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _validate_table_name(table_name: str) -> str:
    if not isinstance(table_name, str) or not _TABLE_NAME_PATTERN.match(table_name):
        raise ValueError(
            f"Invalid availability table name {table_name!r}; expected a plain "
            "catalog.schema.table (or schema.table) identifier"
        )
    return table_name


def _sql_literal(value: Any) -> str:
    """Render one availability value as a safely escaped SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        raise TypeError("Boolean values are not part of the availability contract")
    return "'" + str(value).replace("'", "''") + "'"


def build_availability_id(
    source_family: str,
    source_entity_id: str,
    source_version: str,
    file_type: str,
) -> str:
    """Return the deterministic ledger ID for one expected asset identity.

    Computed over the identity WITHOUT any content hash: an expected
    asset keeps one ledger row across checks, and the ID can never
    equal a manifest source_file_id (whose canonical string includes
    the file hash).
    """
    canonical = (
        f"{source_family}|{source_entity_id}|{source_version}|{file_type}|availability"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_availability_record(record: Any) -> list[str]:
    """Return every availability-record problem; each message names the field."""
    if not isinstance(record, dict):
        return ["Availability record must be a mapping"]

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if not _is_nonempty_string(record.get(field)):
            errors.append(f"Missing required availability field: {field}")

    file_type = record.get("file_type")
    if _is_nonempty_string(file_type) and file_type not in SUPPORTED_FILE_TYPES:
        errors.append(
            f"Unsupported file type {file_type!r}; expected one of: "
            + ", ".join(SUPPORTED_FILE_TYPES)
        )

    state = record.get("availability_state")
    if _is_nonempty_string(state) and state not in ALLOWED_AVAILABILITY_STATES:
        errors.append(
            f"Invalid availability_state {state!r}; expected one of: "
            + ", ".join(ALLOWED_AVAILABILITY_STATES)
        )

    checked = record.get("checked_at_utc")
    if _is_nonempty_string(checked):
        valid = UTC_TIMESTAMP_PATTERN.match(str(checked))
        if valid:
            try:
                datetime.fromisoformat(str(checked))
            except ValueError:
                valid = None
        if not valid:
            errors.append(
                "checked_at_utc must be an ISO-8601 UTC timestamp like "
                "2026-11-23T18:00:00Z"
            )

    evidence_url = record.get("evidence_url")
    if _is_nonempty_string(evidence_url) and not str(evidence_url).startswith(
        ("https://", "http://")
    ):
        errors.append("evidence_url must start with https:// or http://")

    landed_id = record.get("landed_source_file_id")
    if _is_nonempty_string(landed_id) and not SHA256_HEX_PATTERN.match(str(landed_id)):
        errors.append(
            "landed_source_file_id must be a 64-character lowercase SHA-256 hex digest"
        )

    if state == "not_published":
        if not _is_nonempty_string(evidence_url):
            errors.append(
                "evidence_url is required when availability_state is not_published"
            )
        if not _is_nonempty_string(record.get("evidence_note")):
            errors.append(
                "evidence_note is required when availability_state is not_published"
            )
        if _is_nonempty_string(landed_id):
            errors.append(
                "landed_source_file_id is not allowed when availability_state is "
                "not_published; an unacquired asset has no landed record"
            )

    if state == "available" and not _is_nonempty_string(landed_id):
        errors.append(
            "landed_source_file_id is required when availability_state is available"
        )

    note = record.get("evidence_note")
    if _is_nonempty_string(note) and any(
        pattern.search(str(note)) for pattern in SECRET_PATTERNS
    ):
        errors.append(
            "evidence_note appears to contain a credential; sanitize it first"
        )

    if all(_is_nonempty_string(record.get(field)) for field in IDENTITY_FIELDS):
        expected_id = build_availability_id(
            str(record["source_family"]),
            str(record["source_entity_id"]),
            str(record["source_version"]),
            str(record["file_type"]),
        )
        if (
            _is_nonempty_string(record.get("availability_id"))
            and record.get("availability_id") != expected_id
        ):
            errors.append(
                "availability_id must equal the deterministic ID built from the "
                "asset identity"
            )

    return errors


def _build_base_record(
    source_identity: dict[str, Any],
    availability_state: str,
    checked_at_utc: str,
    recorded_by: str,
    run_id: str | None,
) -> dict[str, Any]:
    if not isinstance(source_identity, dict):
        raise TypeError("source_identity must be a mapping")
    record: dict[str, Any] = {
        "source_family": source_identity.get("source_family"),
        "source_entity_id": source_identity.get("source_entity_id"),
        "source_version": source_identity.get("source_version"),
        "file_type": source_identity.get("file_type"),
        "availability_state": availability_state,
        "checked_at_utc": checked_at_utc,
        "recorded_by": recorded_by,
        "run_id": run_id if _is_nonempty_string(run_id) else build_run_id(),
    }
    if all(_is_nonempty_string(record.get(field)) for field in IDENTITY_FIELDS):
        record["availability_id"] = build_availability_id(
            str(record["source_family"]),
            str(record["source_entity_id"]),
            str(record["source_version"]),
            str(record["file_type"]),
        )
    else:
        record["availability_id"] = None
    return record


def _refuse_when_landed_manifest_exists(
    record: dict[str, Any], manifest_store: Any
) -> None:
    if manifest_store is None:
        return
    try:
        landed = manifest_store.read_landed_by_identity(
            record["source_family"],
            record["source_entity_id"],
            record["source_version"],
            record["file_type"],
        )
    except ValueError:
        # No landed record (or ambiguous hash versions): the absence
        # claim is not contradicted by acquired bytes.
        return
    raise ValueError(
        "Refusing to record not_published for "
        f"{record['source_family']}/{record['source_entity_id']}/"
        f"{record['source_version']}/{record['file_type']}: a landed "
        f"manifest record exists (source_file_id "
        f"{landed.get('source_file_id')}). Acquired bytes contradict an "
        "absence claim; investigate the source listing instead."
    )


def _verify_landed_identity(record: dict[str, Any], manifest_store: Any) -> None:
    if manifest_store is None:
        return
    landed = manifest_store.read(record["landed_source_file_id"])
    if landed is None:
        raise ValueError(
            f"No manifest record found for landed_source_file_id "
            f"{record['landed_source_file_id']}; only a landed record can mark an "
            "asset available"
        )
    if landed.get("processing_state") != "landed":
        raise ValueError(
            f"Manifest record {record['landed_source_file_id']} is "
            f"{landed.get('processing_state')!r}, not landed; only a landed record "
            "can mark an asset available"
        )
    mismatches = [
        field for field in IDENTITY_FIELDS if landed.get(field) != record.get(field)
    ]
    if mismatches:
        raise ValueError(
            "landed_source_file_id identity does not match the expected asset "
            "("
            + ", ".join(f"{field}: {record.get(field)!r}" for field in mismatches)
            + ")"
        )


def build_not_published_record(
    source_identity: dict[str, Any],
    evidence_url: str,
    evidence_note: str,
    checked_at_utc: str,
    recorded_by: str,
    manifest_store: Any = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return a validated not_published record for one expected asset.

    source_identity carries source_family, source_entity_id,
    source_version and file_type. evidence_url and evidence_note
    describe the source's own confirmation that the asset was not
    published for this snapshot; a download failure or timeout must
    never be recorded here.

    When manifest_store is provided (recommended: the ManifestStore or
    any adapter with read_landed_by_identity), the claim is REFUSED if
    a landed manifest record exists for the same identity and file
    type - bytes exist, so not_published would contradict the manifest.

    Raises ValueError (sanitized) listing every problem.
    """
    record = _build_base_record(
        source_identity, "not_published", checked_at_utc, recorded_by, run_id
    )
    record["evidence_url"] = str(evidence_url)
    record["evidence_note"] = sanitize_error_message(str(evidence_note))[
        :MAX_EVIDENCE_NOTE_LENGTH
    ]
    record["landed_source_file_id"] = None
    _refuse_when_landed_manifest_exists(record, manifest_store)
    errors = validate_availability_record(record)
    if errors:
        raise ValueError(
            "Invalid source availability record:\n- " + "\n- ".join(errors)
        )
    return record


def build_available_record(
    source_identity: dict[str, Any],
    landed_source_file_id: str,
    checked_at_utc: str,
    recorded_by: str,
    manifest_store: Any = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Return a validated available record superseding a prior absence claim.

    landed_source_file_id must reference a LANDED manifest record whose
    identity matches source_identity; when manifest_store is provided
    (recommended: the ManifestStore or any adapter with read), the
    record is read and cross-checked, so a stale or mistyped ID can
    never mark an asset available.

    Raises ValueError (sanitized) listing every problem.
    """
    record = _build_base_record(
        source_identity, "available", checked_at_utc, recorded_by, run_id
    )
    record["evidence_url"] = None
    record["evidence_note"] = None
    record["landed_source_file_id"] = str(landed_source_file_id)
    _verify_landed_identity(record, manifest_store)
    errors = validate_availability_record(record)
    if errors:
        raise ValueError(
            "Invalid source availability record:\n- " + "\n- ".join(errors)
        )
    return record


def build_create_table_sql(table_name: str) -> str:
    """Return CREATE TABLE IF NOT EXISTS SQL for the ledger shape."""
    _validate_table_name(table_name)
    columns = ",\n".join(
        f"  {field} {AVAILABILITY_COLUMN_TYPES[field]}"
        + ("" if field in NULLABLE_FIELDS else " NOT NULL")
        for field in AVAILABILITY_FIELDS
    )
    return f"CREATE TABLE IF NOT EXISTS {table_name} (\n{columns}\n) USING DELTA"


def build_upsert_sql(table_name: str, record: dict[str, Any]) -> str:
    """Return the idempotent MERGE for one availability record.

    ON availability_id: WHEN MATCHED, update only the
    availability/evidence fields (the identity is the key and is never
    rewritten); WHEN NOT MATCHED, insert the full record. Duplicate rows
    cannot be appended because the merge key is the deterministic ID.
    """
    _validate_table_name(table_name)
    select_items = ", ".join(
        f"{_sql_literal(record.get(field))} AS {field}" for field in AVAILABILITY_FIELDS
    )
    update_items = ", ".join(
        f"target.{field} = source.{field}" for field in UPDATABLE_FIELDS
    )
    insert_columns = ", ".join(AVAILABILITY_FIELDS)
    insert_values = ", ".join(f"source.{field}" for field in AVAILABILITY_FIELDS)
    return (
        f"MERGE INTO {table_name} AS target\n"
        f"USING (SELECT {select_items}) AS source\n"
        "ON target.availability_id = source.availability_id\n"
        "WHEN MATCHED THEN UPDATE SET\n"
        f"  {update_items}\n"
        "WHEN NOT MATCHED THEN INSERT\n"
        f"  ({insert_columns})\n"
        f"VALUES ({insert_values})"
    )


class AvailabilityStore:
    """Thin Delta-backed adapter: create/evolve, idempotent upsert, read.

    spark is the Databricks Spark session (injected so unit tests can
    pass a stub). The ledger holds one row per expected asset; a
    supersession (not_published later becoming available) updates the
    same row's availability/evidence fields through the MERGE.
    """

    def __init__(
        self,
        table_name: str = AVAILABILITY_TABLE,
        spark: Any = None,
    ) -> None:
        self.table_name = _validate_table_name(table_name)
        self.spark = spark

    def _require_spark(self) -> Any:
        if self.spark is None:
            raise ValueError(
                f"{self.table_name}: a Spark session is required for availability "
                "store operations"
            )
        return self.spark

    def ensure_table(self) -> None:
        """Create the ledger table if missing; evolve it forward.

        CREATE TABLE IF NOT EXISTS only fills gaps; an existing table
        is evolved forward with ALTER ADD COLUMNS without touching any
        existing row (the shared table_setup evolution pattern).
        """
        spark = self._require_spark()
        spark.sql(build_create_table_sql(self.table_name))
        existing = [
            str(row["col_name"])
            for row in spark.sql(f"DESCRIBE {self.table_name}").collect()
        ]
        alter_sql = build_add_columns_sql(
            self.table_name, AVAILABILITY_COLUMN_TYPES, existing
        )
        if alter_sql is not None:
            spark.sql(alter_sql)

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Validate and merge one record; return the stored record.

        Refuses to store an invalid record. The MERGE inserts a new
        row or updates only the availability/evidence fields of the
        existing row for the same expected asset.
        """
        if not isinstance(record, dict):
            raise TypeError("Availability record must be a mapping")
        errors = validate_availability_record(record)
        if errors:
            raise ValueError(
                "Refusing to store invalid availability record:\n- "
                + "\n- ".join(errors)
            )
        self._require_spark().sql(build_upsert_sql(self.table_name, record))
        return record

    def read(self, availability_id: str) -> dict[str, Any] | None:
        """Return the ledger row for one ID, or None when absent."""
        if not isinstance(availability_id, str) or not availability_id.strip():
            raise ValueError(
                "availability_id is required to read an availability record"
            )
        columns = ", ".join(AVAILABILITY_FIELDS)
        sql = (
            f"SELECT {columns} FROM {self.table_name} "
            f"WHERE availability_id = {_sql_literal(availability_id)}"
        )
        rows = self._require_spark().sql(sql).collect()
        if not rows:
            return None
        row = rows[0]
        if hasattr(row, "asDict"):
            return dict(row.asDict())
        return dict(row)

    def read_by_identity(
        self,
        source_family: str,
        source_entity_id: str,
        source_version: str,
        file_type: str,
    ) -> dict[str, Any] | None:
        """Return the ledger row for an expected asset identity, or None."""
        return self.read(
            build_availability_id(
                source_family, source_entity_id, source_version, file_type
            )
        )
