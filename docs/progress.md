# TripPilot progress

## Current roadmap position (v28 Build Guide)

**F02.2 — Isolated migration execution and recovery tests. Status: In progress.**

F02.1 fixes are pushed (commit `f6d1420`: CI `run:` repair, Silver test alignment, this progress file). F02.2 implementation is complete and unit-tested; runtime test-mode execution is the remaining work.

Note: the CI workflow's push trigger covers `main` and `feature/add-ci` only, so CI for this branch runs via the pull-request check or a manual `workflow_dispatch` from the Actions tab.

## Actual working environment and source paths (verified 2026-11-12)

- Databricks catalog: `trippilot_dev` — schemas `bronze`, `silver`, `gold`, `ops` all present
- Source Volume: managed Volume `trippilot_dev.bronze.source_files` at `/Volumes/trippilot_dev/bronze/source_files`
- Source file: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz` — exists, 13,117,826 bytes
- Current city: Toronto; snapshot date `2026-09-16`
- Databricks compute: serverless, Python 3.12.3 (meets the 3.11+ requirement for `datetime.UTC`), Spark 4.3.0.dev0

## Repository state (verified 2026-11-12)

- Repository: `Liao993/trippilot`, Git folder branch `chore/feature-1-foundation-migration`
- Local HEAD `e64a9ae3cdef6e5881c58359dcedfa35ea232e3b`, equal to `origin/chore/feature-1-foundation-migration` as of the last fetch
- Layout reconciles with v28: `src/airbnb`, `src/common`, `src/quality`, `src/contracts`; `tests/airbnb`, `tests/common`, `tests/quality`; `config/project.yml`, `config/city_registry.yml`; `contracts/airbnb/bronze_listings.yml`, `contracts/airbnb/silver_listings.yml`; notebooks under `notebooks/bronze|silver|gold|ops`

## Verified F02.1 evidence (2026-11-12)

- CI workflow `.github/workflows/lint-test.yml`: the duplicated `run: run:` in the dependency-install step was corrected to a single `run:` key (pending commit).
- Unit tests: 21 passed, 0 failed, 0 skipped, pytest exit code 0, executed on Databricks serverless compute against the Git folder working tree.
- Test alignment: `tests/common/test_silver_contract.py` still imported the pre-rename `get_rejection_reason`; updated to `get_exclusion_reason` (current API in `src/airbnb/transformations.py`). The accepted-listing fixture now uses the post-`clean_price` decimal value `150.0` because `contracts/airbnb/silver_listings.yml` declares `price` as `type: decimal`. Assertions unchanged.
- YAML validation: `config/project.yml`, `config/city_registry.yml`, `contracts/airbnb/bronze_listings.yml`, `contracts/airbnb/silver_listings.yml` all load via `yaml.safe_load`.
- Tables inspected read-only (no writes): `bronze.airbnb_listings_bronze` 22,050 rows; `bronze.airbnb_ingestion_control` 1 row; `silver.airbnb_listings_silver` 22,050 rows; `silver.airbnb_listings_rejected` 0 rows; `ops.quality_results` 0 rows. Additional tables present: `bronze.airbnb_listings_bronze_test`, `ops.setup_verification`.
- No Bronze/Silver write or destructive cell was executed during preflight.

## F02.2 implementation (2026-11-12, unit-tested; runtime pending)

- `src/common/environment.py`: the single source of truth for run-mode isolation. `run_mode` is `test` (default) or `live`; test mode resolves every logical table (`bronze`, `bronze_control`, `silver`, `silver_rejected`, `quality_results`, `exclusion`) to an isolated `*_test` Delta table, so a test run can never write a development table. `force_reload` defaults to false; `decide_should_run` combines it with the existing skip rule.
- `tests/common/test_environment.py`: 13 unit tests covering mode validation, per-mode table resolution, isolation invariants, force-reload coercion, and run-control decisions.
- The Bronze and Silver notebooks define `run_mode` / `force_reload` widgets (defaults `test` / `false`) and resolve all table names through `src.common.environment`. Bronze creates the isolated control table on its first test run, guards the slice DELETE with `tableExists`, and its summary cell no longer hardcodes the development table. Silver writes only the resolved `*_test` tables in test mode.
- Lint: `ruff check src tests` passes (import-order fixes applied across 7 files). `EXE002` appears only on the workspace filesystem copy; git records every file as mode 100644 (`core.fileMode=false`), so CI is unaffected.
- Unit tests: 34 passed, 0 failed, 0 skipped (pytest, Databricks serverless, Python 3.12.3).
- Runtime test-mode execution (Bronze run, skip rerun, force reload, failure recovery, Silver run, synthetic invalid input) and F02.3 reconciliation are pending.

## Remaining gaps / blockers

- Runtime test-mode execution (Bronze/Silver writes to the isolated `*_test` tables only) is implemented and unit-tested but not yet executed; awaiting run confirmation.
- `notebooks/ops/verify_setup.ipynb` contains a Delta `overwrite` to `trippilot_dev.ops.setup_verification`; review that cell and its target before any run.
- GitHub Actions verification for the F02.2 commit still pending (PR check or manual `workflow_dispatch`).
- Local workspace cleanup pending confirmation: `.pytest_cache/`, `.ruff_cache/` (gitignored caches) and the stray `src/common/__init__` (superseded by `src/common/__init__.py`).

## Next task

Execute the F02.2 runtime sequence in test mode (Bronze run, skip-rerun check, force reload, failure recovery, Silver run, synthetic invalid-input test), capture F02.3 reconciliation evidence, update this file, then open the PR.
