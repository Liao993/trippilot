# TripPilot Progress

> Concise, evidence-based status ledger. The Project Plan defines the roadmap, the Unified Build Guide defines the implementation workflow, and this file records actual progress, verified outcomes, blockers, and the next task.

## 1. Project Status

- **Project:** TripPilot — AI-enabled travel discovery and planning platform
- **Current phase:** Airbnb data platform — summary and neighbourhood Bronze ingestion completed
- **Completed through:** F06.3, the pre-F07 cleanup (T01–T14), the post-cleanup verification audit, the listings control-table rename (R1, branch `chore/listings-control-rename`), the legacy control-table drop, live source-manifest registration and the first live calendar/reviews Bronze ingestion (2026-11-19), F07.1 summary/neighbourhood registration and F07.2 Bronze ingestion (2026-11-23, branch `feature/f07-2-bronze-ingestion`)
- **Next task:** F07.3
- **Roadmap:** Project Plan v31
- **Build workflow:** Unified Build Guide v31

## 2. Completed Features

| Feature | Status | Outcome |
|---|---|---|
| F02 — Foundation and environment isolation | Complete | Databricks project foundation, table configuration, test/live isolation |
| F03 — CI and validation | Complete | Automated code, configuration, notebook, and security checks |
| F04 — Source acquisition and manifest | Complete | Source registration, immutable landing, file identity and run controls |
| F05 — Airbnb listings Bronze/Silver | Complete | Listings ingestion, Bronze/Silver processing, identity-aware reruns |
| F06.1 — Calendar and reviews contracts | Complete | Source inspection, schema contracts and source registration in test mode |
| F06.2 — Calendar and reviews Bronze ingestion | Complete | Separate ingestion paths, raw-data preservation, quality annotations and reconciliation |
| F06.3 — Quality and rerun controls | Complete | Dataset-scoped run controls, retry handling, failure isolation and reconciliation |
| Pre-F07 cleanup — storage, code and data reconciliation | Complete | Shared Bronze flow (calendar/reviews notebooks thinned to 4 cells), standardized idempotent control-table setup, post-landing staging cleanup, duplicate retirement, live manifest created, 286 tests green |
| F07.1 — Summary and neighbourhood registration | Complete | Plain-CSV and GeoJSON staged-content validation and inspection in acquisition, hash-versioned landing, four new identities registered in both test and live manifests (schema_versions reproduce the merged F07.1 guide's recorded values) |
| F07.2 — Summary and neighbourhood Bronze | Complete | File-type dispatch in the shared Bronze flow (csv.gz/csv/geojson), one-row-per-feature GeoJSON ingestion with full geometry preserved as `geometry_json`, feature counts recorded and reconciled, four new Bronze products and control tables in test and live, 322 tests green |

## 3. Verified Airbnb Data State

**Airbnb data validation: Passed.**

| Dataset | Records | Invalid records | Status |
|---|---:|---:|---|
| Listings | 22,050 | Previously validated | Passed |
| Calendar | 8,048,251 | 0 | Passed |
| Reviews | 729,202 | 0 | Passed |
| Listings summary | 22,050 | 0 | Passed |
| Reviews summary | 729,202 | 0 | Passed |
| Neighbourhoods (CSV) | 140 | 0 | Passed |
| Neighbourhood geometry (GeoJSON) | 140 | 0 | Passed |

- Calendar and reviews were processed using the full source files, not sampled datasets.
- Source data was preserved as raw strings in Bronze.
- Data quality annotations and provenance metadata were retained.
- Dataset-level reconciliation passed.
- Rerun, new-snapshot, corrected-file and failure-isolation validation passed.
- F06 runtime validation was performed using isolated test-mode destinations.
- Existing canonical listings data was not modified during F06 validation.
- 2026-11-19: the three real source identities were registered into the live manifest (licence CC BY 4.0, chosen per the Project Plan v31 data-licence statement) and the first live calendar and reviews ingestion created `airbnb_calendar_bronze` (8,048,251 rows) and `airbnb_reviews_bronze` (729,202 rows); all rows valid, control records `success`, Bronze reached its full 12-table end state.
- 2026-11-23 (F07.1/F07.2, branch `feature/f07-2-bronze-ingestion`): the four remaining 2026-09-16 files were registered into both the test and live manifests through the acquisition flow with the new plain-CSV/GeoJSON staged-content validation — schema_versions reproduce the merged F07.1 guide's recorded values exactly (`summary-listings-sha256:6d5eeaa74190cf08`, `summary-reviews-sha256:9f1260580cdd24d2`, `neighbourhoods-sha256:d2259d198ebd6435`, `neighbourhood-geojson-sha256:90f71a0951417639`, GeoJSON feature count 140). After the full test-mode evidence gate (isolation, idempotent retries, an invalid-GeoJSON failure drill with a sanitized `failed` manifest record, skip/no-op rerun protection and force-reload slice replacement), the first live ingestion created `airbnb_listings_summary_bronze` (22,050), `airbnb_reviews_summary_bronze` (729,202), `airbnb_neighbourhoods_bronze` (140) and `airbnb_neighbourhood_geometry_bronze` (140) — one run identity per slice, zero invalid rows, `success` control records. Summary/neighbourhood products stay separate assets (never unioned with the detailed facts); the GeoJSON preserves each feature's full geometry object as compact JSON. Bronze row counts were cross-checked against the raw landed bytes with an independent CSV parser (22,050 data rows × 19 columns; `wc -l` overcounts by 131 due to quoted embedded newlines) and against the GeoJSON feature count (140, all MultiPolygon). `_staging` is empty; the landing directory holds exactly the 7 manifest-registered immutable objects. 322 unit tests, ruff format/check, config validation and notebook validation all pass.

## 4. Current Environment

- Databricks Catalog: `trippilot_dev`
- Schemas: `bronze`, `silver`, `gold`, `ops`
- Compute: Serverless
- Runtime: Python 3.12 / Spark 4.x
- Current data source: Inside Airbnb
- Initial city: Toronto
- Source snapshot: `2026-09-16`

Test and live destinations now come from the standardized, idempotent setup (`notebooks/ops/setup_control_tables.py`): canonical control shapes (10/11 columns), the 17-field manifest contract in both modes, and resolver-driven isolation. The live listings control table was evolved in place to the 10-column shape. Root duplicate uploads and the `_incoming` staging leftover were hash-verified against the immutable landed objects and removed.

**Post-cleanup verification audit and listings control rename (2026-11-19, R1):** a fresh evidence-based audit confirmed the cleanup end state — the 3 immutable landed 2026-09-16 source objects match the manifest records exactly (hash, size, landing path), `_incoming` staging is empty by design (post-landing cleanup works), and there are no orphaned files or tables. The listings ingestion control was renamed to the dataset-specific convention: `airbnb_listings_ingestion_control`(`_test`), resolver key `listings_control`. All 1 live and 11 test control records were copied to the new tables and verified identical (symmetric EXCEPT, zero differences); resolver, table setup, listings notebook and tests were updated and gated (286 tests, ruff format, config + notebook validation). The old `airbnb_ingestion_control`(`_test`) tables were dropped on 2026-11-19 after explicit user approval; their history had already been migrated to and verified in the new tables. Live `airbnb_calendar_bronze` / `airbnb_reviews_bronze` were created on 2026-11-19 by their first live ingestion runs, after the three real source identities were registered into the live manifest through the acquisition flow.

**Acquisition staging rename (2026-11-19, `_incoming` → `_staging`):** at operator request the staging folder was renamed following the build guide's rename checklist. Code (`STAGING_DIR_NAME`, `approved_staging_roots` in `src/common/source_acquisition.py`), both acquisition test suites, the acquire notebook's widget defaults and labels, and the listings notebook were updated together; the empty `_incoming` directory tree on the volume was removed and `_staging` created (staged files are deleted after landing by design — only leftover empty folders existed, no data). All gates pass (286 tests, ruff format, config + notebook validation; ruff check shows only the pre-existing workspace EXE002 artifacts). Historical manifest records keep their original `_incoming` staging paths — manifests are immutable history.

## 5. Outstanding Items

- Verify the registered licence text (CC BY 4.0, chosen from the Project Plan v31 data-licence statement when the operator deferred confirmation) against the current official Inside Airbnb data policy; live manifest records are immutable, so a confirmed mismatch requires a documented remediation. This applies to the three 2026-11-19 records and the four 2026-11-23 records alike.
- The four 2026-11-23 manifest records use `retrieved_at_utc` at date precision (`2026-11-23T00:00:00Z`): the exact download time was not recorded. Corrected-in-place metadata is impossible on immutable manifest records; if exact times are later needed, re-register from the immutable landed objects with a documented correction file.
- Decide the retirement of exploration stubs (`notebooks/exploration/`); they still reference the retired root upload paths.
- `config/project.yml` still carries the legacy `file_format: csv_gzip` keys on the pre-F07 dataset entries (superseded by the manifest's `file_type`); F07.1 D2 left them untouched as out of scope.

## 6. Next Task

**F07.3.**

F07.1 and F07.2 completed on 2026-11-23: the four summary/neighbourhood identities are registered in the live manifest, all four Bronze products exist live with reconciled single-slice loads, and the volume end state is clean (empty `_staging`, 7 immutable landed objects).

Scope (per Project Plan v31):

1. F07.3 validation/replacement work on the summary and neighbourhood sources.
2. Verify the registered licence text against the current official Inside Airbnb data policy (records are immutable; a confirmed mismatch requires a documented remediation).
3. Decide the retirement of exploration stubs.

Detailed implementation history, file hashes, schemas, run IDs, test drills and technical decisions are retained in feature documentation, GitHub PRs and Notion rather than duplicated here.
