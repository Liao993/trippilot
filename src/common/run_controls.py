"""
Helpers that make ingestion safe to rerun.

The control record is a plain dictionary so the pipeline stays simple.
Each record describes one attempted load for one city and snapshot date.

Since F05.3 the decision is identity-aware: it distinguishes an exact
same-file retry (safe skip) from a corrected source file (blocked
until an explicit reprocess authorization) and records failures
against the run's control row.
"""

import re
from datetime import UTC, datetime
from typing import Any

_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8,64}$")
_MAX_ERROR_MESSAGE = 500


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


def decide_ingestion_action(
    existing_controls: list[dict[str, Any]],
    city: str,
    snapshot_date: str,
    source_file_id: str,
    force_reload: bool = False,
) -> str:
    """Decide the ingestion action for one source-file identity (F05.3).

    Rules, aligned with the replace_city_snapshot Bronze contract:
    - No successful load for this city/snapshot -> "load": a first load
      or a NEW quarterly snapshot, which lands as a separate slice while
      previous snapshots remain untouched.
    - The successful load used the SAME source_file_id -> exact retry of
      the same bytes: "skip" (a no-op that cannot duplicate rows) unless
      force_reload authorizes an exact rerun.
    - A successful load exists with a DIFFERENT source_file_id (or a
      legacy record with no identity) -> the source file was corrected
      or replaced: raise ValueError. Only force_reload - the deliberate
      reprocess authorization - turns this into a "load" that replaces
      exactly this city/snapshot slice under audit.

    Returns "load" or "skip"; raises ValueError when a corrected file
    was selected without the explicit reprocess authorization.
    """
    if not isinstance(source_file_id, str) or not source_file_id.strip():
        raise ValueError("source_file_id is required to decide the ingestion action")

    successful = [
        control
        for control in existing_controls
        if control.get("city") == city
        and control.get("snapshot_date") == snapshot_date
        and control.get("status") == "success"
    ]

    if not successful:
        # No successful load yet for this slice: first load, a retry
        # after a failure, or a brand-new snapshot date.
        return "load"

    prior_id = latest_successful_source_file_id(successful)
    if prior_id == source_file_id:
        if force_reload:
            return "load"
        return "skip"

    if force_reload:
        return "load"

    raise ValueError(
        f"Corrected or replaced source file for {city}/{snapshot_date}: the "
        f"successful load used source_file_id {prior_id or '<legacy, no identity>'}, "
        f"but the selected file is {source_file_id}. A corrected file needs an "
        "explicit reprocess: set force_reload=true to authorize replacing "
        "exactly this city/snapshot slice. Without it, the run is blocked to "
        "protect the existing Bronze data."
    )


def latest_successful_source_file_id(
    controls: list[dict[str, Any]],
) -> str | None:
    """Return the source_file_id of the latest successful control row.

    "Latest" is the row with the newest completed_at_utc. Legacy rows
    without a source_file_id yield None. Used to link a controlled
    reprocess to the identity it replaces.
    """
    with_identity = [
        control for control in controls if control.get("status") == "success"
    ]
    if not with_identity:
        return None
    latest = max(
        with_identity,
        key=lambda control: (control.get("completed_at_utc") or "",),
    )
    return latest.get("source_file_id")


def _sanitize_error_message(error: Any) -> str:
    """Collapse whitespace, strip quotes and truncate an error message."""
    message = " ".join(str(error).split()).replace("'", "")
    return message[:_MAX_ERROR_MESSAGE]


def record_control_failure(
    spark: Any,
    control_table: str,
    run_id: str,
    error: Any,
) -> None:
    """Mark a started run failed with a sanitized, auditable message.

    Called from the ingestion cells when validation, parsing or the write
    raises: the control row for this run_id moves from 'running' to
    'failed' with the failure time and a truncated, injection-safe
    error message, so an aborted load leaves evidence instead of a
    stuck 'running' row.
    """
    if not _RUN_ID_PATTERN.fullmatch(str(run_id)):
        raise ValueError("run_id must be a hex identifier to record a failure")
    if not isinstance(control_table, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){1,2}", control_table
    ):
        raise ValueError("Expected catalog.schema.table for the control table")
    completed_at_utc = datetime.now(UTC).isoformat()
    message = _sanitize_error_message(error)
    spark.sql(
        f"UPDATE {control_table} "
        f"SET status = 'failed', "
        f"completed_at_utc = '{completed_at_utc}', "
        f"error_message = '{message}' "
        f"WHERE run_id = '{run_id}'"
    )
