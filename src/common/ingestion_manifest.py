"""Unified ingestion manifest (F07.4): one row per source file per run.

One shared table per environment (``ops.ingestion_manifest`` in each
catalog) records the outcome of every dataset load. A run that loads
several source assets writes one row per asset, sharing the ``run_id``;
one asset failing never disturbs another asset's row.

The column set deliberately extends the F06.3 per-dataset control
shape so migrated history stays compatible and
``decide_ingestion_action``/``should_load`` keep working unchanged
(rows are read as dicts with the same keys). The proposed F07.4 field
names map as: ingestion_run_id->run_id, dataset_type->dataset,
city_id->city, source_snapshot_date->snapshot_date, load_status->status,
load_started_at->started_at_utc, load_completed_at->completed_at_utc.
source_url/source_file_name/source_content_hash are NOT duplicated:
``ops.source_file_manifest`` carries them, referenced by
``source_file_id``.

Semantics:
- Identity/idempotency: (dataset, city, snapshot_date, source_file_id)
  identifies the exact bytes; decide_ingestion_action (reused,
  unchanged) turns that into skip/exact-rerun/replace decisions.
- status lifecycle: running -> success | failed; source availability
  states (F07.3) live in ops.source_file_availability, never here.
- counts: source_row_count = raw rows read from the landed object
  (header excluded for CSV), loaded_row_count = rows written to the
  target slice, rejected_row_count = rows retained but flagged invalid
  by the row-quality policy (so loaded = source, valid + rejected).
- prior_source_file_id: when a controlled reprocess replaces a
  corrected file, the identity of the superseded load.
- target_table: fully qualified table in the run's own catalog.
"""

import re
from collections.abc import Mapping
from typing import Any

from src.common.table_setup import (
    INGESTION_MANIFEST_COLUMNS,
    ensure_operational_table,
)

# Controlled dataset tags: exactly the seven Airbnb source assets the
# ingestion code supports (F06/F07). No arbitrary strings.
INGESTION_DATASETS: tuple[str, ...] = (
    "listings",
    "calendar",
    "reviews",
    "listings_summary",
    "reviews_summary",
    "neighbourhoods",
    "neighbourhood_geometry",
)

# Controlled load lifecycle. not_published/not_available is a SOURCE
# property recorded in the availability ledger (F07.3), never a load
# status: a load that never started leaves no row here. F08.3 state
# model: `pending` is derived from the absence of a row (coverage
# reporting only); running/success/failed stay the stored lifecycle.
INGESTION_STATUSES: tuple[str, ...] = ("running", "success", "failed")

# A manifest row is terminal once success/failed; only a running row
# may transition. Retries of a failed load are NEW rows (new run_id).
VALID_STATUS_TRANSITIONS: Mapping[str, tuple[str, ...]] = {
    "running": ("success", "failed"),
    "success": (),
    "failed": (),
}

_RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8,64}$")
_TABLE_NAME_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){1,2}$"
)


def validate_dataset(dataset: str) -> str:
    """Return the dataset tag or raise for an unsupported dataset."""
    if dataset not in INGESTION_DATASETS:
        raise ValueError(
            f"Unknown dataset {dataset!r}. Expected one of {INGESTION_DATASETS}."
        )
    return dataset


def validate_status(status: str) -> str:
    """Return the load status or raise for an unsupported status."""
    if status not in INGESTION_STATUSES:
        raise ValueError(
            f"Unknown load status {status!r}. Expected one of {INGESTION_STATUSES}."
        )
    return status


def validate_status_transition(from_status: str, to_status: str) -> None:
    """Raise when a status change violates the documented lifecycle."""
    validate_status(from_status)
    validate_status(to_status)
    if to_status not in VALID_STATUS_TRANSITIONS[from_status]:
        raise ValueError(
            f"Invalid manifest status transition {from_status!r} -> {to_status!r}; "
            f"allowed: {VALID_STATUS_TRANSITIONS[from_status] or ('<terminal>',)}"
        )


