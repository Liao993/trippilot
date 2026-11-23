"""Delta persistence for source-file manifest records (F04.3).

One operational Delta table stores one row per deterministic
source_file_id, with a schema aligned to
contracts/ops/source_file_manifest.yml. Every write goes through an
idempotent MERGE keyed by source_file_id: a new record inserts, and an
existing record updates ONLY the permitted operational fields
(processing_state, landing_path, run_id, error_message). Source
identity and metadata are never overwritten in the table, and
duplicate rows are never appended.

The Spark session is injected, so the SQL contracts can be unit-tested
with stubs; no production table is required for the unit tests. The
dev-workspace runtime tests use an isolated *_test table instead of the
live manifest table.
"""

import re
from typing import Any

from src.common.source_manifest import (
    validate_source_metadata,
)
from src.common.table_setup import build_add_columns_sql

# Declared by contracts/ops/source_file_manifest.yml.
MANIFEST_TABLE = "trippilot_dev.ops.source_file_manifest"

# Contract field order: source identity, metadata, operational fields.
# error_type (F07.3-T01) is the optional classified failure reason.
MANIFEST_FIELDS: tuple[str, ...] = (
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
    "landing_path",
    "run_id",
    "processing_state",
    "error_message",
    "error_type",
)

# Delta column types per contract field (byte_size is the only integer).
MANIFEST_COLUMN_TYPES: dict[str, str] = {
    field: ("BIGINT" if field == "byte_size" else "STRING") for field in MANIFEST_FIELDS
}

# Columns that may hold NULL: the optional operational fields.
NULLABLE_FIELDS = ("landing_path", "error_message", "error_type")

# Only the operational state of the latest attempt may change after a
# row exists. Everything else is immutable in the table.
UPDATABLE_FIELDS: tuple[str, ...] = (
    "processing_state",
    "landing_path",
    "run_id",
    "error_message",
    "error_type",
)

_TABLE_NAME_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){1,2}$"
)


def _validate_table_name(table_name: str) -> str:
    """Reject anything that is not a plain catalog.schema(.table) name."""
    if not isinstance(table_name, str) or not _TABLE_NAME_PATTERN.match(table_name):
        raise ValueError(
            f"Invalid manifest table name {table_name!r}; expected a plain "
            "catalog.schema.table (or schema.table) identifier"
        )
    return table_name


