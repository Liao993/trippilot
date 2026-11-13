# TripPilot progress

## Current roadmap position (v29 Build Guide)

**F04.1 — Source manifest and provenance contract. Status: Complete on `feature/f04-1-source-manifest`; PR pending (see F04.1 evidence below).**

The F03 foundation is fully closed: PR #11 (`c909a4f`), PR #12 (`2a4c24f`), PR #13 (`a041d01`) and PR #14 (`58b4da7`) are merged, and F03.3 (merge protection and delivery readiness) merged as PR #15 → `a924126`.

Note: the CI workflow's push trigger covers `main` and `feature/add-ci` only, so CI for this branch runs via the pull-request check or a manual `workflow_dispatch` from the Actions tab.

## Actual working environment and source paths (verified 2026-11-12)

- Databricks catalog: `trippilot_dev` — schemas `bronze`, `silver`, `gold`, `ops` all present
- Source Volume: managed Volume `trippilot_dev.bronze.source_files` at `/Volumes/trippilot_dev/bronze/source_files`
- Source file: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz` — exists, 13,117,826 bytes
- Current city: Toronto; snapshot date `2026-09-16`
- Databricks compute: serverless, Python 3.12.3 (meets the 3.11+ requirement for `datetime.UTC`), Spark 4.3.0.dev0

## Repository state (verified 2026-11-13, start of F04.1)

- Repository: `Liao993/trippilot` (public), Git folder branch `feature/f04-1-source-manifest` (based on `main` at `a924126`, merge of PR #15 / F03.3), clean tree
- `main` confirmed on origin at `a924126`; F03.3 closed the F03 foundation (branch protection on `main` configured by the maintainer per the delivered T01 steps; PR #15 merged with both checks green)
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

## F03.2 implementation and evidence (2026-11-13, complete; merged as PR #14 → `58b4da7`, Actions run #43355393517, both jobs green)

Scope per the v28 runbook (F03.2-T01 to T03): contract-driven fixture tests, static notebook/source validation, and dependency/secret scanning — no CI system change beyond extending `lint-test.yml`, no Databricks runtime work.

- T01 (contract-driven tests): populated the empty `tests/quality/test_exclusion.py` placeholder with 13 fixture tests (inline-dict convention) driving `record_validation.validate_listing` / `exclusion.get_exclusion_reason` against the real Silver contract rules — boundary values (price 0, latitude ±90, longitude ±180), missing required fields, unparseable price, out-of-range coordinates, disallowed `city`/`currency`, joined multi-error reasons, and the `validate_listing` return shape. New `tests/airbnb/test_ingestion.py` adds 11 service-contract tests for `ingestion.write_snapshot` using a recording `DataFrameWriter` stub: happy path (delta format, overwrite mode, `replaceWhere` predicate, `saveAsTable` last), unsafe city (uppercase, SQL-injection string), non-ISO date, 2-/4-part and unsafe-identifier table names, unsafe column names, and the hyphenated-city boundary that must stay allowed.
- T02 (notebook/source validation): new `src/quality/notebook_validation.py` validates `.ipynb` JSON structure (nbformat >= 4, non-empty cells, valid cell types, string-or-list sources) and `ast.parse`s every non-magic code cell (cells starting with `%`/`!` are skipped); plain `.py` files under `notebooks/` are syntax-checked. Errors name the file and cell. CLI: `python -m src.quality.notebook_validation`. `tests/quality/test_notebook_validation.py` adds 12 tests (valid/invalid notebooks and `.py` via `tmp_path`, magic-cell skip, negative JSON, plus one run over the real repo).
  - Real catch: on its first run over the repository the validator found `notebooks/ops/investigate_silver_quality.ipynb` cell 0 beginning with a stray backtick before a `#` comment (invalid Python). The notebook was fixed (single character removed); the test was not weakened.