def _validate_table_name(table_name: str) -> str:
    if not isinstance(table_name, str) or not _TABLE_NAME_PATTERN.fullmatch(table_name):
        raise ValueError(
            f"Invalid ingestion manifest table name {table_name!r}; expected a "
            "plain catalog.schema.table (or schema.table) identifier"
        )
    return table_name


def sql_string_literal(value: Any) -> str:
    """Render one value as a safely escaped SQL string literal."""
    if value is None:
        raise ValueError("SQL string literal requires a value; use NULL explicitly")
    return "'" + str(value).replace("'", "''") + "'"


def _validate_counts(
    source_row_count: int | None,
    loaded_row_count: int | None,
    rejected_row_count: int | None,
) -> None:
    for name, count in (
        ("source_row_count", source_row_count),
        ("loaded_row_count", loaded_row_count),
        ("rejected_row_count", rejected_row_count),
    ):
        if count is None:
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{name} must be a non-negative integer or NULL")


def build_ingestion_start_sql(
    manifest_table: str,
    *,
    city: str,
    snapshot_date: str,
    run_id: str,
    dataset: str,
    source_file_id: str,
    prior_source_file_id: str | None,
    started_at_utc: str,
    target_table: str,
) -> str:
    """Return the INSERT that starts one manifest row (status running).

    One row per source file per ingestion run: a multi-asset run
    inserts one row per asset, all sharing the run_id.
    """
    _validate_table_name(manifest_table)
    validate_dataset(dataset)
    if not _RUN_ID_PATTERN.fullmatch(str(run_id)):
        raise ValueError("run_id must be a hex identifier to start a manifest row")
    for label, value in (
        ("city", city),
        ("snapshot_date", snapshot_date),
        ("source_file_id", source_file_id),
        ("started_at_utc", started_at_utc),
        ("target_table", target_table),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required to start a manifest row")

    prior = (
        "NULL"
        if prior_source_file_id is None
        else sql_string_literal(prior_source_file_id)
    )
    # Positional values follow the INGESTION_MANIFEST_COLUMNS order.
    return (
        f"INSERT INTO {manifest_table} VALUES ("
        f"{sql_string_literal(city)}, "
        f"{sql_string_literal(snapshot_date)}, "
        f"{sql_string_literal(run_id)}, "
        f"{sql_string_literal(dataset)}, "
        f"{sql_string_literal(source_file_id)}, "
        f"{prior}, "
        "'running', "
        "NULL, NULL, NULL, "
        f"{sql_string_literal(started_at_utc)}, "
        "NULL, "
        f"{sql_string_literal(target_table)}, "
        "NULL)"
    )


def build_ingestion_success_sql(
    manifest_table: str,
    *,
    run_id: str,
    source_row_count: int | None,
    loaded_row_count: int | None,
    rejected_row_count: int | None,
    completed_at_utc: str,
) -> str:
    """Return the UPDATE that completes a running row as success.

    Count reconciliation: source_row_count is everything read,
    loaded_row_count everything written to the target slice, and
    rejected_row_count the rows retained but flagged invalid (so
    loaded == source and valid + rejected reconcile in-table).
    """
    _validate_table_name(manifest_table)
    if not _RUN_ID_PATTERN.fullmatch(str(run_id)):
        raise ValueError("run_id must be a hex identifier to complete a run")
    _validate_counts(source_row_count, loaded_row_count, rejected_row_count)
    if not isinstance(completed_at_utc, str) or not completed_at_utc.strip():
        raise ValueError("completed_at_utc is required to complete a run")

    counts = ", ".join(
        f"{name} = {count if count is not None else 'NULL'}"
        for name, count in (
            ("source_row_count", source_row_count),
            ("loaded_row_count", loaded_row_count),
            ("rejected_row_count", rejected_row_count),
        )
    )
    return (
        f"UPDATE {manifest_table} SET status = 'success', {counts}, "
        f"completed_at_utc = {sql_string_literal(completed_at_utc)}, "
        f"error_message = NULL WHERE run_id = {sql_string_literal(run_id)}"
    )


def build_manifest_read_sql(
    manifest_table: str,
    *,
    city: str,
    snapshot_date: str,
) -> str:
    """Return the SELECT of every manifest row for one city/snapshot.

    All datasets of the slice are returned as dicts; the reused
    decision helpers (decide_ingestion_action, should_load) scope by
    dataset tag themselves.
    """
    _validate_table_name(manifest_table)
    for label, value in (("city", city), ("snapshot_date", snapshot_date)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required to read a slice")
    return (
        f"SELECT * FROM {manifest_table} "
        f"WHERE city = {sql_string_literal(city)} "
        f"AND snapshot_date = {sql_string_literal(snapshot_date)}"
    )


def build_manifest_list_city_dataset_sql(
    manifest_table: str,
    *,
    city: str,
    dataset: str,
) -> str:
    """Return the SELECT of every manifest row for one city/dataset (F08.6).

    Coverage reporting derives a slice's latest load status from these
    rows; `pending` itself is derived from their absence and is never
    a stored status.
    """
    _validate_table_name(manifest_table)
    validate_dataset(dataset)
    if not isinstance(city, str) or not city.strip():
        raise ValueError("city is required to read a city/dataset slice")
    return (
        f"SELECT * FROM {manifest_table} "
        f"WHERE city = {sql_string_literal(city)} "
        f"AND dataset = {sql_string_literal(dataset)}"
    )


class IngestionManifestStore:
    """Thin Spark-injected repository over one environment's manifest.

    Delegates shape creation/evolution to the shared
    ``ensure_operational_table`` helper so setup stays idempotent and
    additive-only.
    """

    def __init__(self, table_name: str, spark: Any = None) -> None:
        self.table_name = _validate_table_name(table_name)
        self.spark = spark

    def _require_spark(self) -> Any:
        if self.spark is None:
            raise ValueError(
                "Spark session is required to use the ingestion manifest store"
            )
        return self.spark

    def ensure_table(self) -> str:
        """Create the table when missing / evolve it forward; idempotent.

        Returns "ok" or "evolved" (see ensure_operational_table).
        """
        return ensure_operational_table(
            self._require_spark(), self.table_name, INGESTION_MANIFEST_COLUMNS
        )

    def start_run(self, record: Mapping[str, Any]) -> None:
        """Insert one running manifest row from a mapping of fields."""
        self._require_spark().sql(
            build_ingestion_start_sql(
                self.table_name,
                city=record["city"],
                snapshot_date=record["snapshot_date"],
                run_id=record["run_id"],
                dataset=record["dataset"],
                source_file_id=record["source_file_id"],
                prior_source_file_id=record.get("prior_source_file_id"),
                started_at_utc=record["started_at_utc"],
                target_table=record["target_table"],
            )
        )

    def complete_run(
        self,
        *,
        run_id: str,
        source_row_count: int | None,
        loaded_row_count: int | None,
        rejected_row_count: int | None,
        completed_at_utc: str,
    ) -> None:
        """Update the run's row to success with reconciled counts."""
        self._require_spark().sql(
            build_ingestion_success_sql(
                self.table_name,
                run_id=run_id,
                source_row_count=source_row_count,
                loaded_row_count=loaded_row_count,
                rejected_row_count=rejected_row_count,
                completed_at_utc=completed_at_utc,
            )
        )

    def read_for_slice(self, city: str, snapshot_date: str) -> list[dict[str, Any]]:
        """Return every manifest row for the city/snapshot as dicts."""
        rows = (
            self._require_spark()
            .sql(
                build_manifest_read_sql(
                    self.table_name, city=city, snapshot_date=snapshot_date
                )
            )
            .collect()
        )
        return [row.asDict() for row in rows]

    def list_for_city_dataset(self, city: str, dataset: str) -> list[dict[str, Any]]:
        """Return every manifest row for the city/dataset as dicts (F08.6)."""
        rows = (
            self._require_spark()
            .sql(
                build_manifest_list_city_dataset_sql(
                    self.table_name, city=city, dataset=dataset
                )
            )
            .collect()
        )
        return [row.asDict() for row in rows]