def _sql_literal(value: Any) -> str:
    """Render one manifest value as a safely escaped SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        raise TypeError("Boolean values are not part of the manifest contract")
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build_create_table_sql(table_name: str) -> str:
    """Return CREATE TABLE IF NOT EXISTS SQL aligned with the contract."""
    _validate_table_name(table_name)
    columns = []
    for field in MANIFEST_FIELDS:
        sql_type = MANIFEST_COLUMN_TYPES[field]
        required = field not in NULLABLE_FIELDS
        columns.append(f"  {field} {sql_type}" + (" NOT NULL" if required else ""))
    return (
        f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        + ",\n".join(columns)
        + "\n) USING DELTA"
    )


def build_upsert_sql(table_name: str, record: dict[str, Any]) -> str:
    """Return the idempotent MERGE for one manifest record.

    ON source_file_id: WHEN MATCHED, update only the operational
    fields; WHEN NOT MATCHED, insert the full record. Duplicate rows
    cannot be appended because the merge key is the deterministic ID.
    """
    _validate_table_name(table_name)
    select_items = ", ".join(
        f"{_sql_literal(record.get(field))} AS {field}" for field in MANIFEST_FIELDS
    )
    update_items = ", ".join(
        f"target.{field} = source.{field}" for field in UPDATABLE_FIELDS
    )
    insert_columns = ", ".join(MANIFEST_FIELDS)
    insert_values = ", ".join(f"source.{field}" for field in MANIFEST_FIELDS)
    return (
        f"MERGE INTO {table_name} AS target\n"
        f"USING (SELECT {select_items}) AS source\n"
        "ON target.source_file_id = source.source_file_id\n"
        "WHEN MATCHED THEN UPDATE SET\n"
        f"  {update_items}\n"
        "WHEN NOT MATCHED THEN INSERT\n"
        f"  ({insert_columns})\n"
        f"VALUES ({insert_values})"
    )


def _row_to_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "asDict"):
        return dict(row.asDict())
    return dict(row)


class ManifestStore:
    """Thin Delta-backed adapter: create, idempotent upsert, read.

    spark is the Databricks Spark session (injected so unit tests can
    pass a stub). landing_path_prefixes is forwarded to manifest
    metadata validation; tests that land into temporary directories
    pass those roots instead of /Volumes/.
    """

    def __init__(
        self,
        table_name: str = MANIFEST_TABLE,
        spark: Any = None,
        landing_path_prefixes: tuple[str, ...] = ("/Volumes/",),
    ) -> None:
        self.table_name = _validate_table_name(table_name)
        self.spark = spark
        self.landing_path_prefixes = tuple(landing_path_prefixes)

    def _require_spark(self) -> Any:
        if self.spark is None:
            raise ValueError(
                f"{self.table_name}: a Spark session is required for manifest "
                "store operations"
            )
        return self.spark

    def ensure_table(self) -> None:
        """Create the manifest table if missing; evolve it forward.

        CREATE TABLE IF NOT EXISTS only fills gaps. An existing table
        (for example the live manifest created before F07.3) is evolved
        forward with ALTER ADD COLUMNS - here adding the error_type
        column - without touching any existing row, mirroring the
        shared operational-table evolution in src/common/table_setup.
        """
        spark = self._require_spark()
        spark.sql(build_create_table_sql(self.table_name))
        existing = [
            str(row["col_name"])
            for row in spark.sql(f"DESCRIBE {self.table_name}").collect()
        ]
        alter_sql = build_add_columns_sql(
            self.table_name, MANIFEST_COLUMN_TYPES, existing
        )
        if alter_sql is not None:
            spark.sql(alter_sql)

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Validate and merge one record; return the stored record.

        Refuses to store an invalid record. The MERGE inserts a new row
        or updates only the operational fields of the existing row.
        """
        if not isinstance(record, dict):
            raise TypeError("Manifest record must be a mapping")
        errors = validate_source_metadata(
            record, landing_path_prefixes=self.landing_path_prefixes
        )
        if errors:
            raise ValueError(
                "Refusing to store invalid manifest record:\n- " + "\n- ".join(errors)
            )
        self._require_spark().sql(build_upsert_sql(self.table_name, record))
        return record

    def read(self, source_file_id: str) -> dict[str, Any] | None:
        """Return the manifest row for one ID, or None when absent."""
        if not isinstance(source_file_id, str) or not source_file_id.strip():
            raise ValueError("source_file_id is required to read a manifest record")
        columns = ", ".join(MANIFEST_FIELDS)
        sql = (
            f"SELECT {columns} FROM {self.table_name} "
            f"WHERE source_file_id = {_sql_literal(source_file_id)}"
        )
        rows = self._require_spark().sql(sql).collect()
        if not rows:
            return None
        return _row_to_dict(rows[0])

    def read_landed(self, source_file_id: str) -> dict[str, Any]:
        """Return the landed manifest row for one ID; raise otherwise.

        Downstream Bronze processing consumes the landing_path from
        this record; it must never re-download or re-copy the file.
        """
        record = self.read(source_file_id)
        if record is None:
            raise ValueError(
                f"{source_file_id}: no manifest record found in {self.table_name}"
            )
        state = record.get("processing_state")
        if state != "landed":
            raise ValueError(
                f"{source_file_id}: manifest record state is {state!r}, not landed; "
                "only landed records can be reprocessed"
            )
        landing_path = record.get("landing_path")
        if not isinstance(landing_path, str) or not landing_path.strip():
            raise ValueError(
                f"{source_file_id}: landed manifest record has no landing_path"
            )
        return record

    def read_landed_by_identity(
        self,
        source_family: str,
        source_entity_id: str,
        source_version: str,
        file_type: str,
    ) -> dict[str, Any]:
        """Return the single landed manifest row for a source identity.

        Bronze resolves its input file by stable source identity
        (family/entity/version/type) instead of a hard-coded path. Exactly
        one landed row must exist for that identity: a missing row, or
        several hash-versioned landed rows, means the operator must
        decide which source_file_id to process - this method never
        guesses and never falls back to a root path.
        """
        for name, value in (
            ("source_family", source_family),
            ("source_entity_id", source_entity_id),
            ("source_version", source_version),
            ("file_type", file_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required to resolve a manifest record")
        identity = f"{source_family}/{source_entity_id}/{source_version} ({file_type})"
        columns = ", ".join(MANIFEST_FIELDS)
        sql = (
            f"SELECT {columns} FROM {self.table_name} "
            f"WHERE source_family = {_sql_literal(source_family)} "
            f"AND source_entity_id = {_sql_literal(source_entity_id)} "
            f"AND source_version = {_sql_literal(source_version)} "
            f"AND file_type = {_sql_literal(file_type)} "
            "AND processing_state = 'landed'"
        )
        rows = self._require_spark().sql(sql).collect()
        if not rows:
            raise ValueError(
                f"{identity}: no landed manifest record found in {self.table_name}"
            )
        if len(rows) > 1:
            ids = ", ".join(
                _row_to_dict(row).get("source_file_id", "?") for row in rows
            )
            raise ValueError(
                f"{identity}: {len(rows)} landed manifest records found "
                f"({ids}); pass an explicit source_file_id to choose one"
            )
        record = _row_to_dict(rows[0])
        landing_path = record.get("landing_path")
        if not isinstance(landing_path, str) or not landing_path.strip():
            raise ValueError(
                f"{record.get('source_file_id')}: landed manifest record has no "
                "landing_path"
            )
        return record
