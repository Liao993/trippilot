"""
Helpers that make ingestion safe to rerun.

The control record is a plain dictionary so the pipeline stays simple.
Each record describes one attempted load for one city and snapshot date.
"""

from typing import Any


def should_load(
    existing_controls: list[dict[str, Any]],
    city: str,
    snapshot_date: str,
) -> bool:
    """
    Decide whether a city/snapshot should be loaded.

    Rules:
    - Load if there is no existing control record.
    - Load if the previous attempt failed.
    - Skip if this exact city/snapshot already loaded successfully.

    Args:
        existing_controls: Existing control records from the control table.
        city: City being ingested, such as "toronto".
        snapshot_date: Source snapshot date, such as "2026-09-16".

    Returns:
        True if the pipeline should load the data; False if it should skip.
    """
    for control in existing_controls:
        is_same_city = control.get("city") == city
        is_same_snapshot = control.get("snapshot_date") == snapshot_date
        is_successful = control.get("status") == "success"

        # A successful load for the same city and snapshot means
        # rerunning it now would create duplicate Bronze data.
        if is_same_city and is_same_snapshot and is_successful:
            return False

    # No matching successful load was found, so it is safe to load.
    return True


def build_control_record(
    city: str,
    snapshot_date: str,
    run_id: str,
    status: str,
    row_count: int = 0,
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    Build one ingestion-control record.

    This record is written to the control table before and after ingestion.
    It gives the pipeline an audit trail: what ran, when, and whether it worked.
    """
    return {
        "city": city,
        "snapshot_date": snapshot_date,
        "run_id": run_id,
        "status": status,
        "row_count": row_count,
        "error_message": error_message,
    }