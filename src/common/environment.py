"""
Resolve the pipeline run mode and every table name the pipeline may touch.

The run mode is the single source of truth for environment isolation:

- ``test`` (the default) maps every logical table to an isolated ``_test``
  Delta table. Code running in test mode cannot write the development
  tables, because the development names are never returned.
- ``live`` resolves the normal development tables.

The notebook dropdown is only a convenience. This module, not the widget,
enforces isolation: all target and audit table names must flow through
``resolve_table`` / ``resolve_tables``.
"""

from typing import Any

from src.common.run_controls import should_load

VALID_RUN_MODES = ("test", "live")

# Canonical development table names (run mode "live").
LIVE_TABLES = {
    "bronze": "trippilot_dev.bronze.airbnb_listings_bronze",
    "bronze_control": "trippilot_dev.bronze.airbnb_ingestion_control",
    "silver": "trippilot_dev.silver.airbnb_listings_silver",
    "silver_rejected": "trippilot_dev.silver.airbnb_listings_rejected",
    "quality_results": "trippilot_dev.ops.quality_results",
    "exclusion": "trippilot_dev.ops.exclusion",
}


def validate_run_mode(run_mode: str) -> str:
    """
    Return the normalized run mode.

    Args:
        run_mode: Widget value, such as "test" or "live".

    Returns:
        "test" or "live".

    Raises:
        ValueError: When the value is not a known run mode.
    """
    normalized = str(run_mode).strip().lower()

    if normalized not in VALID_RUN_MODES:
        raise ValueError(
            f"Unknown run mode: {run_mode!r}. Expected one of {VALID_RUN_MODES}."
        )

    return normalized


def resolve_table(logical_name: str, run_mode: str) -> str:
    """
    Resolve one logical table name to a fully qualified table name.

    Args:
        logical_name: Key in LIVE_TABLES, such as "bronze" or "silver".
        run_mode: "test" or "live".

    Returns:
        The isolated ``_test`` table in test mode, the development table
        in live mode.
    """
    mode = validate_run_mode(run_mode)

    if logical_name not in LIVE_TABLES:
        raise ValueError(
            f"Unknown table name: {logical_name!r}. "
            f"Expected one of {sorted(LIVE_TABLES)}."
        )

    live_name = LIVE_TABLES[logical_name]

    if mode == "test":
        catalog, schema, table = live_name.split(".")
        return f"{catalog}.{schema}.{table}_test"

    return live_name


def resolve_tables(run_mode: str) -> dict[str, str]:
    """
    Resolve every pipeline table for the validated run mode.

    Returns:
        A mapping of logical name to fully qualified table name.
    """
    mode = validate_run_mode(run_mode)

    return {name: resolve_table(name, mode) for name in LIVE_TABLES}


def validate_force_reload(force_reload: Any) -> bool:
    """
    Coerce the force-reload setting to a boolean.

    Accepts booleans and the widget strings "true" / "false".

    Raises:
        ValueError: When the value is not a recognized setting.
    """
    if isinstance(force_reload, bool):
        return force_reload

    normalized = str(force_reload).strip().lower()

    if normalized == "true":
        return True
    if normalized == "false":
        return False

    raise ValueError(
        f"Unknown force-reload value: {force_reload!r}. Expected 'true' or 'false'."
    )


def decide_should_run(
    force_reload: Any,
    existing_controls: list[dict[str, Any]],
    city: str,
    snapshot_date: str,
) -> bool:
    """
    Combine the force-reload setting with the normal rerun rule.

    Rules:
    - Always run when force reload is enabled.
    - Otherwise defer to should_load: run when there is no successful
      load for this city/snapshot, skip when one exists.

    Args:
        force_reload: Force-reload setting (bool or "true"/"false").
        existing_controls: Existing control records from the control table.
        city: City being ingested, such as "toronto".
        snapshot_date: Source snapshot date, such as "2026-09-16".

    Returns:
        True when ingestion should run, False when it should skip.
    """
    if validate_force_reload(force_reload):
        return True

    return should_load(
        existing_controls=existing_controls,
        city=city,
        snapshot_date=snapshot_date,
    )
