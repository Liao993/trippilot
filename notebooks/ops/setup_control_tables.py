# Standardized operational-table setup for both run modes (pre-F07
# cleanup T02; F07.4 catalog separation + unified ingestion manifest).
#
# This script is the single place that creates or repairs the unified
# ingestion-manifest, quality-results and source-manifest tables, with
# every destination resolved through the shared environment resolver -
# the same isolation rules the ingestion notebooks use. It is
# idempotent: rerunning it never drops or overwrites data.
#
# - The run mode's catalog is created when missing (F07.4: "test" uses
#   the dedicated trippilot_test catalog, "live" uses trippilot_dev),
#   then its schemas, then the operational tables.
# - ops.ingestion_manifest: ONE shared run-control table per
#   environment, one row per source file per ingestion run (F07.4; it
#   replaced the seven per-dataset control tables after their history
#   was migrated).
# - ops.quality_results: run-quality results sink.
# - ops.source_file_manifest: created from the tested ManifestStore
#   contract (18 fields since F07.3 adds the optional classified
#   error_type; an existing table is evolved in place), idempotent
#   MERGE upserts.
# - ops.source_file_availability: created from the tested
#   AvailabilityStore contract (F07.3-T01), the evidence-backed
#   ledger for expected assets the source did not publish.
#
# RUN_MODE selects the destination exactly like the ingestion notebooks:
# "test" (default) initializes the dedicated trippilot_test catalog;
# "live" initializes the canonical development tables and is an
# intentional promotion step - edit it explicitly before running.

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

from src.common.environment import (
    catalog_for,
    resolve_tables,
    validate_run_mode,
)
from src.common.source_availability import AvailabilityStore
from src.common.source_manifest_store import ManifestStore
from src.common.table_setup import (
    ensure_catalog,
    ensure_operational_tables,
    ensure_schemas,
)

mode = validate_run_mode(RUN_MODE)
tables = resolve_tables(mode)

print(f"Setting up TripPilot operational tables in {mode!r} mode")
print(f"Catalog ensured: {ensure_catalog(spark, catalog_for(mode))}")
print(f"Schemas ensured: {', '.join(ensure_schemas(spark, tables.values()))}")

actions = ensure_operational_tables(spark, tables)
for key, action in sorted(actions.items()):
    print(f"{key:18} {action:8} {tables[key]}")

manifest_store = ManifestStore(tables["source_manifest"], spark=spark)
manifest_store.ensure_table()
print(f"{'source_manifest':18} {'ready':8} {tables['source_manifest']}")

availability_store = AvailabilityStore(tables["source_availability"], spark=spark)
availability_store.ensure_table()
print(f"{'source_availability':18} {'ready':8} {tables['source_availability']}")
print("Operational tables ready.")
