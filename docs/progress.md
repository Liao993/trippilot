# TripPilot progress

## Current roadmap position (v28 Build Guide)

**F02.1 — Migration preflight and workspace validation. Status: In progress.**

Remaining for the F02.1 exit gate: commit and push the CI workflow fix and the test alignment fix, then confirm GitHub Actions passes lint and tests for the exact pushed commit (the workflow's push trigger covers `main` and `feature/add-ci` only, so a run on this branch needs a manual `workflow_dispatch` from the Actions tab or the pull-request check).

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

## Remaining gaps / blockers

- `notebooks/ops/verify_setup.ipynb` contains a Delta `overwrite` to `trippilot_dev.ops.setup_verification`; review that cell and its target before any run.
- GitHub Actions not yet re-verified for the pending CI fix commit (needs commit + push, then a green run for the exact commit).
- Run IDs, Delta versions and source hash capture are F02.2/F02.3 evidence items, not yet collected.

## Next task

Commit and push the pending changes (CI workflow fix, test alignment) from the Databricks Git panel; confirm the GitHub Actions run for the exact commit; then complete the F02.1 exit-gate review before starting F02.2.
