# Standardized operational-table setup for both run modes (pre-F07
# cleanup T02).
#
# This script is the single place that creates or repairs the
# ingestion-control, quality-results and source-manifest tables, with
# every destination resolved through the shared environment resolver -
# the same isolation rules the ingestion notebooks use. It is
# idempotent: rerunning it never drops or overwrites data.
#
# - listings control: 10-column shape (source_file_id +
#   prior_source_file_id); a legacy 8-column table is evolved in place,
#   preserving all history.
# - calendar/reviews controls: 11-column per-dataset shape with the
#   explicit dataset tag (F06.3).
# - ops.quality_results: run-quality results sink.
# - ops.source_file_manifest: created from the tested ManifestStore
#   contract (17 fields, idempotent MERGE upserts).
#
# RUN_MODE selects the destination exactly like the ingestion notebooks:
# "test" (default) initializes the isolated *_test tables; "live"
# initializes the canonical development tables and is an intentional
# promotion step - edit it explicitly before running.

# Databricks notebook source
RUN_MODE = "test"  # "test" | "live"

from pathlib import Path
import sys

start = Path.cwd().resolve()
ROOT = next(
    (
        p
        for p in [start, *start.parents]
        if (p / "src").is_dir() and (p / "config/project.yml").is_file()
    ),
    None,
)
if ROOT is None:
    raise RuntimeError(
        "Cannot locate the TripPilot repository root (src/ and config/project.yml)."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.environment import resolve_tables, validate_run_mode
from src.common.source_manifest_store import ManifestStore
from src.common.table_setup import ensure_operational_tables, ensure_schemas

mode = validate_run_mode(RUN_MODE)
tables = resolve_tables(mode)

print(f"Setting up TripPilot operational tables in {mode!r} mode")
print(f"Schemas ensured: {', '.join(ensure_schemas(spark, tables.values()))}")

actions = ensure_operational_tables(spark, tables)
for key, action in sorted(actions.items()):
    print(f"{key:18} {action:8} {tables[key]}")

manifest_store = ManifestStore(tables["source_manifest"], spark=spark)
manifest_store.ensure_table()
print(f"{'source_manifest':18} {'ready':8} {tables['source_manifest']}")
print("Operational tables ready.")
