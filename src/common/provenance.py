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
    *,
    source_file_id: str | None = None,
    file_hash_sha256: str | None = None,
) -> dict[str, str]:
    """Return standard metadata attached to every Bronze record.

    The optional manifest-backed fields are included only when
    provided: legacy callers that ingest without the F04 manifest keep
    receiving exactly the six base keys, while F05.2 callers add the
    governed source-file identity and content hash to every row.
    """
    provenance = {
        "source": source,
        "city": city,
        "snapshot_date": snapshot_date,
        "raw_path": raw_path,
        "run_id": run_id,
        "ingested_at_utc": datetime.now(UTC).isoformat(),
    }
    for key, value in (
        ("source_file_id", source_file_id),
        ("file_hash_sha256", file_hash_sha256),
    ):
        if value:
            provenance[key] = value
    return provenance
