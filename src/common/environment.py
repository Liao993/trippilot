"""
Resolve the pipeline run mode and every table name the pipeline may touch.

The run mode is the single source of truth for environment isolation
(F07.4: physical catalog separation):

- ``test`` (the default) maps every logical table into the dedicated
  ``trippilot_test`` catalog. Code running in test mode cannot write
  the development tables, because ``trippilot_dev`` names are never
  returned in test mode.
- ``live`` resolves the development tables in ``trippilot_dev``.

Both catalogs use the same schema and table names, so shapes stay
aligned while data and write destinations stay isolated. Every
resolved mapping is guarded by ``validate_destinations``: a test-mode
run can never receive a ``trippilot_dev`` destination and vice versa.

The notebook dropdown is only a convenience. This module, not the
widget, enforces isolation: all target and audit table names must flow
through ``resolve_table`` / ``resolve_tables``.
"""

from collections.abc import Mapping
from typing import Any

from src.common.run_controls import should_load

VALID_RUN_MODES = ("test", "live")

# F07.4: physical catalog separation. Test execution writes only the
# dedicated test catalog; development/canonical execution writes only
# the development catalog.
DEV_CATALOG = "trippilot_dev"
TEST_CATALOG = "trippilot_test"

# Canonical development table names (run mode "live"). Test mode maps
# every entry into the TEST_CATALOG with the same schema/table names.
LIVE_TABLES = {
    "bronze": "trippilot_dev.bronze.airbnb_listings_bronze",
    "quality_results": "trippilot_dev.ops.quality_results",
    # The former "exclusion" key was removed in the pre-F07 cleanup: it
    # pointed at a placeholder table (ops.exclusion) that was never
    # created. A feature that needs it should create the table
    # populated and re-add the key here.
    "source_manifest": "trippilot_dev.ops.source_file_manifest",
    # F07.3: evidence-backed availability ledger for expected assets
    # that the source did not publish (never a duplicate of the
    # manifest, which only records acquired files).
    "source_availability": "trippilot_dev.ops.source_file_availability",
    # F07.4: ONE shared ingestion manifest per environment. Every
    # dataset records its run outcomes here (one row per source file
    # per ingestion run); the per-dataset control tables were retired
    # after their history was migrated.
    "ingestion_manifest": "trippilot_dev.ops.ingestion_manifest",
    # F06.2: separate Bronze data products for the calendar and review
    # datasets - never conflated with the listings table.
    "calendar_bronze": "trippilot_dev.bronze.airbnb_calendar_bronze",
    "reviews_bronze": "trippilot_dev.bronze.airbnb_reviews_bronze",
    # F07.2: four more separate Bronze data products - the summary
    # listings/reviews files and the neighbourhood CSV/GeoJSON assets
    # are never conflated with the detailed facts tables above.
    "listings_summary_bronze": "trippilot_dev.bronze.airbnb_listings_summary_bronze",
    "reviews_summary_bronze": "trippilot_dev.bronze.airbnb_reviews_summary_bronze",
    "neighbourhoods_bronze": "trippilot_dev.bronze.airbnb_neighbourhoods_bronze",
    "neighbourhood_geometry_bronze": (
        "trippilot_dev.bronze.airbnb_neighbourhood_geometry_bronze"
    ),
}


def catalog_for(run_mode: str) -> str:
    """Return the physical catalog that belongs to the run mode (F07.4)."""
    mode = validate_run_mode(run_mode)
    return TEST_CATALOG if mode == "test" else DEV_CATALOG


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
        logical_name: Key in LIVE_TABLES, such as "bronze" or "quality_results".
        run_mode: "test" or "live".

    Returns:
        The table in the dedicated ``trippilot_test`` catalog in test
        mode, the development table in ``trippilot_dev`` in live mode.
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
        return f"{TEST_CATALOG}.{schema}.{table}"

    return live_name


def resolve_tables(run_mode: str) -> dict[str, str]:
    """
    Resolve every pipeline table for the validated run mode.

    Returns:
        A mapping of logical name to fully qualified table name, guarded
        by ``validate_destinations`` for the run mode.
    """
    mode = validate_run_mode(run_mode)

    resolved = {name: resolve_table(name, mode) for name in LIVE_TABLES}
    return validate_destinations(mode, resolved)


def validate_destination(table_name: str, run_mode: str) -> str:
    """
    Guard one resolved destination against the wrong catalog (F07.4).

    Every table a run may write must live in the catalog that belongs
    to the validated run mode: a test-mode run can never receive a
    ``trippilot_dev`` destination, and a live/dev run can never receive
    a ``trippilot_test`` one. Call this before any write to a table
    name that did not come straight from ``resolve_table``.

    Raises:
        ValueError: When the destination is not inside the mode's
        catalog (or points at the other catalog).
    """
    mode = validate_run_mode(run_mode)
    expected_catalog = catalog_for(mode)
    forbidden_catalog = DEV_CATALOG if mode == "test" else TEST_CATALOG

    if not isinstance(table_name, str) or not table_name.startswith(
        f"{expected_catalog}."
    ):
        raise ValueError(
            f"Destination {table_name!r} is outside the {mode!r} catalog "
            f"{expected_catalog!r}; refusing to touch it. Resolve the table "
            "through src.common.environment for the selected run mode."
        )
    if table_name.startswith(f"{forbidden_catalog}."):
        raise ValueError(
            f"Destination {table_name!r} belongs to the {forbidden_catalog!r} "
            f"catalog but the run mode is {mode!r}; refusing a cross-environment "
            "write."
        )
    return table_name


def validate_destinations(run_mode: str, tables: Mapping[str, str]) -> dict[str, str]:
    """
    Validate every resolved destination against the run mode.

    Args:
        run_mode: "test" or "live".
        tables: Mapping of logical name to fully qualified table name,
        such as the result of ``resolve_tables``.

    Returns:
        The same mapping as a plain dict, once every destination has
        been validated for the run mode.

    Raises:
        ValueError: Naming the first offending table.
    """
    mode = validate_run_mode(run_mode)
    for key, table_name in tables.items():
        try:
            validate_destination(table_name, mode)
        except ValueError as error:
            raise ValueError(f"{key}: {error}") from error
    return dict(tables)


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