- T03 (dependency + secret scans): new `requirements.txt` declares the CI tools (`ruff`, `pytest`, `pyyaml`); the workflow install step now uses `pip install -r requirements.txt` and a new step runs `pip-audit --requirement requirements.txt`. A new `secret-scan` job uses `gitleaks/gitleaks-action@v3` (current major; v2's Node 20 runtime is being removed from runners) with a full-history checkout (`fetch-depth: 0`); no `GITLEAKS_LICENSE` needed (personal-account repo per the action README).
  - pip-audit finding reviewed and resolved: the preinstalled pytest 8.4.2 is affected by `PYSEC-2026-1845` (fixed in 9.0.3). The suite passes under pytest 9.0.3 and 9.2.0 (88 passed each), so `requirements.txt` pins `pytest>=9.0.3` with the advisory documented in a comment. No suppressions used.
  - Local Gitleaks evidence: gitleaks 8.30.1 CLI scanned all 24 commits (~261 KB), no leaks, exit 0 (run redacted).
  - Local pip-audit note: full `-r` mode needs a virtualenv, which the Databricks serverless sandbox cannot create (no `ensurepip`); the scan was verified locally with the three tools pinned at installed versions in `--no-deps --disable-pip` mode (clean after the pytest floor), and the authoritative run executes on the GitHub runner via the PR check.
- Workflow: all F03.1 checks preserved; new steps in order — notebook validation after YAML validation, pip-audit before pytest; second job `secret-scan`. `actions/checkout@v6` is used in the new job per the gitleaks-action v3 migration notes; the proven-green lint job keeps its existing checkout version.
- Local verification, in CI order: `ruff check src tests` exit 0; `ruff format --check src tests` exit 0 (28 files formatted); `python -m src.quality.config_validation` exit 0; `python -m src.quality.notebook_validation` exit 0 ("All notebook and source files under notebooks/ are valid."); pip-audit (pinned local mode) clean; gitleaks clean; `python -m pytest tests` 88 passed (was 53; +35).
- Negative-path evidence: with a broken notebook in a temp root, `python -m src.quality.notebook_validation` exits 1 naming file, cell and syntax error.

## CI evidence convention (added in F03.3; template for every future subfeature)

Every completed subfeature records, in `docs/progress.md` and the matching Notion child page:

- Status: In progress / Blocked / Verified / Merged
- Scope; Branch; PR; Tested commit SHA; Merge commit SHA; GitHub Actions run
- Required CI checks — Ruff lint / Ruff format / YAML validation / Notebook-source validation / pip-audit / Gitleaks / pytest — each recorded as pass, fail or not run; never assumed from a green workflow alone
- Databricks/runtime verification kept separate: a green GitHub workflow does not prove that a notebook, job, table write or deployed application works in the workspace
- Skipped checks, accepted exceptions and blockers stated explicitly; links to the PR and Actions run; the exact tested commit SHA
- Summary first, detail only where it helps reproduce or audit the result

## F03.3 implementation and evidence (2026-11-13, complete)

Scope per the v28 runbook (F03.3-T01 to T03): require CI before merge, standardize the evidence record, and make an evidence-based Databricks deployment go/no-go decision. Documentation and settings only — no workflow, pipeline, table or credential changes.

- T01 (merge protection): the required check names were verified from the workflow file and the successful run on the merge commit: `Lint and unit tests` and `Secret scan (Gitleaks)` (Actions run #43355393517, both green on `58b4da7`). The repository is public, so branch protection/rulesets are available on the free plan. The rule itself is configured in GitHub Settings by the maintainer (browser-only); exact steps were delivered with this PR. Verification: this F03.3 PR doubles as the test PR — it contains no risky changes, and its merge box must show both required checks gating the merge.
- T02 (evidence convention): F03.2 record reconciled (PR #14, merge `58b4da7`, run #43355393517, both jobs green — header and roadmap position above); reusable evidence template added as the section above this one.
- T03 (deployment readiness): decision — **Deferred, prerequisites unavailable**. Evidence (inspected 2026-11-13): (1) the workspace has no service principals (SCIM list returns 0), so no non-interactive M2M authentication exists for GitHub Actions and no GitHub secret holds a Databricks credential; (2) the repository contains no Databricks bundle or deployment definition (`git ls-files` shows none); (3) no separate non-production deployment target exists — the only workspace is the development workspace where the Git folder already syncs the code. Nothing was deployed, no workflow YAML was added, and no credentials were created or committed. Reopen when: a service principal with an OAuth secret stored in GitHub Actions secrets, a defined non-production deployment target, and a minimal validated bundle (dry run) are available.
- Regression confirmation (no Python changed): `ruff check src tests` exit 0; `ruff format --check src tests` exit 0; `python -m src.quality.config_validation` exit 0; `python -m src.quality.notebook_validation` exit 0; `python -m pytest tests` 88 passed.
- Merged after both required checks were green: PR #15 → merge `a924126` (tested commit `6177650`). The branch-protection rule on `main` was configured by the maintainer per the delivered T01 steps.

## F04.1 implementation and evidence (2026-11-13, complete; PR pending)

Scope per the v29 runbook (F04.1-T01/T02): a metadata/contract subfeature — manifest contract, pure-Python validation and state rules. No downloads, no Bronze writes, no changes to the existing Airbnb raw path. Status: Verified locally.

- T01 (manifest contract): new `contracts/ops/source_file_manifest.yml` (the first populated ops contract) defines all 17 manifest fields with types and nullability, the four controlled states (registered/validated/landed/failed), valid transitions (registered→validated→landed; failed and landed terminal), seven supported file types and the 2-GiB size limit. Deterministic identity: `source_file_id` = SHA-256 over `source_family|source_entity_id|source_version|file_type|file_hash_sha256`, so an exact same-file retry is idempotent while a corrected hash creates a new immutable record.
- T02 (validation): new `src/common/source_manifest.py` (pure Python — no Spark, Volume or network): file checks (exists, regular, non-empty, size limit, supported type), streamed SHA-256 of the exact bytes, metadata validation (required fields incl. license/attribution/source identity, ISO-8601 UTC timestamp, hash format, https source_url, /Volumes/ landing path), state-transition rules returning immutable record copies, and sanitized failure messages (credential patterns redacted). Run IDs reuse `src.common.provenance.build_run_id` — no competing helper.
- CI integration: `src/quality/config_validation.py` validates the manifest contract as a fifth populated file (states, transitions, file types, max size, required + optional fields); the two tmp-path config tests were extended accordingly.
- Tests: `tests/common/test_source_manifest.py` — 26 tests (valid record, hash stability and change, deterministic ID, missing/dir/empty/oversized/unsupported files, missing license/attribution/entity, invalid timestamp/hash/URL, full transition chain, rejected skip and terminal transitions, failed requires + sanitizes the message, landing-path rules, new record must start registered, YAML↔module consistency). `tests/quality/test_config_validation.py` — 8 new positive/negative contract tests.
- Local verification, in CI order: `ruff check src tests` exit 0; `ruff format --check src tests` exit 0 (30 files); `python -m src.quality.config_validation` exit 0 (five files); `python -m src.quality.notebook_validation` exit 0; `python -m pytest tests` 124 passed (was 88; +36). No Spark, network, production table or credential used.
- Defect caught during verification: the first draft rejected every valid record with "Missing required manifest field: byte_size" (required-field loop treated the integer field as a string); fixed by special-casing byte_size. Three Ruff findings (redundant Z replacement, join vs f-string, ValueError vs TypeError) also corrected.
- Databricks/runtime verification: none for this subfeature (metadata only, by design).

## Remaining gaps / blockers

- `notebooks/ops/verify_setup.ipynb` contains a Delta `overwrite` to `trippilot_dev.ops.setup_verification`; review that cell and its target before any run.
- F04.1 PR/merge evidence (PR URL, tested SHA, merge SHA, Actions run URL) to be recorded after merge, here and in the Notion page.
- Local workspace cleanup pending confirmation: `.pytest_cache/`, `.ruff_cache/` (gitignored caches) and the stray tracked `src/common/__init__` (superseded by `src/common/__init__.py`).

## Next task

Open the pull request for `feature/f04-1-source-manifest` → `main`, confirm both required checks are green on the PR commit, merge, record the PR URL, tested SHA, merge SHA and Actions run here and in the Notion page, then switch the Git folder back to `main` and pull. Next per the v29 roadmap: F04.2 — Raw acquisition, validation and immutable landing.
