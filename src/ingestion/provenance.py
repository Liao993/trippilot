"""
This keeps reusable logic in src/, where your existing CI can lint and test it. The plan recommends src/ for reusable behavior and tests/ for checks.
"""
"""Reusable provenance metadata for TripPilot ingestion pipelines."""

from datetime import UTC, datetime
from uuid import uuid4


def build_run_id() -> str:
    """Create a unique identifier for one ingestion execution."""
    return uuid4().hex


def build_provenance_columns(
    source: str,
    city: str,
    snapshot_date: str,
    raw_path: str,
    run_id: str,
) -> dict[str, str]:
    """Return standard metadata attached to every Bronze record."""
    return {
        "source": source,
        "city": city,
        "snapshot_date": snapshot_date,
        "raw_path": raw_path,
        "run_id": run_id,
        "ingested_at_utc": datetime.now(UTC).isoformat(),
    } 