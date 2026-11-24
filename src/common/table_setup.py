"""Canonical shapes and idempotent setup for operational tables.

The unified ingestion manifest and quality-result tables are defined
here in one place, with idempotent create/repair helpers, so
notebooks/ops/setup_control_tables.py can initialize either run mode
through the shared environment resolver. (F07.4: the seven per-dataset
ingestion-control tables were consolidated into ONE shared
ops.ingestion_manifest per environment after their history was
migrated.)

The helpers mirror the ManifestStore pattern: pure SQL builders covered
exactly by unit tests, plus a thin Spark-injected apply step. Existing
data is never touched - CREATE TABLE IF NOT EXISTS only fills gaps, and
ALTER ADD COLUMNS only evolves legacy shapes forward.
"""

import re
from collections.abc import Iterable, Mapping
from typing import Any

_SAFE_TABLE_NAME = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+){2}$")
_SAFE_COLUMN_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\(\d+\))?$")

# F07.4: ONE shared ingestion manifest per environment (ops.ingestion_manifest
# in each catalog). Extends the retired F06.3 per-dataset control shape
# (city, snapshot_date, run_id, status, row_count, started/completed,
# error_message, source_file_id, prior_source_file_id, dataset) with
# reconciliation counts and target_table; the legacy row_count maps to
# loaded_row_count when history is migrated. Column order defines the
# positional INSERT in src/common/ingestion_manifest.py.
INGESTION_MANIFEST_COLUMNS: dict[str, str] = {
    "city": "STRING",
    "snapshot_date": "STRING",
    "run_id": "STRING",
    "dataset": "STRING",
    "source_file_id": "STRING",
    "prior_source_file_id": "STRING",
    "status": "STRING",
    "source_row_count": "BIGINT",
    "loaded_row_count": "BIGINT",
    "rejected_row_count": "BIGINT",
    "started_at_utc": "STRING",
    "completed_at_utc": "STRING",
    "target_table": "STRING",
    "error_message": "STRING",
}

QUALITY_RESULTS_COLUMNS: dict[str, str] = {
    "run_id": "STRING",
    "source": "STRING",
    "city": "STRING",
    "snapshot_date": "STRING",
    "layer": "STRING",
    "check_name": "STRING",
    "passed": "BOOLEAN",
    "observed_count": "BIGINT",
    "checked_at_utc": "TIMESTAMP",
}

# Logical environment-resolver keys this module knows how to set up.
# Data tables (bronze, silver, ...) are intentionally absent: they are
# created by their ingestion flows, not by operational setup.
OPERATIONAL_TABLE_SHAPES: Mapping[str, Mapping[str, str]] = {
    # F07.4: the ONE shared ingestion manifest replaced the seven
    # per-dataset control tables (their history was migrated first).
    "ingestion_manifest": INGESTION_MANIFEST_COLUMNS,
    "quality_results": QUALITY_RESULTS_COLUMNS,
}


def _validate_table_name(table_name: str) -> str:
    if not isinstance(table_name, str) or not _SAFE_TABLE_NAME.fullmatch(table_name):
        raise ValueError(f"Expected a safe catalog.schema.table name: {table_name!r}")
    return table_name


def _validate_columns(columns: Mapping[str, str]) -> None:
    for name, data_type in columns.items():
        if not _SAFE_COLUMN_NAME.fullmatch(name):
            raise ValueError(f"Unsafe column name: {name!r}")
        if not _SAFE_TYPE.fullmatch(str(data_type)):
            raise ValueError(f"Unsafe data type for {name!r}: {data_type!r}")


def build_create_table_sql(table_name: str, columns: Mapping[str, str]) -> str:
    """Return CREATE TABLE IF NOT EXISTS ... USING DELTA for the shape."""
    _validate_table_name(table_name)
    _validate_columns(columns)
    definitions = ",\n  ".join(f"{name} {dtype}" for name, dtype in columns.items())
    return f"CREATE TABLE IF NOT EXISTS {table_name} (\n  {definitions}\n) USING DELTA"


