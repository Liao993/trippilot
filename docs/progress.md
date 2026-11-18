# TripPilot progress

Concise, high-level record of verified state. Detailed task narratives live in the merged PRs and the Notion child pages; this file keeps what a new session needs: current position, verified facts and identities, standing conventions, blockers and next steps.

## Roadmap position (Project Plan v29 / Build Guide v30)

**F06.3 — file-level quality and rerun validation: complete on `feature/f06-3-run-controls` (tested commit `885d550`, PR pending). Next: F07 (not started — F06.3 stopped per the handoff).**

- `main` @ `b7b97ae` (2026-11-18): includes the pre-F06 cleanup (PR #22 → `6f4dfa4`), the plan/guide docs (PR #23), F06.1 source contracts (PR #24) and F06.2 Bronze ingestion (PR #25).
- Feature history: F02 foundation migration + run-mode isolation (PRs #11–#13); F03 CI baseline, contract/notebook validation, secret scanning (PRs #13–#15); F04 source manifest, acquisition/immutable landing, run controls (PRs #16–#18); F05 listings inspection/registration, manifest-backed Bronze, identity-aware reprocessing (PRs #19–#21, merge commits `289d281` / `093ee31` / `8deb9c8`); F06.1 calendar/review source contracts (PR #24, merge `c585d9f`).
- CI note: the workflow's push trigger covers `main` and `feature/add-ci` only — every other branch gets CI via the pull-request check or a manual `workflow_dispatch`.

## Environment (verified 2026-11-12; unchanged since)

- Catalog `trippilot_dev` with schemas `bronze`/`silver`/`gold`/`ops`; managed Volume `trippilot_dev.bronze.source_files` at `/Volumes/trippilot_dev/bronze/source_files`; staging convention `_incoming/insideairbnb/toronto/`.
- Serverless compute, Python 3.12.3, Spark 4.3.0.dev0 (Python ≥3.11 required).
- City: Toronto; Inside Airbnb snapshot family `2026-09-16`.
- Live tables: `bronze.airbnb_listings_bronze` 22,050; `bronze.airbnb_ingestion_control` 1; `silver.airbnb_listings_silver` 22,050; `silver.airbnb_listings_rejected` 0; `ops.quality_results` 0 (production Bronze/control date from the F02 migration). The live `ops.source_file_manifest` is deliberately NOT created yet — the first real (post-licence) acquisition creates it; tests use `ops.source_file_manifest_test`.

## Governed source files (all verified; manifest rows currently in the TEST table only, pending the licence gate)

Root files at `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/`; each lands immutably at `<version>/<name>__<sha256[:12]>.csv.gz` under the same tree:

- **listings.csv.gz** — 13,117,826 bytes; sha256 `e84fe1a5ff1735d5676fe0da211cc12bab2ab9050c3ddc64a4b8a939d5b11d19`; landed `2026-09-16/listings__e84fe1a5ff17.csv.gz`; `source_file_id` `26de1c3ce6216172d8faf28ddad8c789e40c1d5eb02a608ce98dea1fb08e3a68`; schema `detailed-listings-sha256:061445eae4bb06f8` (90 columns, new-generation header).
- **calendar.csv.gz** — 18,619,348 bytes; sha256 `f5eb68a9691d8187739ff2def780166bd917870e833431a36448e8e1d4c39de3`; landed `2026-09-16/calendar__f5eb68a9691d.csv.gz`; `source_file_id` `09a7ef20b005bc7fb5ee0abdb6ba27f07a2d2e72a62885351442702ef38fefb2`; schema `calendar-sha256:eac60c6598969586` (5 columns).
- **reviews.csv.gz** — 77,707,803 bytes; sha256 `78f4e72aae1fbe61ba49b421bd71b4fd085368a642962b5951e9626f466588dd`; landed `2026-09-16/reviews__78f4e72aae1f.csv.gz`; `source_file_id` `7c5ada51f8e413854aa4a567d781617746b8421ced84b2f0e6e86ec79cd12be0`; schema `detailed-reviews-sha256:246ea39b2dab730b` (6 columns).

## Feature summaries (F02–F05)

- **F02 — foundation migration + isolation (PRs #11–#13):** repository migrated to `Liao993/trippilot`; `src.common.environment` resolves every logical table to isolated `*_test` Delta tables in test mode (the default), so test runs can never write development tables; Bronze/Silver notebooks are widget-driven. Reconciliation: raw 22,050 = bronze_test = silver_test + rejected 0.
- **F03 — CI + validation (PRs #13–#15):** `lint-test.yml` runs ruff check/format, YAML config validation (`src.quality.config_validation`), notebook-source validation (`src.quality.notebook_validation`), pip-audit and gitleaks on PRs to `main`; branch protection requires both jobs; Databricks deployment go/no-go deferred (no service principals, bundles or non-production target exist).
- **F04 — governed acquisition (PRs #16–#18):** `source_manifest.py` (17-field contract, deterministic `source_file_id` = SHA-256 over family|entity|version|file-type|content-hash, registered→validated→landed/failed state machine, credential-redacted errors); `source_acquisition.py` (approved `_incoming` staging, gzip signature + 2-GiB checks, hash-verified atomic never-overwrite landing, per-file failure isolation, reprocess from landed objects without re-download); `source_manifest_store.py` (`ManifestStore` MERGE keyed by `source_file_id`, immutable identity/metadata, operational-fields-only updates).
- **F05 — listings end-to-end (PRs #19–#21):** header inspection with content-addressed schema fingerprints; manifest-backed Bronze (reads only the landing object; 8 provenance columns `_source`…`_file_hash_sha256`; atomic `replaceWhere`+`mergeSchema` slice replace); identity-aware skip/blocked/force decisions with prior-id audit trail; pre-write validation (hash/size, full gzip decompress, required columns, schema drift). Test-mode drills covered idempotent reruns, new-snapshot slices, corrected-file controlled replacement and failure isolation; `read_landed_by_identity` resolves a single landed record or raises on ambiguity.

## F06.1 — Calendar and review source contracts (2026-11-17; complete on `feature/f06-1-source-contracts`, tested commit `c1dacf84ef13f35038be0066f762aa78cc8a2451`; merged via PR #24, merge commit `c585d9f`)

Scope (F06.1-T01/T02): inspect `calendar.csv.gz` and `reviews.csv.gz` independently, register both in the shared F04 manifest, and create Bronze source contracts from the observed schemas. No Bronze writes (F06.2), no Silver (F08/F09).

Observed grains (verified by profiling, never assumed):

- **Calendar** — 5 columns `listing_id,date,available,minimum_nights,maximum_nights`; 8,048,251 rows; grain one row per `listing_id`+`date` with zero duplicate keys; 22,050 listings; date window 2026-09-17 → 2027-09-17; `available` ∈ {t,f}; no duplicate/blank header names. Schema version `calendar-sha256:eac60c6598969586`.
- **Reviews** — 6 columns `listing_id,id,date,reviewer_id,reviewer_name,comments`; **729,202 rows** (F06.1 profiling recorded 729,190 — an undercount corrected in F06.2 by dual-parser verification: Spark multiLine+escape and Python `csv` both parse 729,202, and all (listing_id,id) pairs are unique); grain one row per `listing_id`+`id` — **the review `id` alone is NOT unique**: 183 ids are attached to 2–9 listings each (839 extra rows) with identical review content, and there are zero full-row duplicates. Dates 2010-06-07 → 2026-09-18, all ISO `YYYY-MM-DD`, no blank keys; 17,764 listings have reviews (4,286 of 22,050 have none). Schema version `detailed-reviews-sha256:246ea39b2dab730b`.
- Both gzip streams fully decompress (291,714,020 / 207,510,679 bytes expanded).

Snapshot derivation (evidence, not assumption): the calendar window starts 2026-09-17 — the day after the Inside Airbnb compile date — and its 22,050 `listing_id`s exactly equal the F05 listings Bronze set (zero orphans both directions); reviews' `listing_id`s are a subset of that same set; both files were uploaded together. Both files therefore belong to the **2026-09-16** publication batch. The operator should still confirm the official publication date alongside the licence confirmation below.

Changes (tested commit `c1dacf8`, 6 files):

- `src/airbnb/source_inspection.py` — `inspect_csv_gz_header` gained a `schema_label` parameter (default `detailed-listings`); calendar and review files now register correctly-labelled schema versions instead of a mislabelled listings schema.
- `contracts/airbnb/bronze_calendar.yml` + `contracts/airbnb/bronze_reviews.yml` — created from the observed schemas only: required columns, `source_types: string` (no coercion before Silver), `replace_city_snapshot` + `explicit_reprocess_replace_slice`, the 8 provenance columns, grains documented in comments.
- `src/quality/config_validation.py` — both contracts registered in `CONFIG_FILES`; the Bronze contract validator generalized to per-file rules keys (`BRONZE_CONTRACT_RULES_KEYS`).
- `tests/airbnb/test_source_inspection.py` + `tests/quality/test_config_validation.py` — +8 tests (schema_label behaviour; per-contract valid/invalid; wrong-key detection; extended missing-file/invalid-YAML paths).

Verification:

- Local gate on the tested tree: `ruff check` — only the EXE002 workspace-mode artifact (git records every file 100644; CI unaffected); `ruff format --check` clean; `python -m src.quality.config_validation` pass (7 files); `python -m src.quality.notebook_validation` pass; `pytest` **227 passed** (was 219).
- Runtime (test mode only — isolated `ops.source_file_manifest_test`): staged copies hash-equal to the root files; both identities landed with the hashes/sizes/source_file_ids in the Governed source files section above; two distinct `source_file_id`s; Delta read-back `landed`; staged `_incoming` copies removed afterwards. No Bronze table was written; production tables unchanged (bronze 22,050 / control 1 / silver 22,050 / rejected 0); the live `ops.source_file_manifest` remains absent.
- Licence: both files registered with the clearly-marked TEST-ONLY placeholder licence (F05.2 precedent) — production registration withheld, see blockers.
- F06.2 design note: with listings, calendar and reviews all landed for identity `insideairbnb/toronto/2026-09-16` + `csv.gz`, `read_landed_by_identity` is now ambiguous (verified: it raises listing all three landed records). F06.2 must resolve per-dataset identities — explicit `source_file_id` selection (the F05.3 widget already exists) or per-dataset entity ids. (Resolved in F06.2: both notebooks resolve by explicit `source_file_id`.)

## F06.2 — Separate calendar/review Bronze ingestion paths (2026-11-17; complete on `feature/f06-2-bronze-ingestion`, tested commit `0a1419bc67abe089903fc6684156538954316098`; merged via PR #25, merge commit `b7b97ae`)

Scope (F06.2-T01/T02/T03): Bronze ingestion for both new datasets from their immutable manifest landing objects — raw-string preservation, contract-driven row-quality marking with retention, separate data products, per-file reconciliation. No Silver, no joins, no control-table rows (F06.3 resolves the city/snapshot key collision).

Changes (tested commit `0a1419b`, 10 files):

- `src/common/environment.py` — LIVE_TABLES keys `calendar_bronze`/`reviews_bronze` → `trippilot_dev.bronze.airbnb_calendar_bronze` / `airbnb_reviews_bronze` (test mode → `*_test`).
- `contracts/airbnb/bronze_calendar.yml` + `bronze_reviews.yml` — `row_validation` blocks from the observed grains (required fields + ISO-date fields).
- `src/quality/config_validation.py` — enforces the `row_validation` shape (mapping; non-empty string list; date fields ⊆ required).
- `src/airbnb/row_quality.py` (new) — `extract_row_validation_policy` (pure, raises TypeError on malformed policy) + `annotate_row_quality` (native Spark `_quality_status`/`_quality_reason`; rows never dropped or cast; pyspark imported in-function so CI stays Spark-free).
- `notebooks/bronze/airbnb/ingest_airbnb_calendar.ipynb` + `ingest_airbnb_reviews.ipynb` (new, 18 cells each, listings-notebook flow): widget-driven explicit `source_file_id`; manifest resolve + hash/size + full-gzip + header-fingerprint + required-column gates; dataset-scoped rerun guard against the slice's `_source_file_id` (same → skip, different → blocked, `force_reload` authorizes); string-preserving read (header on, inferSchema off, multiLine + escaped quotes); quality annotation; 8 provenance columns; atomic `write_snapshot` slice replace; per-identity reconciliation.
- Tests +15 (row_quality incl. both real contracts; config-validation `row_validation` cases; environment key assertions). Suite **242 passed** (was 227).

Runtime evidence (test mode only — `bronze.airbnb_calendar_bronze_test` / `bronze.airbnb_reviews_bronze_test`; live calendar/reviews tables do NOT exist):

- Calendar: 8,048,251 raw = slice = identity rows (matches F06.1 exactly); 0 invalid; one run id `e07a5ef0daca4cafafa5cd309901a388`; schema = 5 source + `_quality_reason`/`_quality_status` + 8 provenance columns, ALL string; Delta version 0 (`WRITE`); `available` ∈ {t,f}; dates/night counts preserved as raw strings.
- Reviews: **729,202** raw rows — dual-parser verified (Spark multiLine+escape and Python `csv` both 729,202; all (listing_id,id) pairs unique; physical lines 743,664); 3,590 rows carry embedded newline/quote in `comments` and parse intact (spot-checked); 0 invalid; one run id `a204cdbf3dcb4cd6bc8f32c10de573c7`; all-string schema; Delta version 0.
- Guard drills (notebook-mirrored logic): exact same-file rerun → skip with NO new Delta version on either table; a different `source_file_id` for the same slice → blocked with an explicit error; `force_reload=true` → load authorized. `id`-alone non-uniqueness re-verified under the corrected count: 728,363 distinct ids vs 729,202 rows (839 extra).
- F05 production outputs unchanged after both runs: bronze 22,050 / control 1 / silver 22,050 / rejected 0 / quality 0.
- Local gate on the tested tree: `ruff check` only the EXE002 workspace artifact; `ruff format --check` clean (3 new files formatted); config validation pass (7 files); notebook validation pass; pytest **242 passed**.

## F06.3 — File-level quality and rerun validation (2026-11-18; complete on `feature/f06-3-run-controls`, tested commit `885d550b5700d46bed4c439b5d69bace3262ccee`; PR pending)

Scope (F06.3-T01/T02): independent per-file run outcomes, counts and errors for calendar and reviews; dataset-scoped decisions preserving same-file skip, new-snapshot isolation and explicit `force_reload` for corrected files; failure isolation between files. No Silver, no cross-file business reconciliation, no F07 (stopped after F06.3 per the handoff).

Design (approved by the operator before any schema/signature change): separate per-dataset control tables `bronze.airbnb_calendar_ingestion_control` / `bronze.airbnb_reviews_ingestion_control` (11 columns: 8 base + `source_file_id` + `prior_source_file_id` + `dataset`). The listings control table and its history stay untouched; every new row is tagged with its dataset. `decide_ingestion_action` gained an optional `dataset` parameter (default `"listings"`, backward compatible — the F05 notebook was not edited) whose scope rule reads untagged legacy rows as listings history only: they never leak into calendar/reviews decisions and tagged rows are invisible to the listings scope. No backfill of legacy rows.

Changes (tested commit `885d550`, 7 files):

- `src/common/run_controls.py` — `_in_dataset_scope` helper; `decide_ingestion_action(..., dataset="listings")`; `build_control_record(..., dataset=None)`; the blocked-corrected-file error now names the dataset.
- `src/common/environment.py` — LIVE_TABLES keys `calendar_control`/`reviews_control` (test mode → `*_test`).
- `notebooks/ops/setup_control_tables.py` — creates the two new control tables with the 11-column schema (the listings CREATE block is unchanged).
- `notebooks/bronze/airbnb/ingest_airbnb_calendar.ipynb` + `ingest_airbnb_reviews.ipynb` (21 cells each) — the F06.2 Bronze-slice guard replaced by the control-table flow: CREATE IF NOT EXISTS + dataset-scoped decision with skip assert; start-control row (run_id, prior identity, dataset tag); read and write wrapped in `record_control_failure`; success UPDATE with row_count before per-identity reconciliation.
- Tests +10 (same-dataset skip/blocked/force/new-snapshot; other-dataset rows ignored; legacy untagged rows = listings scope; tagged rows invisible to listings; `build_control_record` dataset tag; environment key assertions). Suite **251 passed** (was 242).

Runtime evidence (test mode only — new `bronze.airbnb_*_ingestion_control_test` tables; the live calendar/reviews control tables do NOT exist):

- Calendar E2E: empty control → load; run `c4d5785325f347b39ee1d0124792ccee`; 8,048,251 raw = slice = control row_count (matches F06.1/F06.2); 0 invalid; success, `dataset='calendar'`, prior NULL; control Delta v2 / `airbnb_calendar_bronze_test` v1.
- Reviews E2E: run `6cabd21a9b32400d8d31a669e2e28775`; 729,202 raw = slice = control row_count; 0 invalid; success, `dataset='reviews'`; control v2 / `airbnb_reviews_bronze_test` v1.
- Decision drills: same-file retry → skip (no new control row, no Bronze write, bronze version unchanged); corrected file (the other dataset's source_file_id) → blocked naming `calendar|reviews/toronto/2026-09-16`; `force_reload` → load; new snapshot date → load for both; cross-dataset isolation both directions (a calendar success row never affects a reviews decision and vice versa); legacy NULL-dataset rows in the listings `_test` control behave exactly as F05 under the default scope (same-file skip, different blocked, force load) and are invisible to the reviews scope.
- Failure isolation (real read failures through the notebook code path, both directions): a nonexistent landing path raised PATH_NOT_FOUND and was recorded via `record_control_failure`; both control tables hold success+failed rows with the error message and row_count 0; each dataset's success row stayed intact (8,048,251 / 729,202); failed rows never block retries (same-file still skips); control Delta versions 4/4.
- Reconciliation: control row_count == Bronze slice count == expected for both files; slice `source_file_id` == control `source_file_id`; exactly one run id per slice == the control run_id; prior_source_file_id NULL on first loads.
- F05 production unchanged (read-only checks): live control 1 success row / 22,050, still Delta v2 (last op 2026-11-01); live listings bronze 22,050 (v4); live silver 22,050 (v3); none of the new live tables exist. The F05 listings notebook and its control history were not touched.
- Local gate on the tested tree: `ruff check` only the EXE002 workspace artifact; `ruff format --check` clean; config validation pass (7 files); notebook validation pass; pytest **251 passed**.

## Standing conventions and gotchas

- pytest on serverless: `PYTHONDONTWRITEBYTECODE=1` + subprocess `python -m pytest tests` from the repo root (assertion rewrite cannot create `__pycache__` on the workspace filesystem).
- Fresh serverless sessions start without ruff (`pip install -r requirements.txt` after restarts); `importlib.reload` `src.*` modules after editing repo files mid-session.
- `ruff check` locally shows only the EXE002 artifact (the workspace FS marks files executable; git records 100644 — CI unaffected).
- gitleaks scans every commit in the PR range: fixing current code is not enough while the flagged commit is still in the range; one surgical `.gitleaksignore` fingerprint exists for `f1880ba` (tests/common/test_source_acquisition.py). Never author token-shaped literals, even synthetic ones.
- Auto Mode blocks f-string SQL writes and external binary downloads: use the Delta DataFrame API for control-row writes and hard-assert `_test` table names in drill helpers.
- `createAsset` with `.ipynb` in the name double-appends the extension — rename after create.
- Batched `editAsset` updates on Git-folder notebooks can partially fail with a transient "Cell not found" (and one reported-apply can miss the file); after any batched notebook edit, verify the changed cells in the `.ipynb` on disk before continuing, and re-read the notebook for fresh cell ids before the next edit.
- Evidence convention (F03.3): every subfeature records status/scope/branch/PR/tested SHA/merge SHA/CI checks, with runtime verification kept separate from local tests; never infer a pass from a green workflow alone.

## Remaining gaps / blockers

- **F05.1 licence verification (open; gates ALL production manifest registration):** the operator must confirm the current official Inside Airbnb licence and attribution (insideairbnb.com/get-the-data) before any live manifest row is written — listings, calendar and reviews alike. Manifest identity/metadata is immutable once written, so placeholder values must never enter the live table. The landed objects are content-addressed and already in place, so live registration completes idempotently the moment the values are confirmed.
- Notion child pages: PR URL, tested SHA, merge SHA and Actions run URL to be pasted by the operator after each merge (this file carries the SHAs). The live `ops.source_file_manifest` table is created by the first real acquisition run, never by tests.
- Test fixtures under `source_files/_test_fixtures/f05-3` and drill rows in the `_test` manifest/control tables are runtime evidence and may be cleaned up after review. The F06.2/F06.3 `_test` Bronze tables (`airbnb_calendar_bronze_test` 8,048,251 rows / `airbnb_reviews_bronze_test` 729,202 rows) and the F06.3 `_test` control tables (`airbnb_calendar_ingestion_control_test`, `airbnb_reviews_ingestion_control_test` — each one success + one failed drill row) are runtime evidence and may be dropped after review.

## Next task

Open/merge the F06.3 PR (`feature/f06-3-run-controls`, tested commit `885d550`), update the Notion handoff page with the evidence above, then start **F07** per the roadmap (not started — F06.3 stopped after T01–T02 as instructed). Live-mode runs for calendar/reviews stay withheld until the licence confirmation.
