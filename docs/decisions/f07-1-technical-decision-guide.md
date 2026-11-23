# TripPilot — F07.1 Technical Decision & AI Agent Handoff Guide

**Version:** 1.0 · **Date:** 2026-11-23 · **Prepared from:** direct inspection of GitHub `Liao993/trippilot` @ main `1d21909`, live manifest `trippilot_dev.ops.source_file_manifest`, the source Volume, and the four uploaded files themselves.

> Evidence labels: **[V]** = verified fact (observed this session) · **[D]** = existing project decision · **[R]** = new recommendation · **[A]** = assumption requiring verification · **[⏳]** = approval required · **[U]** = unknown / open item.

---

## 1. Executive Summary

F07.1 (Summary Source Registration and Bronze) starts from a strong position. The entire registration machinery it needs — deterministic source identity, immutable hash-versioned landing, manifest-driven acquisition, idempotent retries, failure recording — already exists and is verified (F04/F05/F06). The four target files are already in the workspace (operator-uploaded into the landed folder), and F07.1-T01 inspection evidence is complete (§3.2).

Three real gaps, all small:

1. **Acquisition supports only `csv.gz`** (`ACQUISITION_FILE_TYPES` in `src/common/source_acquisition.py`); the four files are plain `csv` and `geojson` — types the manifest contract already accepts, so only the acquisition validation layer needs extending.
2. **`src/airbnb/source_inspection.py` is gzip-CSV-specific**; plain-CSV and GeoJSON inspection helpers are needed to produce schema fingerprints for registration.
3. **The four uploads sit in the landed folder outside the approved `_staging` roots**, unregistered — they must be moved to `_staging` and registered through the standard flow.

One scope ambiguity needs operator approval: the subfeature title says "…and Bronze" but the task register's F07.1 tasks (T01/T02) cover inspection + registration only, while F07.2-T01 explicitly owns "Parse summary files into distinct Bronze sources." Recommended: registration-only for F07.1, matching the F06.1→F06.2 precedent.

Estimated implementation: ~3 file modifications + 2 test-suite extensions + 1 config edit + 1 minor notebook edit; no new notebooks, tables, or contracts.

---

## 2. Project Context and Target Scope

**Feature F07** — Airbnb summary and neighbourhood ingestion/Bronze. **Goal:** land the summary and geographical reference files without conflating them with detailed facts.

**Target subfeature F07.1 — Summary source registration and Bronze**

- `F07.1-T01` — Inspect `listings.csv`, `reviews.csv`, `neighbourhoods.csv`, `neighbourhoods.geojson` for the selected source snapshot. *(Evidence complete — §3.2.)*
- `F07.1-T02` — Register each file separately and preserve its schema/version.

**Scope boundary (per Build Guide v31 task register):** F07.2-T01 (parse summary files into distinct Bronze sources), F07.2-T02/T03 (neighbourhood CSV/GeoJSON Bronze), F07.3 (geometry/availability/replacement validation), F08–F10 are out of scope. The only permitted dependency repair is extending acquisition to `csv`/`geojson` and inspection utilities — both required to enable T02.

**Governing references (all verified present on main):** `docs/trippilot-project-plan-v31.md`, `docs/trippilot-unified-build-guide-v31.md`, `docs/progress.md` (next task: F07), repository @ `1d21909`.

---

## 3. Existing Implementation Assessment

### 3.1 Project state [V]

| Aspect | State |
|---|---|
| Git | `main` @ `1d21909`; PRs #29 (pre-F07 cleanup), #30 (control rename), #31 (`_incoming`→`_staging`) all merged 2026-11-19. Stale branch `feature/add-ci` (2026-11-01) — irrelevant. |
| Local Git folder | On main, clean, synced with origin (verified 2026-11-23). |
| Environment | Catalog `trippilot_dev`; schemas bronze/silver/gold/ops; serverless; source Volume `/Volumes/trippilot_dev/bronze/source_files`. |
| Live manifest | `ops.source_file_manifest` — 3 records, all `csv.gz`, `insideairbnb/toronto/2026-09-16`, CC BY 4.0, `landed` (listings `26de1c3c…`, calendar `09a7ef20…`, reviews `7c5ada51…`). |
| Volume end state | Landed dir `…/toronto/2026-09-16/` holds the 3 managed hash-named objects **plus 4 unmanaged raw uploads** (the F07.1 files, not registered); `_staging` empty. |
| Tests/CI | 286 pytest green at last gate; CI = ruff check/format, `config_validation`, `notebook_validation`, pip-audit, pytest, gitleaks. |

### 3.2 Source assessment — F07.1-T01 evidence [V, recorded 2026-11-23]

All four files were uploaded by the operator to `…/toronto/2026-09-16/` and fully inspected by streaming read:

| File | Bytes | SHA-256 | Structure | Grain / key |
|---|---:|---|---|---|
| `listings.csv` | 4,193,812 | `63717f6a22814b64690c4c145165b8d52aa3040b4afc4f4ae17d93704064a4b6` | 19 cols: `id, name, host_id, host_profile_id, host_name, neighbourhood_group, neighbourhood, latitude, longitude, room_type, price, minimum_nights, number_of_reviews, last_review, reviews_per_month, calculated_host_listings_count, availability_365, number_of_reviews_ltm, license` | 1 row per listing; `id` unique (0 duplicates over 22,050 rows) |
| `reviews.csv` | 18,233,434 | `7e9064b26455231fcaebb85d54b769a18e6d4966ada6460e283069bd03ff1db2` | 2 cols: `listing_id, date` | 1 row per review event; `listing_id`+`date` **NOT unique** (1,021 same-day duplicate pairs) — never enforce uniqueness on this pair |
| `neighbourhoods.csv` | 2,638 | `96cd1ba4b804209ec5d6e4306dc3a12c218f449f8b64c3593ae6e752b5b53a2d` | 2 cols: `neighbourhood_group, neighbourhood` | 140 unique names; `neighbourhood_group` blank in every row (Toronto characteristic) |
| `neighbourhoods.geojson` | 1,017,142 | `e4db99db3fa54e741fc15f482df2f634a7919e00d6c1607d5744059ea139d029` | GeoJSON `FeatureCollection`, 140 features, properties `{neighbourhood, neighbourhood_group}`, all `MultiPolygon`, no feature ids | 1 feature per neighbourhood; names match the CSV's 140 exactly |

Data characteristics [V]: summary `listings.csv` has blank `price` in 5,290 rows (24%), blank `license` in 10,222 + `Exempt` 103; all `reviews.csv` dates are well-formed `YYYY-MM-DD`; summary listings reference exactly the 140 official neighbourhood names. **Reconciliation signals:** summary listings rows (22,050) == detailed listings rows; summary reviews rows (729,202) == detailed reviews rows — same observation sets, different schema/grain.

Derived schema fingerprints (convention `<label>-sha256:<header-hash-16>`) [V]:

| File | schema_version |
|---|---|
| `listings.csv` | `summary-listings-sha256:6d5eeaa74190cf08` |
| `reviews.csv` | `summary-reviews-sha256:9f1260580cdd24d2` |
| `neighbourhoods.csv` | `neighbourhoods-sha256:d2259d198ebd6435` |
| `neighbourhoods.geojson` | `neighbourhood-geojson-sha256:90f71a0951417639` (fingerprint over canonicalized properties+geometry signature; the new inspection helper must define the canonicalization deterministically) |

Availability: **all four files present** — no partial-availability case at registration time (tests must still cover missing/invalid scenarios).

### 3.3 Key existing components [V]

- `src/common/source_manifest.py` — identity (`source_file_id` = SHA-256 over `family|entity|version|file_type|content-hash`), 15 required fields + `landing_path`/`error_message`, states `registered→validated→landed` / `failed` (terminal). `SUPPORTED_FILE_TYPES` **already includes `csv` and `geojson`**.
- `src/common/source_acquisition.py` — `acquire_source_file`: staging-root guard (`_ensure_within`), signature check (`FILE_SIGNATURES = {"csv.gz": gzip}` — the gap), hash-versioned immutable landing (`build_landing_path` → `<base>__<hash12>.<type>`), manifest-driven idempotency (same bytes → verify existing landed record; corrected bytes → new record), failure recording, optional post-landing staging cleanup, `verify_landed_record`, `reprocess_source_file`.
- `src/common/source_manifest_store.py` — Delta MERGE manifest persistence (operational-field updates only).
- `src/airbnb/source_inspection.py` — `inspect_csv_gz_header(path, schema_label)` producing header fingerprint + `schema_version`; `verify_gzip_integrity`; `check_required_columns`. **Gzip-only.**
- `src/airbnb/bronze_flow.py` — shared `BronzeDatasetSpec` + `run_bronze_ingestion` (gzip-CSV specific; resolves by explicit `source_file_id` because identity alone is ambiguous; per-dataset control tables; raw-string preservation; atomic `replaceWhere` write; reconciliation). **Not needed by F07.1; F07.2 will extend it.**
- `notebooks/ops/acquire_source_file.ipynb` — the single registration surface: widgets (`source_path`, `source_family`, `source_entity_id`, `source_version`, `file_type` (default `csv.gz`), `source_url`, `schema_version`, `license`, `attribution`, `retrieved_at_utc`, `run_mode` acquire/verify_existing/reprocess/inspect, `environment` test/live, `manifest_table` override, `cleanup_staged` default true).
- `config/project.yml` — dataset registry for toronto (listings/calendar/reviews with `file` + `required_identifier`). `config_validation` only checks `sources` is a non-empty mapping — new dataset entries pass unchanged.
- `src/common/environment.py` — resolver; `source_manifest` key exists; **no new keys needed for F07.1**.

---

## 4. Implementation Gap Analysis

