# TripPilot progress

## Current roadmap position (v28 Build Guide)

**F03.1 — CI baseline and developer checks. Status: Complete on `feature/f03-1-ci-baseline`; PR pending (see F03.1 evidence below).**

F02 is fully closed: PR #11 (F02 runtime work, merge `c909a4f`) and PR #12 (v28 docs alignment, merge `2a4c24f`) are both merged into `main`; the user confirmed the main-branch CI run passed on `2a4c24f`.

Note: the CI workflow's push trigger covers `main` and `feature/add-ci` only, so CI for this branch runs via the pull-request check or a manual `workflow_dispatch` from the Actions tab.

## Actual working environment and source paths (verified 2026-11-12)

- Databricks catalog: `trippilot_dev` — schemas `bronze`, `silver`, `gold`, `ops` all present
- Source Volume: managed Volume `trippilot_dev.bronze.source_files` at `/Volumes/trippilot_dev/bronze/source_files`
- Source file: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz` — exists, 13,117,826 bytes
- Current city: Toronto; snapshot date `2026-09-16`
- Databricks compute: serverless, Python 3.12.3 (meets the 3.11+ requirement for `datetime.UTC`), Spark 4.3.0.dev0

## Repository state (verified 2026-11-13, start of F03.1)

- Repository: `Liao993/trippilot`, Git folder branch `feature/f03-1-ci-baseline` (based on `main` at `2a4c24f`, merge of PR #12), clean tree
- `main` confirmed on origin at `2a4c24f` after PR #11 (`c909a4f`, F02 runtime work) and PR #12 (v28 docs alignment, commit `f1bc087`)
- Layout reconciles with v28: `src/airbnb`, `src/common`, `src/quality`, `src/contracts`; `tests/airbnb`, `tests/common`, `tests/quality`; `config/project.yml`, `config/city_registry.yml`; `contracts/airbnb/bronze_listings.yml`, `contracts/airbnb/silver_listings.yml`; notebooks under `notebooks/bronze|silver|gold|ops`

## Verified F02.1 evidence (2026-11-12)

- CI workflow `.github/workflows/lint-test.yml`: the duplicated `run: run:` in the dependency-install step was corrected to a single `run:` key (pending commit).
- Unit tests: 21 passed, 0 failed, 0 skipped, pytest exit code 0, executed on Databricks serverless compute against the Git folder working tree.
- Test alignment: `tests/common/test_silver_contract.py` still imported the pre-rename `get_rejection_reason`; updated to `get_exclusion_reason` (current API in `src/airbnb/transformations.py`). The accepted-listing fixture now uses the post-`clean_price` decimal value `150.0` because `contracts/airbnb/silver_listings.yml` declares `price` as `type: decimal`. Assertions unchanged.
- YAML validation: `config/project.yml`, `config/city_registry.yml`, `contracts/airbnb/bronze_listings.yml`, `contracts/airbnb/silver_listings.yml` all load via `yaml.safe_load`.
- Tables inspected read-only (no writes): `bronze.airbnb_listings_bronze` 22,050 rows; `bronze.airbnb_ingestion_control` 1 row; `silver.airbnb_listings_silver` 22,050 rows; `silver.airbnb_listings_rejected` 0 rows; `ops.quality_results` 0 rows. Additional tables present: `bronze.airbnb_listings_bronze_test`, `ops.setup_verification`.
- No Bronze/Silver write or destructive cell was executed during preflight.

## F02.2 implementation (2026-11-12, complete)

- `src/common/environment.py`: the single source of truth for run-mode isolation. `run_mode` is `test` (default) or `live`; test mode resolves every logical table (`bronze`, `bronze_control`, `silver`, `silver_rejected`, `quality_results`, `exclusion`) to an isolated `*_test` Delta table, so a test run can never write a development table. `force_reload` defaults to false; `decide_should_run` combines it with the existing skip rule.
- `tests/common/test_environment.py`: 13 unit tests covering mode validation, per-mode table resolution, isolation invariants, force-reload coercion, and run-control decisions.
- The Bronze and Silver notebooks define `run_mode` / `force_reload` widgets (defaults `test` / `false`) and resolve all table names through `src.common.environment`. Bronze creates the isolated control table on its first test run, guards the slice DELETE with `tableExists`, and its summary cell no longer hardcodes the development table. Silver writes only the resolved `*_test` tables in test mode.
- Lint: `ruff check src tests` passes (import-order fixes applied across 7 files). `EXE002` appears only on the workspace filesystem copy; git records every file as mode 100644 (`core.fileMode=false`), so CI is unaffected.
- Unit tests: 34 passed, 0 failed, 0 skipped (pytest, Databricks serverless, Python 3.12.3).
- Runtime test-mode execution and F02.3 reconciliation completed 2026-11-12 — evidence below.

## F02.2/F02.3 runtime evidence (2026-11-12; all writes to isolated *_test tables only)

All notebook runs executed the committed code (branch `chore/feature-1-foundation-migration`, commit `7ff44b8`) via `dbutils.notebook.run` with `run_mode=test`. No development table was written in any run.

- Source file: 13,117,826 bytes, SHA-256 `e84fe1a5ff1735d5676fe0da211cc12bab2ab9050c3ddc64a4b8a939d5b11d19`. Raw source rows (excluding header): 22,050.
- Bronze test run 1 (run_id `5cacee53…`, force_reload=false): created `bronze.airbnb_ingestion_control_test`; replaced the toronto/2026-09-16 slice in `bronze.airbnb_listings_bronze_test` — 22,050 rows, single run_id, Delta version 2 (DELETE + APPEND); control status `success`; runtime ≈ 26.6 s (19:21:59.358 → 19:22:25.927 UTC). Dev bronze (22,050 rows) and dev control (1 row) unchanged.
- Skip-rerun check (rerun after a success, force_reload=false): run aborted with the expected skip assertion; table state unchanged (22,050 rows, version 2, 1 control row).
- Force reload (force_reload=true): replaced the slice again — 22,050 rows, single new run_id `e3359322…`, Delta version 4, no duplicated logical records.
- Failure-recovery drill: while a `success` record remained for toronto/2026-09-16, a no-force rerun was correctly skipped (skip rule fires on any success). After flipping all control rows for that city/snapshot to `failed`, a no-force rerun proceeded, replaced the slice (Delta version 6) and recorded a new `success` (run_id `3f0637d1…`) — recovery verified.
- Silver test run 1: created `silver.airbnb_listings_silver_test` (22,050 rows) and `silver.airbnb_listings_rejected_test` (0 rows). Silver rerun is idempotent (overwrite; counts stable, version 1). Dev silver (22,050) and dev rejected (0) unchanged.
- Synthetic invalid-input test: 3-row synthetic slice (`_snapshot_date=1900-01-01`) appended to bronze_test and validated with the pipeline's own rules (`contracts/airbnb/silver_listings.yml`, table `silver_listings`): empty `id` → rejected (`Missing required field: id`); non-null unparseable price (`not-a-price`) → rejected (`Invalid numeric value for price`); a valid row → accepted. Raw bronze-shaped rows lacking `city`/`snapshot_date` were also rejected with recorded reasons. The synthetic slice was deleted afterward — bronze_test restored to 22,050 rows (version 8), silver_test untouched.
- Reconciliation (F02.3): raw 22,050 = bronze_test 22,050 = silver_test 22,050 + rejected_test 0 + duplicates 0. Test vs dev: silver `listing_id` sets identical (22,050 distinct each, 0 differences); bronze/silver/rejected row counts identical to dev.

## F03.1 implementation and evidence (2026-11-13, complete)

Scope per the v28 runbook: extend the existing CI workflow only — no new CI system, no Databricks deployment, no pipeline or table changes.

- T01 (inspect and preserve): `.github/workflows/lint-test.yml` reviewed in full — triggers are pull request → `main`, push → `main`/`feature/add-ci`, and manual `workflow_dispatch`; it sets up Python 3.11, installs Ruff/pytest/PyYAML, then runs `ruff check src tests` and `python -m pytest tests -v`. The user confirmed the main-branch CI run passed on `2a4c24f`. Nothing was deleted or recreated; Python stays 3.11 (the code targets ≥3.11 and the green run confirms compatibility).
- T02 (Ruff format check): no `pyproject.toml` or Ruff config exists anywhere in the repo, so none was created. `ruff format --check src tests` initially flagged 15 files (all of `src` plus 9 test files); `ruff format src tests` reformatted exactly those 15 (110 insertions, 88 deletions — quote normalization and expression joins only, per `git diff --stat`); all 34 tests still passed afterward. The workflow now runs `ruff format --check src tests` after lint. No new dependency file was needed.
- T03 (YAML validation): new `src/quality/config_validation.py` reuses `contract_loader.load_contract` / `get_table_rules` (no second loader, no duplicate of the Spark-based row validator) and adds structure checks for exactly the four populated files: `config/project.yml` (sections `project`/`databricks`/`sources`; keys `project.name`, `databricks.catalog`, `databricks.schemas`), `config/city_registry.yml` (`cities` list; per-entry `city` + `enabled`), `contracts/airbnb/bronze_listings.yml` (table, source, non-empty `required_columns`), `contracts/airbnb/silver_listings.yml` (table, `business_key`, `required_columns`, non-empty `rules` mapping with per-column mappings). Empty placeholder YAML files are deliberately excluded. Errors name the file and the missing/invalid key; the check needs only Python + PyYAML — no Spark, Databricks, production tables, or credentials. CI step: `python -m src.quality.config_validation`, between the format check and pytest per the runbook's required order.
- Unit tests: `tests/quality/test_config_validation.py` adds 19 tests (synthetic fixtures, error-message checks naming file + key, invalid-YAML and missing-file paths via `tmp_path`, plus one run against the four real repo files). Suite total: 53 passed, 0 failed (was 34).
- Local verification, in CI order: `ruff check src tests` exit 0; `ruff format --check src tests` exit 0 (25 files formatted); `python -m src.quality.config_validation` exit 0 ("All populated YAML configuration and contract files are valid."); `python -m pytest tests` 53 passed.
- Negative-path evidence: with `silver_listings.rules` emptied, the validator exits 1 with `contracts/airbnb/silver_listings.yml: 'silver_listings.rules' must be a non-empty mapping`; the real file was then restored and revalidated clean.

## Remaining gaps / blockers

- `notebooks/ops/verify_setup.ipynb` contains a Delta `overwrite` to `trippilot_dev.ops.setup_verification`; review that cell and its target before any run.
- CI green on `main` was confirmed by the user for `2a4c24f` (runbook F03.1-T01). The four-check CI run on this branch's pull request still needs confirmation in the browser.
- Local workspace cleanup pending confirmation: `.pytest_cache/`, `.ruff_cache/` (gitignored caches) and the stray tracked `src/common/__init__` (superseded by `src/common/__init__.py`).

## Next task

Open the pull request for `feature/f03-1-ci-baseline` → `main`, confirm the Checks tab shows all four checks (lint, format, YAML validation, tests) green on the PR commit, merge, then continue with the next F03 subfeature per the v28 roadmap.