def missing_columns(existing: Iterable[str], columns: Mapping[str, str]) -> list[str]:
    """Return the expected columns absent from an existing table.

    Extra DESCRIBE rows (clustering information markers) are ignored
    automatically: only expected column names are checked.
    """
    present = {str(name) for name in existing}
    return [name for name in columns if name not in present]


def build_add_columns_sql(
    table_name: str,
    columns: Mapping[str, str],
    existing: Iterable[str],
) -> str | None:
    """Return ALTER ADD COLUMNS for the missing columns, or None."""
    missing = missing_columns(existing, columns)
    if not missing:
        return None
    _validate_table_name(table_name)
    definitions = ", ".join(f"{name} {columns[name]}" for name in missing)
    return f"ALTER TABLE {table_name} ADD COLUMNS ({definitions})"


def ensure_operational_table(
    spark: Any, table_name: str, columns: Mapping[str, str]
) -> str:
    """Make one table exist with the full shape; idempotent.

    Creates the table when missing (CREATE IF NOT EXISTS is a no-op for
    an existing table) and evolves a legacy shape forward with ALTER ADD
    COLUMNS, preserving all existing history.

    Returns:
        "ok" when the table already had the full shape, "evolved" when
        legacy columns had to be added.
    """
    _validate_table_name(table_name)
    _validate_columns(columns)
    spark.sql(build_create_table_sql(table_name, columns))
    existing_rows = spark.sql(f"DESCRIBE {table_name}").collect()
    existing = [row["col_name"] for row in existing_rows]
    alter_sql = build_add_columns_sql(table_name, columns, existing)
    if alter_sql is not None:
        spark.sql(alter_sql)
        return "evolved"
    return "ok"


def ensure_operational_tables(spark: Any, tables: Mapping[str, str]) -> dict[str, str]:
    """Ensure every operational table present in a resolved table mapping.

    ``tables`` is a resolved run-mode mapping (for example
    ``resolve_tables(mode)``); non-operational keys (bronze, silver,
    source_manifest, ...) are ignored.

    Returns:
        A mapping of logical key to the action taken per table.
    """
    actions: dict[str, str] = {}
    for key, shape in OPERATIONAL_TABLE_SHAPES.items():
        if key in tables:
            actions[key] = ensure_operational_table(spark, tables[key], shape)
    return actions


def ensure_schemas(spark: Any, table_names: Iterable[str]) -> list[str]:
    """CREATE SCHEMA IF NOT EXISTS for every unique catalog.schema.

    Returns:
        The catalog.schema names in first-seen order.
    """
    seen: set[str] = set()
    created: list[str] = []
    for name in table_names:
        _validate_table_name(name)
        catalog_schema = ".".join(name.split(".")[:2])
        if catalog_schema not in seen:
            seen.add(catalog_schema)
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_schema}")
            created.append(catalog_schema)
    return created


def ensure_reserved_schemas(spark: Any, schemas: Iterable[str]) -> list[str]:
    """CREATE SCHEMA IF NOT EXISTS for stage schemas with no tables yet.

    Reserved schemas keep a future stage's documented home available -
    e.g. the empty silver schema awaiting the F08 rebuild - without
    any resolver keys or tables existing for that stage.
    """
    ensured: list[str] = []
    for schema in schemas:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        ensured.append(schema)
    return ensured


_SAFE_CATALOG_NAME = re.compile(r"^[a-z0-9_]+$")


def ensure_catalog(spark: Any, catalog: str) -> str:
    """CREATE CATALOG IF NOT EXISTS for one catalog; idempotent.

    F07.4 physical isolation: the dedicated test catalog (and the
    development catalog, when it does not exist yet) are created here
    so schema/table setup can proceed. Returns the catalog name.

    Raises:
        ValueError: When the name is not a plain lowercase identifier.
    """
    if not isinstance(catalog, str) or not _SAFE_CATALOG_NAME.fullmatch(catalog):
        raise ValueError(
            f"Invalid catalog name {catalog!r}; expected a plain lowercase identifier"
        )
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    return catalog