| Component | Status | Note |
|---|---|---|
| Manifest identity/state contract | **Implemented and verified** | csv + geojson already supported; reuse unchanged |
| Immutable landing + idempotency + failure recording | **Implemented and verified** | for `csv.gz`; must be extended to `csv`/`geojson` |
| Acquisition file-type validation | **Partially implemented** | `ACQUISITION_FILE_TYPES = ("csv.gz",)` rejects all four F07.1 files |
| Source inspection (plain CSV) | **Missing** | `inspect_csv_gz_header` pattern exists; plain-CSV variant needed |
| Source inspection (GeoJSON) | **Missing** | needs FeatureCollection validation, feature count, property schema, fingerprint |
| Dataset registry entries for the 4 files | **Missing** | `config/project.yml` lists only detailed datasets |
| Registration of the 4 files (test + live) | **Missing** | the actual T02 work |
| Bronze ingestion of summary/neighbourhood files | **Not applicable (F07.2)** | intentionally deferred |
| Bronze contracts for the 4 files | **Not applicable (F07.2)** | no F07.1 task requires contracts; schema preservation is via manifest `schema_version` |

Documentation/implementation discrepancies: (a) F07.1 subfeature title "…and Bronze" vs task register T01/T02 (registration only); F07.2-T01 owns summary Bronze parsing. (b) The four uploads bypassed `_staging` — a process deviation to remediate, not a code defect. (c) `docs/progress.md` §5 outstanding items (licence verification, exploration stubs) predate F07.1 and remain open.

Reuse as-is: manifest module/store, environment resolver, table setup, acquire notebook structure, acquisition test patterns, CI gates. Do **not** create a new acquisition notebook, a new manifest table, or a parallel registration path.

---

## 5. Technical Decision Guide

**D1 — F07.1 scope: registration-only** · [⏳ approval required]
Task register gives F07.1 only T01 (inspect) + T02 (register); F07.2-T01 explicitly owns summary Bronze parsing. Option (b) (build summary Bronze tables in F07.1) contradicts the task register, inflates scope/risk, and front-loads F07.2 contract decisions; option (a) (registration only) matches the F06.1→F06.2 precedent exactly. The "Bronze" in the title is satisfied by Bronze-layer source landing (immutable objects under the bronze schema's source Volume) + manifest registration. **Recommendation: (a).**

**D2 — Reuse the existing registration framework** · [D]
Register all four files via `acquire_source_file` through `notebooks/ops/acquire_source_file.ipynb` — no new mechanism. Identity stays `source_family=insideairbnb`, `source_entity_id=toronto`, `source_version=2026-09-16`, with `file_type` `csv`/`geojson` distinguishing them from the detailed `csv.gz` records. Deterministic IDs differ by file type + content hash — no collision with the 3 existing records [V].

**D3 — Extend acquisition to `csv` + `geojson`** · [R, in-scope enabler]
Per-type content validators in `source_acquisition.py`: `csv` — reject gzip magic (catches mislabeled uploads) + require a non-empty first header line; `geojson` — full JSON parse + `type == "FeatureCollection"`. Keeps the module pure-filesystem, preserves the existing `csv.gz` path byte-for-byte, and matches the code's own stated intent ("Other manifest-supported types can be added once their validation behaviour is tested"). 1 MB GeoJSON parse is cheap; streaming noted for future large files (F17).

**D4 — Plain-CSV + GeoJSON inspection helpers** · [R; label naming ⏳ approval required — immutable records]
Extend `src/airbnb/source_inspection.py`: `inspect_csv_header(path, schema_label)` (same fingerprint/`schema_version` derivation as the gzip variant — refactor the shared derivation, don't duplicate) and `inspect_geojson(path, schema_label)` (FeatureCollection check, feature count, distinct property keys, geometry types, canonical fingerprint). **Recommended labels:** `summary-listings`, `summary-reviews`, `neighbourhoods`, `neighbourhood-geojson` (values in §3.2). Labels are baked into immutable manifest `schema_version` values — the F06.1 label-drift defect is the precedent for fixing this once, up front.

**D5 — Staging remediation of the four uploads** · [R; ⏳ approval required — moves operator-uploaded files]
Move the files from the landed folder into `_staging/insideairbnb/toronto/`, then run the standard flow (lands hash-named copies + manifest records; end state: managed objects only, no strays). Widening `approved_staging_roots` to include the landed dir is rejected (weakens the immutability design); re-uploading from outside is wasteful. A content-preserving move (hash before/after), reversible. Expected landing names: `listings__63717f6a2281.csv`, `reviews__7e9064b26455.csv`, `neighbourhoods__96cd1ba4b804.csv`, `neighbourhoods__e4db99db3fa5.geojson` — no collision with existing objects.

**D6 — Data separation** · [D, extends a verified F06.1 finding]
Separation is enforced at the manifest layer: distinct `file_type`, content hashes, `source_file_id`s, schema labels. With **seven** records sharing the identity `insideairbnb/toronto/2026-09-16`, any resolution must be by explicit `source_file_id` (already the verified Bronze pattern). No F07.1 code may resolve a source by identity alone; no Bronze tables are created; no summary row can be unioned with detailed facts in this subfeature.

**D7 — `config/project.yml` dataset registry** · [R]
Add four toronto dataset entries (`summary_listings`, `summary_reviews`, `neighbourhoods`, `neighbourhood_geometry`) with `file` + `required_identifier` (`id`, `listing_id`, `neighbourhood`, `neighbourhood`). Verified: `config_validation` accepts arbitrary dataset keys, so no validator change is needed.

**D8 — Bronze contracts deferred to F07.2** · [R]
No F07.1 task requires contracts; `required_columns`/`row_validation` are ingestion-time decisions owned by F07.2. Schema preservation for F07.1 is via manifest `schema_version` (the established F06.1 pattern).

**D9 — Execution flow: test mode → gates → live** · [R, per Unified Build Guide v31]
Landing is mode-independent (shared Volume); only the manifest table differs. Acquire all four in **test** mode (`environment=test` → `ops.source_file_manifest_test`, `cleanup_staged=false` so staged copies survive for the live run), verify states/idempotency/isolation; after gates pass, re-run in **live** mode (`cleanup_staged=true` — resolves the existing landed objects, writes the canonical manifest records, cleans staging). This is the verified F06/T11 live-registration pattern.

**D10 — Licence and source URL** · [⏳ operator input required]
Carry licence `CC BY 4.0 (Creative Commons Attribution 4.0 International)` + attribution `Inside Airbnb (insideairbnb.com), CC BY 4.0` — identical to the 3 registered records. (1) The outstanding `docs/progress.md` §5 licence verification against the official Inside Airbnb data policy applies to these registrations too — confirm before live promotion (records are immutable). (2) Supply the exact per-file `source_url` (the Toronto 2026-09-16 snapshot page/data URLs) — never fabricate a URL; minimum bar is the get-the-data page used by the existing records. `retrieved_at_utc` should be the actual download time.

**D11 — No new tables, notebooks, resolver keys, or pipelines in F07.1** · [R/D]
Registration status *is* the manifest `processing_state`; per-dataset ingestion-control tables belong to Bronze ingestion (F07.2). Keeps the diff minimal; avoids duplicate utilities.

---

## 6. Implementation Decision Matrix

| Area | Required decision | Recommended approach | Reason (evidence) | Approval? |
|---|---|---|---|---|
| Source registration | Mechanism for the 4 files | Reuse `acquire_source_file` + acquire notebook | Verified F04/F06 pattern; manifest already supports csv/geojson | No |
| File identity | Distinguish 4 files + 3 detailed at same identity | Deterministic `source_file_id`; explicit-ID resolution everywhere | file_type+hash differentiates; identity-alone ambiguity verified in F06.1 | No |
| Schema/version | Preserve each file's schema | `schema_version` = `<label>-sha256:<fingerprint16>` via new inspection helpers | Existing convention; fingerprints computed (§3.2) | Labels — **yes** |
| Bronze processing | Where files enter Bronze layer | Land immutably into bronze-schema source Volume via standard flow; no Bronze tables | F07.2-T01 owns parsing; F04.2 landing verified | Scope — **yes** (D1) |
| Data separation | Summary vs detailed vs review facts | Manifest-level separation: types, hashes, IDs, labels; no unions | Project Plan §4.1 rule; F06 precedent | No |
| Provenance | Source URL, retrieval, licence, attribution | Full manifest fields per file, same as detailed records | Contract requires all fields; CC BY 4.0 precedent | URL + licence — **yes** |
| Idempotency | Repeated registration | Inherited: same bytes → existing landed record; corrected bytes → new record | Verified `acquire_source_file` semantics + tests | No |
| Reprocessing | Re-run without reacquisition | `reprocess_source_file` (identity+hash) resolves landing path | Verified F04.3 capability | No |
| Error handling | One file's failure ≠ subfeature success | Independent per-file records; failures stored sanitized (`registered→failed`); tests prove isolation | Verified manifest state machine + F06.3 isolation drills | No |
| Data quality | T01-level observations recorded | Blank price 5,290 / non-unique (listing_id,date) / blank groups documented; no enforcement now | Inspection evidence §3.2; enforcement is F07.2/F10 | No |
| Testing | Unit + fixture + test-mode drills | Extend `test_source_acquisition.py`, `test_source_inspection.py`; test-mode registration + idempotency/isolation drills | Existing suite patterns (286 green) | No |
| Databricks execution | Test vs live | Test-mode manifest first, live after gates; serverless; Git folder on main | Build Guide v31 lifecycle; verified resolver isolation | No |
| Storage/table organization | Where artifacts live | Landed Volume objects + manifest rows only; no new UC tables | No Bronze ingestion in this subfeature | No |

---

## 7. Repository Change Plan

| File path | Classification | Current responsibility | Proposed changes | Dependencies | Tests |
|---|---|---|---|---|---|
| `src/common/source_acquisition.py` | MODIFY | Staging validation, immutable hash-versioned landing, manifest-driven registration (csv.gz only) | Add `csv` + `geojson` per-type content validators; extend `ACQUISITION_FILE_TYPES`; keep the `csv.gz` path behaviour unchanged | None — enables everything else | `tests/common/test_source_acquisition.py` |
| `src/airbnb/source_inspection.py` | MODIFY | Gzip-CSV header inspection, schema fingerprints (F05.1/F06.1) | Add `inspect_csv_header(path, schema_label)` and `inspect_geojson(path, schema_label)`; refactor the shared fingerprint/`schema_version` derivation to avoid duplication; gzip helpers untouched | None | `tests/airbnb/test_source_inspection.py` |
| `notebooks/ops/acquire_source_file.ipynb` | MODIFY (minor) | Single registration surface for all source files | `file_type` widget: text → dropdown `[csv.gz, csv, geojson]` (default `csv.gz`); extend overview markdown to mention summary/neighbourhood files; no structural/flow change | `source_acquisition.py` changes | `notebook_validation` (CI) + manual test/live runs |
| `config/project.yml` | MODIFY | Dataset registry for toronto (listings/calendar/reviews) | Add `summary_listings`, `summary_reviews`, `neighbourhoods`, `neighbourhood_geometry` entries (`file` + `required_identifier`) | None (verified `config_validation` passes new keys) | `config_validation` (CI) |
| `tests/common/test_source_acquisition.py` | MODIFY | Acquisition unit tests (csv.gz fixtures) | csv/geojson happy paths; mislabeled-gzip-as-csv rejected; invalid/non-FeatureCollection geojson rejected; idempotent same-bytes retry; corrected-file new object; staging-root guard still enforced | `source_acquisition.py` | Itself |
| `tests/airbnb/test_source_inspection.py` | MODIFY | Gzip header inspection tests | Plain-CSV header + fingerprint tests; GeoJSON structure/fingerprint tests (synthetic fixtures, tmp-path pattern) | `source_inspection.py` | Itself |
| `docs/progress.md` | MODIFY (close-out only) | Evidence ledger | F07.1 section with verified results, evidence links, next-task pointer | All above | Review step |
| `src/common/source_manifest.py` | REUSE | Identity/state/metadata contract | None — csv/geojson already supported | — | Existing tests unchanged |
| `src/common/source_manifest_store.py` | REUSE | Delta MERGE manifest persistence | None | — | Existing |
| `src/common/environment.py` | REUSE | Table/run-mode resolver | None — `source_manifest` key exists; no new keys | — | Existing |
| `src/common/table_setup.py` | REUSE | Idempotent operational tables | None — no new tables | — | Existing |
| `src/airbnb/bronze_flow.py` | REUSE (untouched) | Shared Bronze ingestion flow | None in F07.1 (F07.2 extends for non-gzip sources) | — | Existing |
| `contracts/ops/source_file_manifest.yml` | REUSE | Manifest contract | None — csv/geojson already listed | — | Existing |
| `contracts/airbnb/*.yml` | REUSE (untouched) | Bronze/Silver contracts for existing datasets | None in F07.1 (F07.2 adds summary/neighbourhood contracts) | — | Existing |

No CREATE (no new modules/notebooks/contracts/tables), no RETIRE within F07.1. Separately outstanding, outside F07.1: `feature/add-ci` branch retirement, `notebooks/exploration/` stubs — both need operator decision; do not touch them in this subfeature.

Independence/order: the two src modules and their tests are independent of each other; the notebook edit depends on D3; the config edit is independent; registration runs depend on all code changes plus the staging move.

---

## 8. Implementation Sequence

1. **Pre-flight (inspect only):** Git folder on `main`, clean tree, synced `1d21909`; re-verify the four uploads' hashes/sizes against §3.2; re-read `docs/progress.md`.
2. **Code + tests:** `source_acquisition.py` (D3), `source_inspection.py` (D4), both test suites → full local gates: `pytest`, `ruff format --check`, `ruff check`, `python -m src.quality.config_validation`, `python -m src.quality.notebook_validation`.
3. **Config + notebook:** `project.yml` entries (D7), `file_type` dropdown (D4) → re-run gates.
4. **Staging remediation (D5, after operator go-ahead):** move the four raw uploads to `_staging/insideairbnb/toronto/`; hash-verify before/after.
5. **Test-mode registration:** acquire each file with `environment=test`, `cleanup_staged=false`; capture per-file `source_file_id`, state, landing path; rerun each once to prove idempotency (zero new objects); run the failure/isolation drills (invalid geojson fixture in the test manifest).
6. **Promotion gates** (§10) → **live registration:** `environment=live`, `cleanup_staged=true`, per file with its verified `schema_version` and confirmed licence/source URL.
7. **Reconcile + close out:** live manifest = 7 records, all `landed`, hashes verified; landed dir = 7 managed objects only; `_staging` empty; review diff; update `docs/progress.md`; PR; Notion F07.1 child page.

---

## 9. Implementation and Validation Checklist

**F07.1-T01 — Source inspection (complete; re-verify at execution)**

- [x] Inspect all four source files — streaming inspection of the actual uploads; schemas §3.2 ✅ done 2026-11-23
- [x] Record actual schemas (19 cols / 2 cols / 2 cols / FeatureCollection 140 features)
- [x] Identify identifiers and grain (`id` unique; review-event rows with non-unique `listing_id+date`; 140 neighbourhood names)
- [x] Identify version/snapshot info (all `2026-09-16`, matching the detailed registrations)
- [x] Assess availability independently (all four present)
- [x] Record schema differences (summary vs detailed; blank `price`/`neighbourhood_group`; licence blanks; 1,021 duplicate date pairs)
- [x] Identify file-specific ingestion considerations (geojson full-parse validation; mislabeled-gzip rejection; no uniqueness enforcement)

**F07.1-T02 — Independent source registration**

- [ ] Move four uploads to `_staging/insideairbnb/toronto/` — *expected: files under approved staging root, hashes unchanged; validation: hash before/after*
- [ ] Extend acquisition to `csv`/`geojson` with tests — *expected: pytest green incl. new cases; mislabeled/invalid rejected*
- [ ] Add plain-CSV + GeoJSON inspection helpers with tests — *expected: derived `schema_version` equals §3.2 values on the real files*
- [ ] Add four `project.yml` dataset entries — *expected: config_validation rc=0*
- [ ] Register each file separately in **test** mode — *expected: 4 new `landed` records in `ops.source_file_manifest_test`, distinct `source_file_id`s, per-file states visible*
- [ ] Verify rerun behaviour — *expected: same-bytes rerun resolves existing record, no new object, no duplicate row*
- [ ] Verify duplicate-registration behaviour — *expected: identical registration parameters resolve to the same `source_file_id`; a changed file would be a new record (fixture test)*
- [ ] Verify partial-availability behaviour — *expected: a missing/invalid file records `failed` (or operator-visible error) without affecting the other three; fixture drill in test mode*
- [ ] Confirm licence + source URL; pass promotion gates; register in **live** mode — *expected: `ops.source_file_manifest` = 7 records, all `landed`*
- [ ] Verify summary/detailed separation — *expected: no new Bronze tables; the 4 records distinguishable from the 3 detailed records by `file_type`/`schema_version`/`source_file_id`; nothing unions summary with detailed rows*

---

## 10. Acceptance Criteria and Evidence Matrix

| Criterion | Implementation | Validation | Expected result | Evidence | Status |
|---|---|---|---|---|---|
| Source independence | 4 separate `acquire_source_file` runs; independent manifest records | Manifest query grouped by `source_file_id` | 4 distinct IDs, each independently `landed`/`failed` | Manifest rows + run prints | Pending |
| Schema/version preservation | `schema_version` from inspected fingerprints (§3.2) | Derived-at-registration fingerprint vs stored value | Equality for all 4; no `pending` values | Manifest `schema_version` + inspection output | Pending |
| Data separation | Manifest-level separation; no Bronze tables; explicit-ID resolution | Table inventory + manifest inspection | No new bronze/silver tables; 7 records distinguishable; summary never registered as detailed | UC table list + manifest rows | Pending |
| Partial availability | Per-file states; failure recording (`registered→failed`) | Fixture drills (missing, invalid geojson, mislabeled gzip) | Failures isolated, visible, sanitized; no silent skips | Test-mode drill outputs | Pending |
| Idempotency | Existing semantics + new-type tests | Same-bytes rerun ×4; duplicate registration | Same record re-verified; zero new objects/rows | Rerun outputs + landing-dir listing | Pending |
| Reconciliation | File-level counts traceable | Manifest byte_size/hash vs landed objects | All 7 landed objects hash+size verified; volume end-state clean (7 managed objects, empty `_staging`) | `verify_landed_record` outputs | Pending |
| Regression | Existing detailed-file functionality untouched | Full pytest suite; skip-drill for calendar/reviews unchanged | 286+ new tests green; existing live tables/records unchanged | CI run + manifest/table diff | Pending |
| (T01) Source inspection | Completed 2026-11-23 | Session streaming inspection | Schemas/grains/keys recorded (§3.2) | This guide | **Done** |

**Promotion gates (live registration):** source identity ✓ (deterministic IDs) · source rights/attribution (**licence confirmation outstanding — D10**) · schema compatibility (fingerprint equality) · data quality (T01 observations recorded, no enforcement claims) · reconciliation · idempotency (rerun drills) · permissions (existing serverless grants) · correct destination (resolver-verified `environment=live`) · environment safety (test-mode run precedes live) · feature acceptance (above). Any gate failure → stop, do not write the live manifest, report evidence + recovery plan.

---

## 11. Risks, Dependencies and Approval Items

**Approval required from the operator (before/at implementation):**

1. **D1 scope:** F07.1 = registration only; summary Bronze parsing stays in F07.2.
2. **D4 schema labels:** `summary-listings`, `summary-reviews`, `neighbourhoods`, `neighbourhood-geojson` — baked into immutable manifest records.
3. **D5 staging move:** relocating the four uploads from the landed dir into `_staging` (content-preserving, hash-verified).
4. **D10 licence:** confirm CC BY 4.0/attribution against the current official Inside Airbnb data policy and supply the per-file official `source_url` values.

**Risks / dependencies:**

- **Immutability [V]:** manifest records and landed objects are never corrected in place — a wrong label/URL stays forever (remediation = documented new record). Mitigate by approving D4/D10 before live registration.
- **7 records share one identity:** any future code resolving by identity alone will be ambiguous. Mitigate: explicit `source_file_id` everywhere (already the verified pattern).
- **GeoJSON validation cost:** full JSON parse is fine at 1 MB; note streaming as a future consideration for larger files (F17).
- **Assumption requiring verification [A]:** the four uploads are assumed to be the operator's downloads of the official Toronto 2026-09-16 snapshot files (cannot be verified against the source from serverless — no outbound internet). The supplied `source_url` + `retrieved_at_utc` attest provenance.
- **Environment gotchas [V, prior sessions]:** run pytest on `/Workspace` with `PYTHONDONTWRITEBYTECODE=1` (FUSE Errno 95); `ruff` must be pip-installed in-session on serverless; `dbutils.fs.cp` to `file:/Workspace` does not reach local Python — use `/Volumes` paths.
- **Not blockers [U]:** stale `feature/add-ci` branch; `notebooks/exploration/` stubs (pre-existing decisions, out of F07.1 scope).

---

## 12. Copy-ready Genie Code Implementation Prompt

> **TripPilot — implement F07.1 (Summary Source Registration and Bronze)**
>
> **Project context.** TripPilot is an integrated travel lakehouse + grounded conversational AI on Databricks (catalog `trippilot_dev`, schemas bronze/silver/gold/ops, serverless). Repo: https://github.com/Liao993/trippilot (work in the Databricks Git folder copy of this repo). Governing docs: `docs/trippilot-project-plan-v31.md`, `docs/trippilot-unified-build-guide-v31.md`, `docs/progress.md`. Airbnb is the first vertical slice; F01–F06 and the pre-F07 cleanup are complete and verified (main @ `1d21909`).
>
> **Target: F07.1 — Summary source registration and Bronze.** Task IDs: `F07.1-T01` (inspect `listings.csv`, `reviews.csv`, `neighbourhoods.csv`, `neighbourhoods.geojson` for the selected snapshot) and `F07.1-T02` (register each file separately and preserve its schema/version). **Scope: registration only — do NOT build Bronze tables, Bronze ingestion, contracts, control tables, Silver, or neighbourhood processing (F07.2/F07.3/F08+).** The only permitted dependency repair: extend `src/common/source_acquisition.py` to acquire `csv` and `geojson` file types, and extend `src/airbnb/source_inspection.py` with plain-CSV and GeoJSON inspection helpers.
>
> **Verified decisions (already approved — follow, don't re-litigate).** Register all four files through the existing `acquire_source_file` flow via `notebooks/ops/acquire_source_file.ipynb`; identity `insideairbnb|toronto|2026-09-16` with `file_type` `csv`/`geojson`; deterministic `source_file_id`s; schema_version = `<label>-sha256:<fingerprint16>` with labels `summary-listings`, `summary-reviews`, `neighbourhoods`, `neighbourhood-geojson`; add the four datasets to `config/project.yml`; change the notebook's `file_type` widget to a dropdown `[csv.gz, csv, geojson]`; no new notebooks, tables, resolver keys, contracts, or pipelines.
>
> **Verified inspection evidence (F07.1-T01, recorded 2026-11-23 — re-verify at execution).** The four files are at `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/2026-09-16/` (uploaded there directly — they are NOT in `_staging` and NOT registered; move them to `_staging/insideairbnb/toronto/` before acquiring, hash-verifying before/after — this move is user-approved):
> - `listings.csv` — 4,193,812 B, sha256 `63717f6a22814b64690c4c145165b8d52aa3040b4afc4f4ae17d93704064a4b6`; 19 columns (`id, name, host_id, host_profile_id, host_name, neighbourhood_group, neighbourhood, latitude, longitude, room_type, price, minimum_nights, number_of_reviews, last_review, reviews_per_month, calculated_host_listings_count, availability_365, number_of_reviews_ltm, license`); 22,050 rows; `id` unique; `price` blank in 5,290 rows; `neighbourhood_group` blank everywhere; expected schema_version `summary-listings-sha256:6d5eeaa74190cf08`.
> - `reviews.csv` — 18,233,434 B, sha256 `7e9064b26455231fcaebb85d54b769a18e6d4966ada6460e283069bd03ff1db2`; columns `listing_id, date`; 729,202 rows; `(listing_id, date)` NOT unique (1,021 duplicates — grain is one row per review event; never enforce uniqueness); expected schema_version `summary-reviews-sha256:9f1260580cdd24d2`.
> - `neighbourhoods.csv` — 2,638 B, sha256 `96cd1ba4b804209ec5d6e4306dc3a12c218f449f8b64c3593ae6e752b5b53a2d`; columns `neighbourhood_group, neighbourhood`; 140 unique names; expected schema_version `neighbourhoods-sha256:d2259d198ebd6435`.
> - `neighbourhoods.geojson` — 1,017,142 B, sha256 `e4db99db3fa54e741fc15f482df2f634a7919e00d6c1607d5744059ea139d029`; FeatureCollection, 140 features, properties `{neighbourhood, neighbourhood_group}`, all MultiPolygon, no feature ids; 140 names match the CSV exactly; expected schema_version `neighbourhood-geojson-sha256:90f71a0951417639` (fingerprint over a deterministic, code-defined canonicalization of sorted property keys + geometry types).
>
> **Before modifying anything (Stage 1–2):** inspect the repository — branch `main` @ `1d21909`, clean tree; re-read `docs/progress.md`; read `src/common/source_acquisition.py`, `src/common/source_manifest.py`, `src/common/source_manifest_store.py`, `src/airbnb/source_inspection.py`, `notebooks/ops/acquire_source_file.ipynb`, `config/project.yml`, `contracts/ops/source_file_manifest.yml`, and the test suites `tests/common/test_source_acquisition.py`, `tests/common/test_source_reprocessing.py`, `tests/airbnb/test_source_inspection.py`. Re-verify the four uploads' sizes/hashes against the values above. Report any discrepancy between docs and code before proceeding. Do not invent schemas, function names, file paths, or test results; use actual repository names only.
>
> **Implementation (Stage 3–4), in order:** (1) `src/common/source_acquisition.py`: add `csv` and `geojson` acquisition support — per-type content validators (`csv`: reject gzip magic bytes, require a non-empty first header line; `geojson`: full JSON parse with `type == "FeatureCollection"`), extend `ACQUISITION_FILE_TYPES`; keep the existing `csv.gz` behaviour unchanged. (2) `src/airbnb/source_inspection.py`: add plain-CSV header inspection and GeoJSON inspection helpers reusing the existing fingerprint/`schema_version` derivation (refactor shared logic; do not duplicate it). (3) `config/project.yml`: add `summary_listings`, `summary_reviews`, `neighbourhoods`, `neighbourhood_geometry` datasets under toronto with `file` + `required_identifier` (`id`, `listing_id`, `neighbourhood`, `neighbourhood`). (4) `notebooks/ops/acquire_source_file.ipynb`: `file_type` widget → dropdown. (5) Extend both test suites: csv/geojson happy paths, mislabeled-gzip-as-csv rejection, invalid geojson rejection, idempotent same-bytes retry, corrected-file-becomes-new-record, staging-root guard, failure isolation (one bad registration never affects others). Make small, logically grouped changes; reuse existing patterns; do not create new utilities that duplicate existing ones.
>
> **Gates after code (Stage 5):** run `pytest` (on `/Workspace` set `PYTHONDONTWRITEBYTECODE=1`; pip-install `ruff` in-session), `ruff format --check src tests`, `ruff check src tests`, `python -m src.quality.config_validation`, `python -m src.quality.notebook_validation`. All must pass before any registration run. Then: move the four uploads into `_staging/insideairbnb/toronto/`; acquire each with `environment=test`, `cleanup_staged=false`, `schema_version` set from the inspection helper output (must equal the expected values above; a mismatch is a schema-drift stop); rerun each once to prove idempotency (zero new landed objects); run failure-isolation drills in the test manifest. Only unit tests + test-mode validation count as progress — never claim a test passed without executing it.
>
> **Live promotion (Stage 6) — automatic only if ALL gates pass:** licence/attribution (CC BY 4.0 + `Inside Airbnb (insideairbnb.com), CC BY 4.0` — the user must have confirmed this and supplied the per-file official `source_url` values; if not confirmed, STOP and ask), source identity, schema compatibility (fingerprint equality), reconciliation (landed hash+size == manifest), idempotency, permissions, destination safety (`environment=live` via the resolver), environment safety. Then acquire each file with `environment=live`, `cleanup_staged=true`. Expected end state: live `ops.source_file_manifest` has 7 records (3 detailed + 4 new), all `landed`; the landed dir holds 7 managed hash-named objects (new: `listings__63717f6a2281.csv`, `reviews__7e9064b26455.csv`, `neighbourhoods__96cd1ba4b804.csv`, `neighbourhoods__e4db99db3fa5.geojson`); `_staging` is empty. If any gate fails: stop, do not write live, report the failure evidence and a recovery plan.
>
> **Close-out (Stage 7):** review the diff for unrelated changes; verify no Bronze/Silver tables were created and existing tables/records are unchanged; update `docs/progress.md` only with verified evidence; note the Notion F07.1 child-page updates needed; report the commit. Do not start F07.2.
>
> **Report format:** completed work / verification evidence (commands + outputs) / test results (exact counts) / runtime evidence (manifest rows, landed objects, run ids) / discrepancies found / limitations / next steps.

---

## 13. Expected Completion Report Template

```
F07.1 — Summary Source Registration and Bronze — Completion Report
Date / Agent / Branch / Commit: …
Scope: F07.1-T01 (inspection) + F07.1-T02 (registration). Deviations: none / …
T01 evidence: four files inspected; schemas, grains, keys, hashes, counts recorded (…)
Code changes: source_acquisition.py (csv/geojson validators), source_inspection.py
  (plain-CSV + GeoJSON helpers), project.yml (4 datasets), acquire notebook
  (file_type dropdown); tests added: N new tests in <files>
Gates: pytest X passed (Y new); ruff format clean; ruff check (only pre-existing
  workspace EXE002, if any); config_validation rc=0; notebook_validation rc=0
Staging remediation: 4 uploads moved to _staging, hashes verified before/after
Test-mode registration: 4 records landed in ops.source_file_manifest_test
  (source_file_ids: …); idempotent rerun: zero new objects; failure drills: …
Live promotion: gates …; ops.source_file_manifest now 7 records, all landed;
  landed objects …; _staging empty; volume end-state clean
Separation check: no new bronze/silver tables; 7 manifest records distinguishable
Discrepancies found: …
Limitations: geojson full-parse validation; provenance attested by operator URL
Next steps: F07.2 (neighbourhood CSV/GeoJSON Bronze; summary Bronze parsing per
  F07.2-T01); outstanding licence-policy verification item if still open
Notion: F07.1 child-page updates required: …
```
