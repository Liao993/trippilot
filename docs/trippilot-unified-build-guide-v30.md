# TripPilot — Unified Build Guide

**Version:** 30.0  
**Revised:** November 14, 2026  
**Consolidates:** Build Guide v29, Notion Implementation Guide v29, Genie Code Execution Plan v29 and the useful navigation/workflow guidance from HOW_TO_USE v29  
**Architecture companion:** `trippilot-project-plan-v29.md`  
**Purpose:** One reusable, end-to-end manual for starting, restarting, implementing, testing, verifying and handing off any TripPilot feature or subfeature.

## Document role and source-of-truth rules

This is the single operational build guide for TripPilot. It combines the feature roadmap and task register with the human implementation workflow, Databricks browser instructions, Notion templates, Git/GitHub workflow and Genie Code execution protocol.

The existing Project Plan v29 remains the companion source for product vision, architecture decisions, data-source decisions, system boundaries and target repository structure. This guide retains the full F01–F31 roadmap, subfeature IDs, task IDs, dependencies and acceptance criteria from Build Guide v29.

Use this document whether you are:
- starting the project from an empty or newly cloned repository;
- restarting after a long break or switching computers;
- starting the next subfeature in the roadmap;
- continuing partially completed work;
- implementing manually with ChatGPT guidance;
- using Genie Code inside the Databricks browser UI; or
- debugging, reviewing, testing or closing a subfeature.

**Do not maintain separate implementation instructions in the old Notion Implementation Guide v29, Genie Code Execution Plan v29 or HOW_TO_USE v29.** Their useful procedures and navigation guidance are consolidated into this file. Notion remains an optional place to track feature pages and evidence, but the instructions themselves live here.

### Source-of-truth hierarchy

1. `trippilot-project-plan-v29.md` — product scope, architecture, source decisions and system guardrails.
2. This Unified Build Guide v30 — roadmap order, exact feature/subfeature/task IDs, acceptance criteria and implementation procedures.
3. `docs/progress.md` — actual implementation state and verified evidence.
4. Current repository files, tests, schemas, Git history and Databricks runtime metadata — evidence of current reality.
5. Notion parent/child pages — working notes, task execution details and evidence links; they must agree with the sources above.

If these sources conflict, do not silently overwrite one with another. Identify the conflict, explain its impact and ask for a decision. Actual code and runtime evidence determine what exists; documentation alone does not prove implementation.

## How to use this guide — quick start

You do **not** need a separate `HOW_TO_USE.md`. This section is the short navigation layer; the Operational Manual later in this document contains the detailed instructions, UI steps, templates and prompts.

Use only these three project references as your normal starting point:

1. **`trippilot-project-plan-v29.md`** — what TripPilot is, why it is being built, its architecture, source strategy, data layers, product boundaries and target repository structure.
2. **This Unified Build Guide v30** — what to build next, in what order, with which feature/subfeature/task IDs, how to implement it, and how to verify completion.
3. **`docs/progress.md`** — what has actually been implemented and verified in the repository.

Notion is an optional working and evidence-tracking layer. It can hold feature/subfeature notes, checklists, decisions and links, but it does not replace these three references or independently change the roadmap.

### The normal workflow

For every new subfeature:

1. **Find the next item.** Check the roadmap in this guide and compare it with `docs/progress.md`. Confirm the exact `Fxx.y` and task IDs.
2. **Inspect before changing anything.** Check the GitHub/Databricks Git folder branch, commit, working tree, existing files, tests and relevant Databricks workspace capabilities.
3. **Plan one subfeature.** Confirm scope, dependencies, input/output contracts, file plan, UI steps, tests, runtime checks and acceptance criteria.
4. **Choose how to implement.** Use ChatGPT step-by-step guidance if you want to learn and perform the work yourself, or Genie Code in the Databricks browser if you want workspace-assisted implementation.
5. **Verify and record.** Run tests, verify in the actual Databricks runtime where required, review the Git diff, synchronize to GitHub, and update `docs/progress.md` and Notion if used.
6. **Stop at the exit gate.** Do not automatically begin the next subfeature. Record the next eligible roadmap item.

The detailed sequence is in **Operational Manual → Standard implementation workflow for every subfeature**.

### Choose the right working mode

| What you want to do | Use this section |
|---|---|
| Start the project from scratch or restart after a long break | Operational Manual → Project start, restart and computer switching |
| Resume existing work or switch computers | Operational Manual → Resume existing work / Cross-computer handoff |
| Learn while implementing, with exact browser clicks and code | Operational Manual → Implementing with ChatGPT |
| Ask ChatGPT to inspect and plan a subfeature | Operational Manual → Standard prompts for working with ChatGPT |
| Ask Genie Code to inspect, implement and test in Databricks | Operational Manual → Genie Code workflow in Databricks browser |
| Debug a failure | Operational Manual → Troubleshooting procedure and debugging prompts |
| Review and close a subfeature | Operational Manual → Review, verification and close-out |

### Keep the development environment portable

- **Databricks browser UI** is a core development and execution environment for notebooks, PySpark, SQL, Delta and Unity Catalog.
- **Databricks Git folders** connect the browser workspace to the same GitHub repository.
- **GitHub** is the durable source-control anchor for code, branches, commits and pull requests.
- **Notion** is optional for human-readable task notes and evidence.
- **Local development tools** are optional and should use the same GitHub remote when needed.

Before switching computers, save work, run relevant checks, commit and push completed changes where safe, and record any uncommitted files. On the next computer, open the same Databricks workspace/Git folder, pull the intended branch, verify the commit and working-tree state, then read `docs/progress.md`. Never assume local files, Databricks workspace files, GitHub and Notion synchronize automatically.

### Status meanings

Use these status values consistently in `docs/progress.md` and Notion, if used:

- **Not started** — no implementation work has begun.
- **In progress** — implementation or verification is actively underway.
- **Blocked** — work cannot safely proceed because a dependency, permission, source, decision or capability is unavailable.
- **Verified** — the subfeature's required acceptance criteria and tests have passed, including Databricks runtime checks where required, with evidence recorded.
- **Merged** — the verified change has been merged into the agreed integration branch. This does not automatically mean the whole feature is released.
- **Deferred** — intentionally postponed with the reason and impact recorded.
- **Released** — included in the intended project release and its release evidence is recorded.

Do not mark a subfeature Verified because code exists or a notebook was created. Distinguish local tests, CI results and actual Databricks runtime evidence.

### Project restart rule

A restart means re-establishing a trustworthy working environment and determining the actual implementation state; it does **not** mean deleting or rebuilding verified work. Inspect the repository, Git history, tests, Databricks workspace and `docs/progress.md` first. Reuse verified work and resume from the next eligible subfeature.

# Roadmap and implementation register

The following roadmap and detailed task register are carried forward from Build Guide v29. The feature order, subfeature IDs, task IDs, dependencies and acceptance criteria are not being redesigned in this consolidation.


# Part A — Shared platform foundation

## F01 — Project architecture, configuration and source registries

**Goal:** establish common configuration and source metadata so each data family follows the same operating model.

### Subfeature breakdown

#### F01.1 — Repository baseline and architecture

**Task IDs:** `F01.1-T01`, `F01.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F01. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F01.2 — Environment, city and source configuration

**Task IDs:** `F01.2-T01`, `F01.2-T02`, `F01.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F01. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F01.3 — Shared contracts and engineering conventions

**Task IDs:** `F01.3-T01`, `F01.3-T02`, `F01.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F01. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F01.1-T01** — Review the current repository and migration state; preserve established paths unless a concrete defect requires a change.
- **F01.1-T02** — Document the target architecture, source boundaries, Bronze/Silver/Gold responsibilities and service/AI boundaries.
- **F01.2-T01** — Define environment-aware project configuration (local, Databricks development; later deployment targets only if available).
- **F01.2-T02** — Define the city registry with stable city ID, canonical name, country, timezone, currency, coordinates/boundary reference and source coverage.
- **F01.2-T03** — Define a source registry for Inside Airbnb, Overture, GTFS, weather and official documents.
- **F01.3-T01** — Define common run, source-file manifest, quality-result and coverage contracts.
- **F01.3-T02** — Define naming conventions, table grains, keys and schema-version conventions.
- **F01.3-T03** — Record architecture decisions and deferred choices; avoid over-designing later systems.

### Acceptance criteria
- Configuration loads and validates in a test.
- City and source registries have documented schemas and example records.
- Every source family can record version, licence, provenance and coverage.
- Existing repository/migration code is preserved or any necessary changes are explained.

## F02 — Databricks lakehouse foundation and current migration verification

**Goal:** complete the current notebook migration and establish a verified target workspace structure.

### Subfeature breakdown

#### F02.1 — Migration preflight and workspace validation

**Task IDs:** `F02.1-T01`, `F02.1-T02`, `F02.1-T03`

**Deliverable:** a reviewable implementation increment for this part of F02. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F02.2 — Isolated migration execution and recovery tests

**Task IDs:** `F02.2-T01`, `F02.2-T02`, `F02.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F02. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F02.3 — Reconciliation, evidence and migration sign-off

**Task IDs:** `F02.3-T01`, `F02.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F02. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F02.1-T01** — Verify branch, commit, migration package, notebook imports and target paths.
- **F02.1-T02** — Run linting and unit tests locally/CI before any live-table operation.
- **F02.1-T03** — Verify catalog, schema, Volume/storage paths, permissions and supported serverless runtime.
- **F02.2-T01** — Follow the existing migration runbook: preflight, isolated test writes, rerun/idempotency, forced reload, invalid input and failure/recovery tests.
- **F02.2-T02** — Compare test/live outputs and source checksums before enabling normal live writes.
- **F02.2-T03** — Record Delta table versions, run IDs, file hashes, accepted/excluded/duplicate counts and CI run URL.
- **F02.3-T01** — Confirm Bronze/Silver table naming and environment isolation rules.
- **F02.3-T02** — Update `docs/progress.md` with actual evidence; do not mark a migration verified from local tests alone.

### Acceptance criteria
- Migration acceptance checks pass in the actual Databricks workspace.
- Existing detailed-listing outputs are reconciled and their grain/keys are known.
- Test writes cannot unintentionally overwrite live tables.
- The verified revision and runtime evidence are recorded.

## F03 — CI/CD and automated quality foundation

**Goal:** establish repeatable pull-request validation now, then extend the same workflow to Databricks deployment later.

### Subfeature breakdown

#### F03.1 — CI baseline and developer checks

**Task IDs:** `F03.1-T01`, `F03.1-T02`, `F03.1-T03`

**Deliverable:** a reviewable implementation increment for this part of F03. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F03.2 — Contract, fixture and notebook validation

**Task IDs:** `F03.2-T01`, `F03.2-T02`, `F03.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F03. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F03.3 — Merge protection and delivery readiness

**Task IDs:** `F03.3-T01`, `F03.3-T02`, `F03.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F03. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F03.1-T01** — Review the existing `.github/workflows` and keep any working lint/test job.
- **F03.1-T02** — Configure Ruff lint/format checks and pytest.
- **F03.1-T03** — Add configuration and contract-schema validation.
- **F03.2-T01** — Add small fixture-based tests for parsing, key validation, transformations and service contracts.
- **F03.2-T02** — Add notebook/source validation appropriate to the repo; avoid tests that require production data in every PR.
- **F03.2-T03** — Add dependency and secret scanning that is practical for this repository.
- **F03.3-T01** — Require CI checks for merge where repository settings permit.
- **F03.3-T02** — Create a documented CI result/evidence convention.
- **F03.3-T03** — Add a deployment workflow only after authentication and workspace permissions are genuinely available; do not commit workspace tokens.

### Acceptance criteria
- Pull requests trigger repeatable lint, unit and configuration/contract checks.
- Test results are visible and a failing required check blocks the intended merge path.
- No secret or raw source file is needed for the standard CI suite.
- Manual Databricks runtime verification remains documented separately from local CI.

## F04 — Shared source acquisition, manifest and raw landing framework

**Goal:** make a reusable pattern for downloading/uploading, verifying and registering source files.

### Subfeature breakdown

#### F04.1 — Source manifest and provenance contract

**Task IDs:** `F04.1-T01`, `F04.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F04. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F04.2 — Raw acquisition, validation and immutable landing

**Task IDs:** `F04.2-T01`, `F04.2-T02`, `F04.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F04. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F04.3 — Run controls, reprocessing and failure tests

**Task IDs:** `F04.3-T01`, `F04.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F04. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F04.1-T01** — Define a source-file manifest with source family, city/agency/document ID, source version, file type, source URL, retrieval date, file hash, byte size, schema/version, licence/attribution and processing state.
- **F04.1-T02** — Implement common checksum, file-existence, size and file-type validation.
- **F04.2-T01** — Support local download and manual upload to a supported Volume path when Databricks outbound access is restricted.
- **F04.2-T02** — Keep raw files immutable by source version; define how re-downloads and replacements are represented.
- **F04.2-T03** — Implement safe run IDs and per-file status transitions.
- **F04.3-T01** — Keep acquisition separate from Bronze parsing so files can be reprocessed without downloading again.
- **F04.3-T02** — Add tests for missing file, empty file, hash mismatch, duplicate manifest entry and interrupted acquisition.

### Acceptance criteria
- A source file can be registered and verified without a data transformation.
- Re-running the manifest process does not create ambiguous duplicate versions.
- Raw source inputs can be reprocessed from the landing location.
- Licence/provenance metadata follows the file into downstream layers.

---

# Part B — Airbnb-first data platform

## F05 — Airbnb detailed listings ingestion and Bronze

**Goal:** reliably ingest the detailed listing snapshot, the primary accommodation source.

### Subfeature breakdown

#### F05.1 — Detailed listing source inspection and registration

**Task IDs:** `F05.1-T01`, `F05.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F05. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F05.2 — Bronze ingestion and metadata preservation

**Task IDs:** `F05.2-T01`, `F05.2-T02`, `F05.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F05. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F05.3 — Idempotency, schema drift and reprocessing

**Task IDs:** `F05.3-T01`, `F05.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F05. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F05.1-T01** — Inspect the exact current `listings.csv.gz` schema for the selected city/snapshot.
- **F05.1-T02** — Add the file to the common manifest and record its source snapshot date.
- **F05.2-T01** — Preserve the raw compressed file and create a source-faithful Bronze representation.
- **F05.2-T02** — Add ingestion metadata such as city ID, snapshot date, file hash, run ID and ingestion time.
- **F05.2-T03** — Detect missing/duplicate columns, malformed CSV, empty file and schema drift.
- **F05.3-T01** — Implement idempotent ingestion by source file/snapshot identity.
- **F05.3-T02** — Add a controlled reprocess path for a corrected/replaced source file.

### Acceptance criteria
- The selected detailed listing file is reproducibly loaded.
- Source row counts and Bronze counts are reconciled.
- The same file reruns safely; a new snapshot is retained separately.
- The raw source remains recoverable.

## F06 — Airbnb calendar and detailed review ingestion/Bronze

**Goal:** ingest the two listing-linked time-oriented datasets using reusable but source-specific parsing contracts.

### Subfeature breakdown

#### F06.1 — Calendar and review source contracts

**Task IDs:** `F06.1-T01`, `F06.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F06. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F06.2 — Separate Bronze ingestion paths

**Task IDs:** `F06.2-T01`, `F06.2-T02`, `F06.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F06. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F06.3 — File-level quality and rerun validation

**Task IDs:** `F06.3-T01`, `F06.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F06. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F06.1-T01** — Inspect `calendar.csv.gz` and `reviews.csv.gz` independently; record their actual columns and grains.
- **F06.1-T02** — Add calendar and review files to the shared manifest.
- **F06.2-T01** — Parse and preserve raw date, price, availability and review fields without silently coercing invalid values.
- **F06.2-T02** — Write separate Bronze products with city/snapshot/file/run metadata.
- **F06.2-T03** — Validate required IDs/date fields where present; retain invalid rows with exclusion/quarantine reasons.
- **F06.3-T01** — Record file-level counts and run outcomes separately because row volumes differ.
- **F06.3-T02** — Test same-file rerun, new-snapshot ingestion and partial failure isolation.

### Acceptance criteria
- Calendar and review records are separate Bronze assets with documented grains.
- IDs and date fields are preserved in source form before Silver normalization.
- Counts, exclusions and file metadata are traceable.
- One file failure does not hide the status of the other file.

## F07 — Airbnb summary and neighbourhood ingestion/Bronze

**Goal:** land the summary and geographical reference files without conflating them with detailed facts.

### Subfeature breakdown

#### F07.1 — Summary source registration and Bronze

**Task IDs:** `F07.1-T01`, `F07.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F07. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F07.2 — Neighbourhood CSV and GeoJSON Bronze

**Task IDs:** `F07.2-T01`, `F07.2-T02`, `F07.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F07. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F07.3 — Geometry, availability and replacement validation

**Task IDs:** `F07.3-T01`, `F07.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F07. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F07.1-T01** — Inspect `listings.csv`, `reviews.csv`, `neighbourhoods.csv` and `neighbourhoods.geojson` for the selected source snapshot.
- **F07.1-T02** — Register each file separately and preserve its schema/version.
- **F07.2-T01** — Parse summary files into distinct Bronze sources; do not union them with detailed rows.
- **F07.2-T02** — Parse neighbourhood CSV and GeoJSON as separate assets, retaining source identifiers/names and geometry properties.
- **F07.2-T03** — Validate GeoJSON structure and record geometry feature counts.
- **F07.3-T01** — Record missing/not-published status separately from download or schema failure.
- **F07.3-T02** — Add rerun and replacement tests.

### Acceptance criteria
- Each available summary and neighbourhood file has an independent manifest/ingestion status.
- Summary rows remain separate from detailed listing/review facts.
- Geometry is preserved and can be read by the intended spatial tooling.
- Partial source availability is visible rather than silently ignored.

## F08 — Airbnb listings Silver

**Goal:** normalize detailed listing observations into a trusted listing dataset.

### Subfeature breakdown

#### F08.1 — Listing Silver contract and normalization

**Task IDs:** `F08.1-T01`, `F08.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F08. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F08.2 — Business validation, exclusions and deduplication

**Task IDs:** `F08.2-T01`, `F08.2-T02`, `F08.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F08. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F08.3 — Silver tests and reconciliation

**Task IDs:** `F08.3-T01`, `F08.3-T02`, `F08.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F08. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F08.1-T01** — Define listing Silver contract and business key after inspecting real source IDs.
- **F08.1-T02** — Normalize field names and data types.
- **F08.2-T01** — Parse prices into numeric amount and currency while preserving raw strings.
- **F08.2-T02** — Normalize booleans, counts, dates, host/listing attributes and coordinates.
- **F08.2-T03** — Validate plausible price, capacity, coordinate and identifier ranges.
- **F08.3-T01** — Separate valid rows from quarantined/excluded rows with reason codes.
- **F08.3-T02** — Deduplicate according to documented city/snapshot/listing identity rules.
- **F08.3-T03** — Add tests using representative valid, malformed, duplicate and missing-value rows.

### Acceptance criteria
- Silver schema is typed and versioned.
- Raw source values/provenance remain available for audit.
- Accepted + excluded + duplicate outcomes reconcile to input counts.
- No field is silently reinterpreted as live booking data.

## F09 — Airbnb calendar and review Silver

**Goal:** normalize date-level calendar and review-level records while retaining their distinct semantics.

### Subfeature breakdown

#### F09.1 — Calendar Silver model

**Task IDs:** `F09.1-T01`, `F09.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F09. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F09.2 — Review Silver model and privacy minimization

**Task IDs:** `F09.2-T01`, `F09.2-T02`

**Deliverable:** a reviewable implementation increment for this part of F09. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F09.3 — Relationship, history and quality validation

**Task IDs:** `F09.3-T01`, `F09.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F09. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F09.1-T01** — Define the calendar grain as listing/date/source snapshot and review grain using the actual stable review key or documented composite key.
- **F09.1-T02** — Parse calendar dates, reported availability indicators and prices with explicit currency handling.
- **F09.2-T01** — Normalize review IDs, listing IDs, dates and review text fields; minimize or exclude unnecessary reviewer identity fields.
- **F09.2-T02** — Validate listing relationships against Silver listings without losing unmatched rows silently.
- **F09.3-T01** — Add duplicate, invalid-date, malformed-price, missing-listing and out-of-range tests.
- **F09.3-T02** — Preserve all source snapshot context needed for historical comparisons.

### Acceptance criteria
- Calendar and review Silver outputs have clear grains and contracts.
- Relationship failures have auditable reasons.
- Review identity data is minimized for the product's analytical use.
- Counts and exclusions reconcile independently for both datasets.

## F10 — Airbnb summary reconciliation and neighbourhood/spatial Silver

**Goal:** turn source summaries and boundaries into validated references for the listing data.

### Subfeature breakdown

#### F10.1 — Summary reconciliation products

**Task IDs:** `F10.1-T01`, `F10.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F10. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F10.2 — Neighbourhood and geometry normalization

**Task IDs:** `F10.2-T01`, `F10.2-T02`

**Deliverable:** a reviewable implementation increment for this part of F10. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F10.3 — Spatial linkage and audit validation

**Task IDs:** `F10.3-T01`, `F10.3-T02`, `F10.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F10. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F10.1-T01** — Normalize listing and review summary files into separate Silver reference products.
- **F10.1-T02** — Compare summary metrics with detailed-derived metrics only where grain, filters and definitions align.
- **F10.2-T01** — Normalize neighbourhood IDs/names from CSV and geometry properties from GeoJSON.
- **F10.2-T02** — Validate geometry, coordinate reference assumptions, duplicate names and missing IDs.
- **F10.3-T01** — Link listings to source neighbourhood attributes; where needed, use point-in-polygon matching and record method/confidence.
- **F10.3-T02** — Retain unmatched or ambiguous spatial assignments for audit.
- **F10.3-T03** — Add reconciliation and spatial-join tests.

### Acceptance criteria
- Source summaries are not double-counted as additional listing/review facts.
- Neighbourhood matching rules are explicit and testable.
- Invalid geometries and ambiguous matches are visible.
- Derived spatial relationships retain source and method metadata.

## F11 — Airbnb cross-file quality, snapshot history and data monitoring

**Goal:** establish trustworthy cross-dataset controls and operational visibility.

### Subfeature breakdown

#### F11.1 — Cross-file reconciliation and relationship quality

**Task IDs:** `F11.1-T01`, `F11.1-T02`, `F11.1-T03`

**Deliverable:** a reviewable implementation increment for this part of F11. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F11.2 — Snapshot history, coverage and freshness

**Task IDs:** `F11.2-T01`, `F11.2-T02`, `F11.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F11. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F11.3 — Operational quality reporting and recovery

**Task IDs:** `F11.3-T01`, `F11.3-T02`, `F11.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F11. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F11.1-T01** — Reconcile file-level input, Bronze, Silver, accepted, excluded and duplicate counts.
- **F11.1-T02** — Validate listing-to-calendar and listing-to-review relationships.
- **F11.1-T03** — Compare source summary metrics with derived metrics where definitions align.
- **F11.2-T01** — Track city/file/snapshot completeness and freshness.
- **F11.2-T02** — Compare at least two snapshots where available to identify new, removed and changed listings.
- **F11.2-T03** — Make explicit that this is snapshot change analysis, not CDC.
- **F11.3-T01** — Store quality results and pipeline run details in queryable operational tables.
- **F11.3-T02** — Add basic dashboard/report queries for failed files, stale snapshots, row-count anomalies and quality thresholds.
- **F11.3-T03** — Write recovery procedures for failed or partial city runs.

### Acceptance criteria
- Quality metrics can be queried by city, snapshot and file type.
- Cross-file relationship failures and snapshot changes are explainable.
- A partial city ingestion is not marked complete.
- A failed run can be investigated and retried without corrupting previously successful sources.

## F12 — Airbnb Gold data products

**Goal:** create application-ready accommodation products with clear measures and lineage.

### Subfeature breakdown

#### F12.1 — Gold product requirements and grain design

**Task IDs:** `F12.1-T01`

**Deliverable:** a reviewable implementation increment for this part of F12. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F12.2 — Core accommodation Gold tables

**Task IDs:** `F12.2-T01`, `F12.2-T02`, `F12.2-T03`, `F12.2-T04`

**Deliverable:** a reviewable implementation increment for this part of F12. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F12.3 — Profiles, snapshot changes and Gold validation

**Task IDs:** `F12.3-T01`, `F12.3-T02`, `F12.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F12. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F12.1-T01** — Define the grain and keys for each Gold product before implementing it.
- **F12.2-T01** — Build listing snapshot Gold with search-ready fields, price/currency, city, snapshot and data quality context.
- **F12.2-T02** — Build calendar observation Gold with listing/date/snapshot grain and explicit interpretation caveats.
- **F12.2-T03** — Build review Gold and listing-level review metrics where supported by the source fields.
- **F12.2-T04** — Build neighbourhood and city profiles with documented counts and distributions.
- **F12.3-T01** — Build snapshot change outputs only where multiple snapshots and stable IDs support comparison.
- **F12.3-T02** — Include source completeness/freshness and attribution fields or a stable join to metadata tables.
- **F12.3-T03** — Add Gold-level tests for grain, key uniqueness, metric definitions and Silver reconciliation.

### Acceptance criteria
- Gold products answer specific accommodation discovery and comparison questions.
- Each table has a documented grain, key and metric definition.
- Currency, snapshot date and source limitations remain visible.
- Gold outputs reconcile to approved Silver inputs.

## F13 — Python accommodation service layer

**Goal:** expose tested, deterministic functions over Airbnb Gold for both Streamlit and the LLM.

### Subfeature breakdown

#### F13.1 — Service contracts and data access foundation

**Task IDs:** `F13.1-T01`

**Deliverable:** a reviewable implementation increment for this part of F13. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F13.2 — Accommodation search and detail capabilities

**Task IDs:** `F13.2-T01`, `F13.2-T02`, `F13.2-T03`, `F13.2-T04`

**Deliverable:** a reviewable implementation increment for this part of F13. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F13.3 — Context, errors and service-level tests

**Task IDs:** `F13.3-T01`, `F13.3-T02`, `F13.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F13. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F13.1-T01** — Define typed request/response models.
- **F13.2-T01** — Implement listing search with allowlisted filters, validated bounds and result limits.
- **F13.2-T02** — Implement listing detail and comparison functions.
- **F13.2-T03** — Add calendar, review and neighbourhood functions as their Gold products become available.
- **F13.2-T04** — Use parameterized SQL or controlled data access; do not accept arbitrary SQL from the user/model.
- **F13.3-T01** — Return city, currency, snapshot date, freshness and caveats with results.
- **F13.3-T02** — Add predictable error responses for missing city, no results, stale data and unsupported filters.
- **F13.3-T03** — Test service functions without Streamlit or an LLM.

### Acceptance criteria
- Python services work independently of the UI/model.
- Input and output contracts are documented and tested.
- Query limits prevent unexpectedly large result payloads.
- Results carry enough provenance to support trustworthy explanations.

## F14 — Streamlit Airbnb application

**Goal:** build the first useful product interface using the service layer.

### Subfeature breakdown

#### F14.1 — Streamlit application shell and navigation

**Task IDs:** `F14.1-T01`, `F14.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F14. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F14.2 — Accommodation discovery and comparison experience

**Task IDs:** `F14.2-T01`, `F14.2-T02`, `F14.2-T03`, `F14.2-T04`

**Deliverable:** a reviewable implementation increment for this part of F14. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F14.3 — Context, usability and integration validation

**Task IDs:** `F14.3-T01`, `F14.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F14. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F14.1-T01** — Create a modular Streamlit app shell and configuration.
- **F14.1-T02** — Add city and snapshot selection based on actual coverage.
- **F14.2-T01** — Build listing search/filter/explorer page.
- **F14.2-T02** — Add listing detail and side-by-side comparison.
- **F14.2-T03** — Add map/neighbourhood view where geometry and coordinate quality support it.
- **F14.2-T04** — Add calendar/review insights as the corresponding Gold products become available.
- **F14.3-T01** — Show source date, currency, limitations, loading/empty/stale/error states.
- **F14.3-T02** — Add tests for service-to-UI integration and a reproducible local run guide.

### Acceptance criteria
- A user can discover and compare listings for a supported city.
- Streamlit calls Python services and does not contain duplicated SQL/business logic.
- The app presents source context and does not imply live booking data.
- A reviewer can run the app locally using documented configuration.

## F15 — Airbnb conversational assistant with structured tool calling

**Goal:** add the first chatbot to the same Airbnb product, not as a separate demo.

### Subfeature breakdown

#### F15.1 — Assistant scope, model and prompt foundation

**Task IDs:** `F15.1-T01`, `F15.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F15. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F15.2 — Typed tool calling and request clarification

**Task IDs:** `F15.2-T01`, `F15.2-T02`, `F15.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F15. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F15.3 — Grounded responses, failure handling and safety checks

**Task IDs:** `F15.3-T01`, `F15.3-T02`, `F15.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F15. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F15.1-T01** — Select a model/provider accessible within budget and record model/provider/version/configuration.
- **F15.1-T02** — Define supported intents: search listings, compare options, explain a city/neighbourhood profile and summarize supported calendar/review observations.
- **F15.2-T01** — Expose F13 service functions as read-only model tools with typed schemas and descriptions.
- **F15.2-T02** — Validate tool arguments server-side and enforce allowlists, row limits and tool-call limits.
- **F15.2-T03** — Ask for missing city or essential filters rather than inventing them.
- **F15.3-T01** — Ground listing claims in tool outputs and include snapshot, currency and source caveats.
- **F15.3-T02** — Handle no-result, unsupported question, stale data and service failure clearly.
- **F15.3-T03** — Keep prompt/model/tool configuration versioned and keep secrets outside source control.

### Acceptance criteria
- A working Airbnb chatbot can answer supported natural-language requests by calling tested functions.
- It produces consistent structured tool arguments and does not generate arbitrary SQL.
- It does not claim actual occupancy, booking availability or guaranteed future prices.
- The same service works without the LLM and has separate service-level tests.

## F16 — Airbnb AI evaluation and request tracing

**Goal:** measure the first assistant rather than relying on a few successful demos.

### Subfeature breakdown

#### F16.1 — Evaluation dataset and expected tool behaviour

**Task IDs:** `F16.1-T01`, `F16.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F16. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F16.2 — Quality metrics and evaluation execution

**Task IDs:** `F16.2-T01`, `F16.2-T02`, `F16.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F16. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F16.3 — Tracing, privacy and regression reporting

**Task IDs:** `F16.3-T01`, `F16.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F16. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F16.1-T01** — Create a small versioned question set covering normal, ambiguous, unsupported, no-result and failure cases.
- **F16.1-T02** — Define expected tool and expected arguments for tool-selection tests.
- **F16.2-T01** — Evaluate argument correctness, service result correctness, answer faithfulness and source/caveat disclosure.
- **F16.2-T02** — Record model, prompt, tool schema, dataset/snapshot and evaluation version.
- **F16.2-T03** — Add request/correlation IDs and trace model calls, tool calls, statuses, latency and usage where available.
- **F16.3-T01** — Redact personal information and secrets; do not store raw chat history unnecessarily.
- **F16.3-T02** — Capture evaluation output as a report/artifact and add a regression gate for critical test cases.

### Acceptance criteria
- A repeatable evaluation run reports tool selection, arguments and answer quality separately.
- Failures are traceable to a request and tested revision without exposing sensitive data.
- Evaluation scores are not presented without dataset and run metadata.

## F17 — Airbnb multi-city expansion toward 50 and 100-city readiness

**Goal:** scale the verified Airbnb architecture without city-specific code copies. This feature is reached after F01–F16; it is not pulled forward as a shortcut.

### Subfeature breakdown

#### F17.1 — City eligibility and registry onboarding

**Task IDs:** `F17.1-T01`, `F17.1-T02`

**Deliverable:** a city registry contract that distinguishes configured cities from source-eligible cities and records the metadata needed for repeatable processing.

**Subfeature exit gate:** city identity, timezone, currency, coordinates/boundary reference and eligibility states are validated and documented.

#### F17.2 — Candidate cohort and source-availability audit

**Task IDs:** `F17.2-T01`, `F17.2-T02`, `F17.2-T03`

**Deliverable:** a versioned candidate-city inventory with a buffer beyond the 50-city target and explicit source/file availability states.

**Subfeature exit gate:** catalogue evidence, candidate selection rules, exclusion reasons and a reproducible registry/manifest update are recorded.

#### F17.3 — Multi-city batch execution and failure isolation

**Task IDs:** `F17.3-T01`, `F17.3-T02`, `F17.3-T03`

**Deliverable:** bounded city/file/snapshot execution with independent run state, retries and failure isolation.

**Subfeature exit gate:** representative city variation is tested; one failed city/file does not invalidate successful outputs; failed units can be rerun safely.

#### F17.4 — Controlled multi-city Bronze rollout

**Task IDs:** `F17.4-T01`, `F17.4-T02`, `F17.4-T03`

**Deliverable:** detailed-listings Bronze ingestion across bounded city batches, using the shared ingestion path and per-city/file/snapshot run state.

**Subfeature exit gate:** pilot and batch runs demonstrate bounded execution, source-faithful landing, idempotency and failure isolation; actual runtime evidence is recorded.

#### F17.5 — Multi-city Silver validation and reconciliation

**Task IDs:** `F17.5-T01`, `F17.5-T02`, `F17.5-T03`

**Deliverable:** core Silver listings for the eligible cohort, with consistent normalization, quarantine/exclusion reasons and city-level reconciliation.

**Subfeature exit gate:** Silver contracts pass for the accepted city cohort; input/accepted/rejected/duplicate counts reconcile; city-level failures remain isolated.

#### F17.6 — Backfill, coverage reporting and scale validation

**Task IDs:** `F17.6-T01`, `F17.6-T02`, `F17.6-T03`

**Deliverable:** safe rerun/backfill behaviour and city/file/snapshot coverage reporting, supported by measured batch performance.

**Subfeature exit gate:** failed/changed units can be reprocessed safely; coverage distinguishes unavailable, not-published, failed, loaded and validated states; scale limits are documented.

#### F17.7 — 50-city acceptance and evidence

**Task IDs:** `F17.7-T01`, `F17.7-T02`, `F17.7-T03`

**Deliverable:** a reproducible 50-city coverage report and release evidence pack, or a transparent source-availability shortfall report.

**Subfeature exit gate:** every counted city meets the 50-city definition; all other cities/files have explicit statuses; tested commit, CI and Databricks evidence are recorded.

#### F17.8 — 100-city readiness review

**Task IDs:** `F17.8-T01`, `F17.8-T02`

**Deliverable:** an evidence-based review of configuration, keys, operational tables, batch sizing and remaining constraints for future growth toward 100 cities.

**Subfeature exit gate:** the review identifies measured capacity, bottlenecks, risks and the changes required before a 100-city expansion.

### Tasks

- **F17.1-T01** — Define the city registry contract and eligibility states; distinguish configured cities from source-eligible cities.
- **F17.1-T02** — Register city ID, canonical name, country, timezone, currency, coordinates/boundary reference and source status.
- **F17.2-T01** — Inspect the current Inside Airbnb catalogue and capture the catalogue retrieval date and candidate snapshot dates.
- **F17.2-T02** — Select a candidate pool larger than 50; record country/region, timezone, currency, source date and file availability where available.
- **F17.2-T03** — Define deterministic eligibility/exclusion rules and record why a candidate cannot count toward the 50-city target.
- **F17.3-T01** — Test representative city variation in schema, file size, price/currency strings, missing columns and geography.
- **F17.3-T02** — Define the execution unit as city × source file × snapshot, with a stable idempotency key and independent run status.
- **F17.3-T03** — Implement bounded retries/checkpointing so a failed city/file can be rerun without rewriting successful outputs.
- **F17.4-T01** — Pilot a small representative cohort, then increase batch size only after measuring runtime, resource usage, quota behaviour and failure rate.
- **F17.4-T02** — Process city/file/snapshot units in bounded batches with independent run statuses.
- **F17.4-T03** — Verify source-faithful Bronze outputs, provenance, idempotency and isolation of failed units.
- **F17.5-T01** — Apply the existing Silver contract consistently across cities; add representative fixtures for currency/price formats, missing fields, schema variation and geography.
- **F17.5-T02** — Reconcile source, Bronze, accepted Silver, rejected/quarantined and duplicate counts per city/snapshot.
- **F17.5-T03** — Validate cross-city keys, city metadata, currency context and source snapshot lineage; do not compare raw prices across currencies.
- **F17.6-T01** — Add safe rerun/backfill and source replacement behaviour at city/file/snapshot grain.
- **F17.6-T02** — Track completeness for every city, file class and snapshot; separate not-published from failure.
- **F17.6-T03** — Benchmark representative batches and optimize only measured bottlenecks.
- **F17.7-T01** — Publish a report distinguishing configured, eligible, Bronze-loaded and Silver-validated cities.
- **F17.7-T02** — Report secondary file coverage independently for calendar, detailed reviews, summary listings, summary reviews, neighbourhood CSV and GeoJSON.
- **F17.7-T03** — Capture tested commit, CI link, Databricks run evidence, counts, limitations and the final 50-city acceptance decision.
- **F17.8-T01** — Review the verified 50-city processing report and identify gaps against the target.
- **F17.8-T02** — Review configuration, keys, operational tables and batch sizing for future growth toward 100 cities.

### Acceptance criteria

- The same code processes multiple cities through configuration; no city-specific notebook or service copies are required.
- Candidate eligibility is based on current source evidence, not a static city-name list.
- City/file/snapshot outcomes are independent, traceable and safely rerunnable.
- Bronze and Silver outputs pass their contracts and reconciliation checks for every city counted.
- Coverage reports distinguish configured, eligible, unavailable, not-published, failed, Bronze-loaded and Silver-validated states.
- A city counts toward the 50-city target only when detailed-listings Bronze and core Silver succeed with provenance, quality/reconciliation and actual runtime evidence.
- Secondary file classes retain independent availability and processing statuses.
- The 100-city review is based on measured evidence rather than assumed linear scaling.

---

## F18 — Overture Places acquisition and Bronze

**Goal:** acquire versioned Overture Places releases for configured city areas.

### Subfeature breakdown

#### F18.1 — Overture release, schema and licence registration

**Task IDs:** `F18.1-T01`, `F18.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F18. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F18.2 — City-area acquisition and Bronze processing

**Task IDs:** `F18.2-T01`, `F18.2-T02`, `F18.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F18. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F18.3 — Provenance, schema drift and rerun validation

**Task IDs:** `F18.3-T01`, `F18.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F18. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F18.1-T01** — Inspect the current Overture release, schema version, Places taxonomy and changelog.
- **F18.1-T02** — Review attribution and source-provider licence information for the selected release.
- **F18.2-T01** — Pin the release ID and manifest.
- **F18.2-T02** — Select configured city areas/bounding boxes and read only the required columns/partitions where possible.
- **F18.2-T03** — Preserve raw GeoParquet source/version and `sources[]` lineage.
- **F18.3-T01** — Write a source-faithful Bronze product with release, retrieval, hash and city metadata.
- **F18.3-T02** — Test missing columns, changed schema, geometry, empty city extraction and rerun behaviour.

### Acceptance criteria
- A reproducible pinned release is ingested for a sample city area.
- Release/schema/provider lineage and licence metadata are preserved.
- The process can be repeated without downloading or rewriting unrelated city data.

## F19 — Overture Places Silver: taxonomy, geometry, confidence and deduplication

**Goal:** normalize place records into a usable canonical layer.

### Subfeature breakdown

#### F19.1 — Places normalization and taxonomy mapping

**Task IDs:** `F19.1-T01`, `F19.1-T02`, `F19.1-T03`

**Deliverable:** a reviewable implementation increment for this part of F19. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F19.2 — Confidence, geometry and provenance controls

**Task IDs:** `F19.2-T01`, `F19.2-T02`, `F19.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F19. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F19.3 — Deduplication, schema evolution and Silver validation

**Task IDs:** `F19.3-T01`, `F19.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F19. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F19.1-T01** — Normalize names, addresses, phone/website fields, geometry and IDs.
- **F19.1-T02** — Use current `taxonomy` and `basic_category`; do not depend on the removed legacy `categories` field.
- **F19.1-T03** — Map taxonomy values into TripPilot lodging, food/drink and attraction groups using versioned configuration.
- **F19.2-T01** — Preserve confidence and provider sources.
- **F19.2-T02** — Define confidence thresholds and audit low-confidence records.
- **F19.2-T03** — Detect duplicate candidates using stable IDs and conservative spatial/name matching; retain uncertain pairs for review.
- **F19.3-T01** — Validate geometry and core field completeness.
- **F19.3-T02** — Add release-to-release change tests and schema compatibility checks.

### Acceptance criteria
- Canonical place Silver data retains Overture identity and source lineage.
- Category mapping is versioned and testable.
- Confidence, duplicate and completeness rules are explicit.
- Ambiguous duplicates are not silently merged.

## F20 — Places Gold, discovery functions and application integration

**Goal:** support hotel/lodging, restaurant/cafe and attraction discovery through one shared service.

### Subfeature breakdown

#### F20.1 — Places Gold model and category products

**Task IDs:** `F20.1-T01`, `F20.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F20. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F20.2 — Nearby/category discovery service

**Task IDs:** `F20.2-T01`, `F20.2-T02`, `F20.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F20. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F20.3 — Application/AI integration and query evaluation

**Task IDs:** `F20.3-T01`, `F20.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F20. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F20.1-T01** — Create `gold_places` with documented grain, location, taxonomy, confidence and provenance.
- **F20.1-T02** — Create category-specific views/products for lodging, restaurants/cafes and attractions.
- **F20.2-T01** — Implement nearby/category search using coordinates and a bounded radius/result cap.
- **F20.2-T02** — Return address/name/source/confidence and availability caveats where fields are absent.
- **F20.2-T03** — Add place results to Streamlit and expose the same function as an AI tool.
- **F20.3-T01** — Optionally test semantic retrieval over curated place descriptions, keeping canonical structured place data in Gold.
- **F20.3-T02** — Add duplicate/coverage and query correctness tests.

### Acceptance criteria
- One source pipeline supports three discovery categories.
- Place discovery works for configured cities and exposes source quality.
- No hotel room rate, reservation availability or verified opening-hours claims are invented.
- Streamlit and AI tools use the same places service.

---

# Part D — Public transportation

## F21 — GTFS agency registry and Bronze acquisition

**Goal:** acquire official static GTFS feeds and preserve their versions.

### Subfeature breakdown

#### F21.1 — Agency discovery, terms and registry

**Task IDs:** `F21.1-T01`, `F21.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F21. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F21.2 — GTFS feed acquisition and Bronze landing

**Task IDs:** `F21.2-T01`, `F21.2-T02`

**Deliverable:** a reviewable implementation increment for this part of F21. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F21.3 — Feed completeness, versioning and invalid-feed handling

**Task IDs:** `F21.3-T01`, `F21.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F21. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F21.1-T01** — Identify a small set of target agencies with official current feeds.
- **F21.1-T02** — Review licence/terms, service dates and publisher information.
- **F21.2-T01** — Create the agency registry with timezone, URL, feed hash/version, retrieval date and status.
- **F21.2-T02** — Preserve each downloaded ZIP and unpacked source files.
- **F21.3-T01** — Record which required, conditional and optional files are present.
- **F21.3-T02** — Add feed replacement, invalid ZIP and incomplete-feed handling.

### Acceptance criteria
- Every feed is traceable to an official agency/publisher and licence.
- Feed files and service validity are versioned.
- Missing/invalid files produce explicit feed status.

## F22 — GTFS Silver and schedule validation

**Goal:** normalize feed tables and validate identifiers, relationships and service calendars.

### Subfeature breakdown

#### F22.1 — GTFS Silver contracts and normalization

**Task IDs:** `F22.1-T01`, `F22.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F22. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F22.2 — Relationships, calendars and time validation

**Task IDs:** `F22.2-T01`, `F22.2-T02`, `F22.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F22. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F22.3 — Feed acceptance and schema compatibility tests

**Task IDs:** `F22.3-T01`, `F22.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F22. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F22.1-T01** — Normalize agency, routes, trips, stops, stop_times, calendar and calendar_dates.
- **F22.1-T02** — Validate required/conditional files against the current GTFS specification.
- **F22.2-T01** — Validate primary/foreign keys and stop coordinates.
- **F22.2-T02** — Validate times, service dates and calendar exceptions.
- **F22.2-T03** — Apply agency timezone and GTFS time conventions.
- **F22.3-T01** — Preserve unknown/optional fields where practical without letting them break core processing.
- **F22.3-T02** — Add feed acceptance tests and version-to-version schema checks.

### Acceptance criteria
- Selected feed tables pass structural and relationship checks.
- Calendar exceptions and timezone interpretation are tested.
- Invalid or expired feed versions are not silently marked current.

## F23 — GTFS Gold, transit functions and assistant integration

**Goal:** provide simple transit discovery and schedule lookups.

### Subfeature breakdown

#### F23.1 — Transit Gold data products

**Task IDs:** `F23.1-T01`, `F23.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F23. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F23.2 — Schedule and nearby-stop service functions

**Task IDs:** `F23.2-T01`, `F23.2-T02`, `F23.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F23. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F23.3 — Assistant integration and schedule correctness tests

**Task IDs:** `F23.3-T01`, `F23.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F23. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F23.1-T01** — Build Gold stop, route, trip and schedule products around the initial use cases.
- **F23.1-T02** — Implement nearby-stop lookup by coordinate/radius.
- **F23.2-T01** — Implement routes serving a stop.
- **F23.2-T02** — Implement schedule lookup for a requested service date/time using calendar/calendar_dates.
- **F23.2-T03** — Return agency, feed date, service validity, timezone and static-schedule caveat.
- **F23.3-T01** — Add service tests for service day, exception dates, midnight-crossing and unknown stop.
- **F23.3-T02** — Add transit page/function/tool only after the service passes tests.

### Acceptance criteria
- Results match reference feed records for test cases.
- Schedule service correctly handles dates, exceptions and timezone.
- The application does not describe static schedule values as live vehicle locations or arrivals.

---

# Part E — Weather service

## F24 — Weather provider adapter, cache and AI integration

**Goal:** provide date-aware weather lookup with a replaceable provider contract.

### Subfeature breakdown

#### F24.1 — Weather provider contract and terms review

**Task IDs:** `F24.1-T01`, `F24.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F24. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F24.2 — Provider adapter, validation and cache

**Task IDs:** `F24.2-T01`, `F24.2-T02`, `F24.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F24. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F24.3 — Resilience, UI/AI integration and provider tests

**Task IDs:** `F24.3-T01`, `F24.3-T02`, `F24.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F24. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F24.1-T01** — Verify current Open-Meteo terms, non-commercial usage limits, attribution and forecast horizon.
- **F24.1-T02** — Define provider-neutral request/response contracts.
- **F24.2-T01** — Implement location/coordinates, dates, units and forecast product validation.
- **F24.2-T02** — Add a cache with clear key, expiry and stale response handling.
- **F24.2-T03** — Add bounded retry/backoff and rate-limit/error states.
- **F24.3-T01** — Return provider, retrieval time, issue time, valid period and units.
- **F24.3-T02** — Add weather summary to Streamlit and expose a constrained AI tool.
- **F24.3-T03** — Add provider/cache tests, including stale and unsupported horizon.

### Acceptance criteria
- The provider can be replaced without changing the app/tool contract.
- Cache hits avoid unnecessary provider calls.
- Forecast, historical and climate information are not conflated.
- Provider attribution and free-tier restrictions are respected.

---

# Part F — Official documents, vector database and RAG

## F25 — Official visitor/event document catalogue and ingestion

**Goal:** establish a small, permission-aware document corpus for destination questions.

### Subfeature breakdown

#### F25.1 — Document source selection and rights review

**Task IDs:** `F25.1-T01`, `F25.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F25. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F25.2 — Document catalogue and versioned acquisition

**Task IDs:** `F25.2-T01`, `F25.2-T02`, `F25.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F25. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F25.3 — Text extraction, event metadata and expiry controls

**Task IDs:** `F25.3-T01`, `F25.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F25. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F25.1-T01** — Select official tourism, city/government, park, museum, cultural and transit publishers.
- **F25.1-T02** — Review terms/licence and decide whether storing, extracting and embedding the content is permitted.
- **F25.2-T01** — Create a manifest with URL, publisher, city, language, document type, dates, licence/terms, content hash, retrieval date and review/expiry date.
- **F25.2-T02** — Acquire files using permitted source methods; preserve original source references and versions.
- **F25.2-T03** — Extract text/tables and useful structure; retain page/section/source links where available.
- **F25.3-T01** — Extract event fields only when supported by explicit source text.
- **F25.3-T02** — Detect changed/expired documents and mark old versions appropriately.

### Acceptance criteria
- Every document has provenance and a recorded usage decision.
- Extracted text can be traced to page/section/source.
- Undated or expired information cannot silently appear as a current event.

## F26 — Chunking, embeddings and vector database index

**Goal:** build a versioned retrieval index sourced from curated document chunks.

### Subfeature breakdown

#### F26.1 — Chunking strategy and canonical chunk records

**Task IDs:** `F26.1-T01`, `F26.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F26. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F26.2 — Embedding generation and version management

**Task IDs:** `F26.2-T01`, `F26.2-T02`, `F26.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F26. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F26.3 — Vector index synchronization and retrieval metadata tests

**Task IDs:** `F26.3-T01`, `F26.3-T02`, `F26.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F26. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F26.1-T01** — Define deterministic chunking that respects headings, paragraphs, tables and page boundaries where useful.
- **F26.1-T02** — Create chunk IDs and preserve document ID, city, language, publisher, type, page/section, publication date, validity dates, licence and content hash.
- **F26.2-T01** — Select an embedding model available to the actual development environment; record provider, model, dimension and configuration.
- **F26.2-T02** — Store canonical chunks and embedding/index metadata in a Delta-backed table where supported.
- **F26.2-T03** — Evaluate Databricks AI Search Delta Sync index first; verify Free Edition endpoint and embedding capabilities in the workspace.
- **F26.3-T01** — Add a retrieval-provider adapter so an alternate local development vector store can be used only if the managed option is inaccessible.
- **F26.3-T02** — Use triggered index synchronization initially and record sync status/version.
- **F26.3-T03** — Add index freshness, duplicate-chunk and metadata-filter tests.

### Acceptance criteria
- A query can retrieve the appropriate chunk and its original source metadata.
- Embedding and index versions are reproducible.
- City/date/document-type filters work.
- The vector index is treated as a retrieval structure, not the canonical source of truth.

## F27 — RAG retrieval service and evaluation

**Goal:** answer destination questions using evidence from the indexed official corpus.

### Subfeature breakdown

#### F27.1 — Retrieval service and metadata filtering

**Task IDs:** `F27.1-T01`, `F27.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F27. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F27.2 — Retrieval/answer evaluation and grounded generation

**Task IDs:** `F27.2-T01`, `F27.2-T02`, `F27.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F27. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F27.3 — Freshness, no-answer handling and assistant integration

**Task IDs:** `F27.3-T01`, `F27.3-T02`, `F27.3-T03`, `F27.3-T04`

**Deliverable:** a reviewable implementation increment for this part of F27. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F27.1-T01** — Implement a retrieval function with keyword/vector or hybrid retrieval as supported.
- **F27.1-T02** — Apply city, language, document type and validity-date filters.
- **F27.2-T01** — Create a labelled evaluation set with questions, relevant document/chunk IDs and no-answer examples.
- **F27.2-T02** — Measure retrieval Hit Rate/Recall@K and context relevance.
- **F27.2-T03** — Generate answers using retrieved passages and source references.
- **F27.3-T01** — Evaluate faithfulness, answer relevance, citation/source correctness and unsupported-answer rate.
- **F27.3-T02** — Handle outdated sources, missing evidence and conflicting documents explicitly.
- **F27.3-T03** — Version corpus, chunker, embedding model, index and evaluation set.
- **F27.3-T04** — Expose RAG as a tested service/tool to the existing travel assistant.

### Acceptance criteria
- Answers cite the source documents and use valid city/date context.
- No-answer and stale-source cases do not produce fabricated facts.
- Retrieval evaluation is separate from answer evaluation.
- RAG can be tested independently of the full agent.

---

# Part G — MCP and multi-source travel AI

## F28 — MCP server over stable TripPilot services

**Goal:** expose selected existing Python services as typed read-only MCP tools.

### Subfeature breakdown

#### F28.1 — MCP tool selection and protocol contracts

**Task IDs:** `F28.1-T01`, `F28.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F28. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F28.2 — Thin server handlers and service integration

**Task IDs:** `F28.2-T01`, `F28.2-T02`, `F28.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F28. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F28.3 — Security limits, errors and parity tests

**Task IDs:** `F28.3-T01`, `F28.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F28. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F28.1-T01** — Select stable tools for accommodation, nearby places, transit, weather and document retrieval.
- **F28.1-T02** — Pin a compatible MCP SDK/version and record transport choice.
- **F28.2-T01** — Define names, descriptions, typed input/output schemas and error contracts.
- **F28.2-T02** — Implement thin MCP handlers that validate inputs and call existing service functions.
- **F28.2-T03** — Add tool allowlists, result limits, timeouts and read-only access.
- **F28.3-T01** — Test discovery, valid calls, invalid arguments and unavailable service cases.
- **F28.3-T02** — Compare MCP response output with direct Python service output.

### Acceptance criteria
- MCP exposes stable tools without moving business rules into handlers.
- Tool discovery/schema and error behaviour are tested.
- Direct-service and MCP results match for equivalent inputs.

## F29 — MCP client and compatible host integration

**Goal:** connect the server to a client/host and verify safe tool use.

### Subfeature breakdown

#### F29.1 — MCP client and tool discovery

**Task IDs:** `F29.1-T01`, `F29.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F29. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F29.2 — Host integration and controlled tool execution

**Task IDs:** `F29.2-T01`, `F29.2-T02`, `F29.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F29. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F29.3 — Timeout, disconnect and partial-failure validation

**Task IDs:** `F29.3-T01`, `F29.3-T02`

**Deliverable:** a reviewable implementation increment for this part of F29. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F29.1-T01** — Build/configure a minimal client using the selected transport.
- **F29.1-T02** — Discover tools and schemas programmatically.
- **F29.2-T01** — Invoke valid and invalid tools through the client.
- **F29.2-T02** — Use MCP Inspector or an equivalent debugging tool where appropriate.
- **F29.2-T03** — Connect the chosen LLM host/agent after client tests pass.
- **F29.3-T01** — Enforce approved tool list, call count, output size and timeouts.
- **F29.3-T02** — Test server disconnect, timeout, malformed output and partial result handling.

### Acceptance criteria
- Client discovery/invocation works and can be reproduced.
- LLM use is constrained to approved MCP tools.
- Failures are handled without inventing successful tool results.

## F30 — Multi-source travel assistant and itinerary planning

**Goal:** evolve the Airbnb chatbot into the complete TripPilot assistant.

### Subfeature breakdown

#### F30.1 — Travel intent and context design

**Task IDs:** `F30.1-T01`, `F30.1-T02`

**Deliverable:** a reviewable implementation increment for this part of F30. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F30.2 — Multi-source tool routing and itinerary composition

**Task IDs:** `F30.2-T01`, `F30.2-T02`, `F30.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F30. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F30.3 — Grounding, partial failures and end-to-end evaluation

**Task IDs:** `F30.3-T01`, `F30.3-T02`, `F30.3-T03`, `F30.3-T04`

**Deliverable:** a reviewable implementation increment for this part of F30. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F30.1-T01** — Define bounded intents and required context for accommodation, places, transit, weather, destination documents and itinerary questions.
- **F30.1-T02** — Ask clarification for missing city, travel dates, budget, location or other essential context.
- **F30.2-T01** — Route structured questions to deterministic services and document questions to RAG.
- **F30.2-T02** — Compose trip suggestions only from tool results and retrieved source passages.
- **F30.2-T03** — Preserve source, snapshot/release date, valid dates, currency, timezone and uncertainty in the response.
- **F30.3-T01** — Handle partial failures—for example, weather succeeds while the selected transit feed is unavailable.
- **F30.3-T02** — Avoid arbitrary tool chains, infinite loops, unrestricted web search or unbounded result payloads.
- **F30.3-T03** — Treat source documents and tool outputs as data, not instructions.
- **F30.3-T04** — Add representative itinerary scenarios and regression tests.

### Acceptance criteria
- The assistant correctly combines at least accommodation, places, weather and one selected transit/document capability.
- Every factual statement is traceable to a service result or retrieved source.
- Missing source coverage and partial failures are reported honestly.
- The itinerary is a planning suggestion, not a reservation or guaranteed route.

---

# Part H — Unified production-oriented monitoring and release

## F31 — Cross-source observability, deployment readiness and portfolio release

**Goal:** consolidate the CI/CD, data monitoring and AI operations built throughout the project into a reviewable release process.

### Subfeature breakdown

#### F31.1 — Release/version and deployment controls

**Task IDs:** `F31.1-T01`, `F31.1-T02`, `F31.1-T03`

**Deliverable:** a reviewable implementation increment for this part of F31. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F31.2 — Unified data, application and AI observability

**Task IDs:** `F31.2-T01`, `F31.2-T02`, `F31.2-T03`

**Deliverable:** a reviewable implementation increment for this part of F31. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F31.3 — Runbooks, recovery and operational readiness

**Task IDs:** `F31.3-T01`, `F31.3-T02`, `F31.3-T03`

**Deliverable:** a reviewable implementation increment for this part of F31. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

#### F31.4 — Portfolio evidence and release sign-off

**Task IDs:** `F31.4-T01`, `F31.4-T02`

**Deliverable:** a reviewable implementation increment for this part of F31. The exact files are selected after repository inspection; reuse existing modules where they already meet the contract.

**Subfeature exit gate:** all listed tasks are complete; targeted tests pass; required runtime checks are evidenced; file changes are reviewed; the result and tested commit are recorded in the subfeature's Notion child page and `docs/progress.md`.

### Tasks
- **F31.1-T01** — Extend F03 CI from lint/tests to validation of source contracts, bundle configuration and deployable artifacts where supported.
- **F31.1-T02** — Define release/version strategy for application code, configuration, source schemas, Gold models, prompts, tools, embeddings and indexes.
- **F31.1-T03** — Use Databricks Declarative Automation Bundles where supported to declare Jobs/pipelines/apps; deploy only to a real available target.
- **F31.2-T01** — Add health checks after deployment; do not treat a successful upload as proof the app is healthy.
- **F31.2-T02** — Consolidate monitoring for source freshness, pipeline failures, data quality, job duration, city/source coverage and resource usage.
- **F31.2-T03** — Add app/service dashboards for request count, latency, exceptions, tool failures and provider/cache states.
- **F31.3-T01** — Add AI/RAG monitoring for model errors, token/usage where available, tool selection, retrieval latency, index freshness, no-answer and groundedness results.
- **F31.3-T02** — Add thresholds and actionable alerts where the platform supports them; otherwise publish a repeatable monitoring report.
- **F31.3-T03** — Write runbooks for source schema changes, failed city batch, duplicate spike, stale GTFS, API rate limit, weather cache, vector-index sync failure, tool failure and bad deployment.
- **F31.4-T01** — Test rollback/recovery for one representative data pipeline and one application deployment path.
- **F31.4-T02** — Prepare the architecture diagram, source/licence inventory, data dictionary, evaluation reports, demo, run instructions and known limitations.

### Acceptance criteria
- CI checks protect the main branch and build artifacts are traceable to commits.
- Deployment status and app health are distinguished.
- Data, application and AI monitoring have documented metrics and evidence.
- At least one representative recovery/rollback procedure is tested.
- The final portfolio claims match verified evidence and actual city/source coverage.

---

## Cross-cutting checklist for every feature

- [ ] Source/schema/release/feed/model version recorded.
- [ ] Licence/terms/attribution reviewed where applicable.
- [ ] Data grain, keys and contracts documented.
- [ ] Provenance, run ID and file/request metadata preserved.
- [ ] Valid, invalid, duplicate, missing and boundary cases tested.
- [ ] Idempotency, replacement, retry and recovery considered.
- [ ] Coverage and freshness are visible.
- [ ] Secrets and personal information are not exposed.
- [ ] CI checks pass and the tested revision is recorded.
- [ ] Actual Databricks/API/Streamlit/MCP runtime verification is recorded where required.
- [ ] Monitoring metrics or log events exist for important operations.
- [ ] Known limitations and next dependency are documented.

## Subfeature completion checklist

- [ ] Parent feature and subfeature IDs match the v29 register.
- [ ] Objective, scope, dependencies and input/output contracts are explicit.
- [ ] Existing repository files were inspected before paths were proposed.
- [ ] File manifest classifies paths as reuse, modify, create or retire.
- [ ] Tasks use stable IDs (`Fxx.y-Tnn`).
- [ ] Unit/contract/integration tests and expected results are recorded.
- [ ] Required runtime verification and evidence are captured.
- [ ] CI result and tested commit are recorded.
- [ ] Notion child page and GitHub `docs/progress.md` agree on status.
- [ ] Remaining limitations and next dependency are explicit.

## Cross-computer handoff checklist

Before ending a session on any computer:

- [ ] Record the active `Fxx.y` and task IDs.
- [ ] Confirm the current Databricks Git folder/repository and branch.
- [ ] Save all intended workspace edits.
- [ ] Run the relevant targeted checks.
- [ ] Commit and push completed work to GitHub where safe; if not, state exactly what remains uncommitted and why.
- [ ] Record the latest commit SHA or clearly identify that no commit exists yet.
- [ ] Update `docs/progress.md` and the Notion child page with actual results.
- [ ] Record the Databricks workspace, catalog/schema, table/Volume and run evidence needed to resume.
- [ ] Write the single next action for the next session.

When resuming on another computer, open the same remote repository and intended branch, pull the latest changes, inspect the working tree, and confirm the Databricks workspace context before editing. Do not rely on files that exist only on the previous computer.

## Suggested progress record

Keep `docs/progress.md` as the source of truth. Update it after each verified feature.

```markdown
# TripPilot Progress — v29

## Current milestone
- Target checkpoint:
- Active feature ID/title:
- Active subfeature ID/title:
- Active task ID(s):
- Status:

## Repository and CI
- Branch / PR / tested commit:
- CI workflow URL/status:
- Python/runtime/dependency versions:

## Databricks environment
- Edition/runtime:
- Catalog/schema/Volume:
- Job/pipeline/bundle target:
- Verified capabilities / restrictions:

## Source coverage
| Source | City/agency/document | Source version/date | File/feed status | Licence review | Evidence |
|---|---|---|---|---|---|

## Data quality and monitoring
- Input/accepted/excluded/duplicate counts:
- Freshness/coverage:
- Schema and relationship checks:
- Job failures/retries/duration:
- Monitors/dashboards/alerts:

## Application and AI
- Services/UI capabilities:
- Model/provider/version:
- Prompt/tool schema version:
- RAG corpus/chunker/embedding/index version:
- MCP server/client version:
- Evaluation set/run and result:
- Tracing/latency/error observations:

## Verified features
| Feature | Tested revision | Runtime | Evidence | Known gaps |
|---|---|---|---|---|

## Current blockers / next action
```

---

# Operational Manual

This section explains how to execute the roadmap above. It applies to every feature and every subfeature, including a complete project restart.

## 1. Project start, restart and computer switching

### 1.1 Start from scratch or rebuild the working environment

Use this sequence when creating a new working copy, setting up a new computer or restarting TripPilot after a long pause.

1. **Read the architecture baseline.** Open `trippilot-project-plan-v29.md` and review the product scope, architecture, source decisions, target repository structure and guardrails.
2. **Read this guide's roadmap.** Confirm the F01–F31 sequence and start with F01 unless the progress record proves that earlier work is already complete.
3. **Obtain the repository.** Clone the existing GitHub repository. If no repository exists yet, create one only after confirming the intended repository name, visibility and initial branch.
4. **Inspect before creating files.** Check whether source files, notebooks, tests, configuration and documentation already exist. Do not rebuild something that is already implemented.
5. **Open Databricks in a browser.** Connect GitHub credentials and create/open a Git folder connected to the same remote repository. Databricks browser UI is a core workspace, not a disposable demonstration environment.
6. **Check the actual workspace.** Confirm available compute, notebook/SQL execution, Unity Catalog, schemas, Volumes, permissions and outbound access only as needed by the first subfeature.
7. **Establish project tracking.** Create or refresh `docs/progress.md`; create a Notion project parent page and the first feature/subfeature pages if you use Notion.
8. **Start F01.1.** Follow the exact F01.1 scope and acceptance criteria below. Do not begin later features just because a folder or notebook exists.
9. **Commit the baseline.** Push the verified repository baseline to GitHub and record the tested commit.
10. **Continue in strict roadmap order.** Complete each subfeature's exit gate before moving forward, unless a documented dependency decision explicitly changes the sequence.

If restarting an existing project, do not assume the repository is empty. First run the resume/inspect workflow below. A restart means re-establishing a trustworthy working environment and state, not deleting and rebuilding verified work.

### 1.2 Resume existing work

Before making any change, establish:
- GitHub remote repository and current branch.
- Latest commit SHA and whether local/workspace edits are uncommitted.
- Current Databricks workspace and Git folder path.
- Current feature/subfeature/task recorded in `docs/progress.md`.
- Matching Notion parent/child page, if used.
- Existing code, tests, notebooks, tables, schemas and runtime evidence.
- Any known blocker, deferred item or decision awaiting approval.

Then classify the current subfeature as:
- `Not started`
- `Partially implemented`
- `Implemented but unverified`
- `Verified already`
- `Blocked`

Give evidence for the classification. Reuse verified work; do not rebuild it.

### 1.3 Cross-computer handoff

**Before leaving a computer**
1. Save notebook and file changes.
2. Run the relevant targeted checks.
3. Review the Git diff.
4. Commit and push completed work where safe.
5. If work is not ready to commit, record the exact uncommitted files and why they remain uncommitted. Do not assume these files will be available on another computer.
6. Update `docs/progress.md` and Notion with the active task, branch, commit, test results and next action.

**When starting on another computer**
1. Open the same Databricks workspace or the intended workspace.
2. Open the existing TripPilot Git folder connected to the same GitHub remote.
3. Select the intended branch and pull the latest changes.
4. Confirm branch, commit and working-tree status.
5. Open `docs/progress.md` and the matching Notion child page.
6. Confirm catalog/schema/Volume and compute access before running data operations.

Never assume that Databricks workspace files, a local clone, GitHub and Notion are automatically synchronized.

## 2. Development environment and working model

### 2.1 Databricks browser-first model

Databricks browser UI remains a primary development environment so work can continue across computers without depending on a complete local Spark/Databricks installation.

| Responsibility | Primary location | Purpose |
|---|---|---|
| PySpark, Spark SQL, Delta and notebooks | Databricks browser workspace | Execute against the actual Databricks environment |
| Unity Catalog, schemas, tables and Volumes | Databricks browser UI | Inspect real metadata and permissions |
| Genie Code-assisted development | Genie Code panel in Databricks browser | Agent-assisted work in the workspace/Git-folder context |
| Durable source code and history | GitHub | Continue from any computer |
| Browser-based repository editing | Databricks Git folder connected to GitHub | Keep workspace edits version-controlled |
| Requirements, task checklists and evidence | Notion | Human-readable tracking and handoff |
| Optional local Python/app work | Local computer | Use when local tooling is useful or required |

GitHub is the durable source-control anchor. Databricks is the primary place for Databricks-native execution. Notion is the tracking and evidence layer.

### 2.2 Connect GitHub and create a Databricks Git folder

The exact Databricks layout can change. Treat these as navigation targets and use the equivalent workspace feature if a label differs.

1. Sign in to the Databricks workspace in a browser.
2. Open the user/profile menu or workspace settings.
3. Find **Settings** → **Linked accounts** or the Git credentials section.
4. Choose GitHub and complete the supported OAuth/credential flow.
5. Return to the workspace and open **Workspace** in the left navigation.
6. Open your user folder or agreed project location.
7. Choose **Create** → **Git folder** (or the equivalent clone action).
8. Paste the existing TripPilot GitHub repository URL.
9. Select the intended branch and confirm the clone.
10. Confirm that the repository files, including this guide, `docs/progress.md`, source code and tests, are visible.

Do not create a second disconnected repository or workspace-only copy. Never paste GitHub tokens into notebooks, source files, prompts or Notion.

### 2.3 Work with the Git folder in the browser

1. Open the repository-backed Git folder.
2. Use the branch selector to choose the subfeature branch.
3. Edit or create the agreed files within the Git folder.
4. Review the Git diff.
5. Use the Git changes interface to stage, commit and push.
6. Confirm that the commit appears on GitHub.

Use the Git folder UI for supported routine operations. Do not assume advanced Git CLI capabilities are enabled in every workspace or Free Edition environment.

### 2.4 Notebook and SQL workflow

**Create or open a notebook**
1. Open the TripPilot Git folder.
2. Navigate to the agreed `notebooks/` location.
3. Choose **Create** → **Notebook** or open the existing notebook.
4. Follow the repository's existing naming and file format conventions.
5. Select Python or SQL as appropriate.
6. Confirm the notebook is saved in the repository-backed Git folder.
7. Attach the compute option actually available in the workspace.
8. Run a harmless first cell before any write operation.

Example only: `notebooks/bronze/airbnb/F05_2_bronze_listings.py`. Reuse the repository's established format and do not create a duplicate just because this example differs.

**Inspect Unity Catalog**
1. Open **Catalog** in the left navigation.
2. Expand the catalogs and schemas actually available.
3. Inspect tables and permissions.
4. Record the actual catalog, schema and Volume names for the subfeature.
5. Do not assume a catalog named `main` or schema named `default` exists or is writable.
6. Use an isolated development/test destination before writing tables.

**Verify with SQL**
1. Open **SQL Editor** from the left navigation.
2. Run read-only inspection queries using actual catalog/schema/table names.
3. Check schema, row counts, keys, duplicates, nulls, exclusions and versions as relevant.
4. Do not run write/overwrite statements against live tables until the target and recovery plan have been reviewed.

Example read-only queries:

```sql
SHOW SCHEMAS IN <catalog_name>;

SHOW TABLES IN <catalog_name>.<schema_name>;

SELECT *
FROM <catalog_name>.<schema_name>.<table_name>
LIMIT 20;
```

### 2.5 Optional local tools

A local editor and Python environment are optional, not prerequisites for every feature. Use them for app development, local unit tests, linting or tasks that cannot be completed efficiently in the browser. If used, connect the local clone to the same GitHub remote and branch.

Do not install a local Spark cluster merely to reproduce Databricks. Local tests are useful but do not replace actual Databricks runtime verification.

## 3. Git and GitHub workflow

Repeat this workflow for each subfeature. Prefer the Databricks Git folder UI when working in the browser; the commands below are an optional local alternative.

### 3.1 Preflight

```bash
git status
git branch --show-current
git diff
```

If the working tree contains unrelated work, do not discard it. Preserve or commit it separately before continuing.

### 3.2 Create a subfeature branch

Example local Git commands; adapt the base branch and naming to the actual repository:

```bash
git switch main
git pull
git switch -c feature/F01-2-project-config
```

Do not assume the default branch is named `main`; inspect the actual repository.

### 3.3 Implement only the agreed scope

Use the task IDs from this guide. Do not combine unrelated future features into the branch.

### 3.4 Run checks

Typical commands, adjusted to the repository's actual tooling:

```bash
python -m pytest
ruff check .
ruff format --check .
```

Do not claim these checks pass until they have actually run. If a tool is not installed, inspect the project dependency setup and add it only through the agreed dependency/CI task.

### 3.5 Review the diff

```bash
git status
git diff --check
git diff
```

Check for credentials, tokens, raw datasets, private data, unrelated generated files, hard-coded local paths and missing tests/documentation.

### 3.6 Commit and push

```bash
git add <specific-files>
git commit -m "feat(F01.2): add environment and source configuration"
git push -u origin feature/F01-2-project-config
```

Prefer explicit file paths over `git add .` when the working tree contains other changes.

### 3.7 Open a pull request

In GitHub:
1. Open the TripPilot repository.
2. Select **Pull requests** → **New pull request**.
3. Set the base branch to the agreed integration branch and compare branch to the feature branch.
4. Review the changed-file list.
5. Add a summary, tests and Databricks verification evidence.
6. Create the pull request and review CI checks.
7. Merge only after the agreed checks and review pass.

After merging, update the local or Databricks Git folder to the base branch and pull. Do not delete a branch that still contains unmerged work.

## 4. Feature, subfeature and Notion tracking

### 4.1 Work hierarchy

- **Feature (`Fxx`):** a roadmap capability with a parent goal and feature-level acceptance criteria.
- **Subfeature (`Fxx.y`):** an independently implementable deliverable with its own objective, file plan, tests and exit gate.
- **Task (`Fxx.y-Tnn`):** a concrete coding, testing, documentation or verification action within one subfeature.

A subfeature should normally fit one focused implementation cycle. Split it only when it has independent inputs/outputs, acceptance criteria or a separate verification boundary. Do not create a Notion page for every minor code edit.

### 4.2 Recommended Notion hierarchy

`TripPilot` → `Feature F12 — Airbnb Gold` (parent) → `F12.1`, `F12.2`, ... (child pages).

The parent feature page contains the feature objective, scope, dependencies, links to subfeature pages, feature-level acceptance criteria, rolled-up status, decisions and blockers.

Each child page contains the objective, scope, dependencies, input/output contracts, exact file plan, UI navigation, task checklist, tests, acceptance criteria, evidence and status.

Notion is recommended for organizing execution and evidence, but it is not a second source of roadmap truth. Copy IDs and acceptance criteria from this guide; do not independently invent or renumber them.

### 4.3 Parent feature page template

```markdown
# Fxx — [Exact feature title]

## Objective
[Feature objective from this guide.]

## Scope and exclusions
[Copy the feature scope and exclusions.]

## Dependencies
[Preceding features/subfeatures and external prerequisites.]

## Subfeatures
- [ ] Fxx.1 — [Title] — [Status] — [Child page]
- [ ] Fxx.2 — [Title] — [Status] — [Child page]

## Feature-level acceptance criteria
[Copy from this guide.]

## Decisions and blockers
- 

## Roll-up status
Not started / In progress / Blocked / Verified / Merged / Deferred / Released
```

### 4.4 Subfeature child page template

Create one child page per subfeature, not per coding task.

```markdown
# Fxx.y — [Exact subfeature title]

## 1. Objective
[What this subfeature delivers.]

## 2. Scope
### Included
- [Included work]

### Excluded
- [Explicitly deferred work]

## 3. Dependencies
- [Prior subfeature]
- [Required workspace/source access]

## 4. Input contract
| Input | Format/schema | Required? | Validation |
|---|---|---|---|

## 5. Output contract
| Output | Grain | Location | Validation |
|---|---|---|---|

## 6. Environment and UI steps
- [Git branch]
- [Databricks page/menu]
- [Notebook/SQL object]
- [Target catalog/schema/Volume]

## 7. File plan
| Action | Path | Reason |
|---|---|---|
| Reuse | | |
| Modify | | |
| Create | | |
| Retire | | |

## 8. Implementation
- [Ordered instructions]
- [Code blocks]
- [Configuration]
- [SQL]

## 9. Task checklist
- [ ] Fxx.y-T01 — ...
- [ ] Fxx.y-T02 — ...

## 10. Tests and verification
| Check | Command/UI action | Expected result | Actual result |
|---|---|---|---|

## 11. Evidence
- Git branch:
- Commit SHA:
- Pull request:
- CI run:
- Databricks notebook/run:
- SQL verification:
- Screenshots or links:

## 12. Known gaps and decisions
- ...

## 13. Exit gate
[Acceptance criteria copied from this guide.]

## 14. Status
Not started / In progress / Blocked / Verified / Merged / Deferred / Released

## 15. Next subfeature
[Next item in strict roadmap order.]
```

### 4.5 Evidence rules

Record actual values, not expected values.

Weak evidence:
- "Notebook successfully tested."
- "Pipeline completed."
- "All records loaded."

Useful evidence:
- Actual notebook run URL.
- Tested commit SHA.
- Actual source and output record counts.
- Actual excluded counts and reasons.
- Actual Delta version and run ID.
- Actual SQL verification result.
- Actual CI run and result.

## 5. Standard implementation workflow for every subfeature

Follow these stages in order. The same process applies whether you write the code yourself, ask ChatGPT to generate it or use Genie Code.

### Stage 1 — Resume and inspect

1. Confirm the exact `Fxx.y` and task IDs from the roadmap.
2. Confirm that it is the next eligible subfeature using `docs/progress.md`.
3. Inspect repository root, branch, commit and working-tree status.
4. Inspect existing code, notebooks, configuration, tests, schemas and relevant runtime metadata.
5. Inspect the Databricks Git folder and actual workspace capabilities if the subfeature uses Databricks.
6. Read the matching Notion child page if one exists.
7. Do not edit during the inspection stage.

Return the current state with evidence: `Not started`, `Partially implemented`, `Implemented but unverified`, `Verified already` or `Blocked`.

### Stage 2 — Confirm scope and contracts

Prepare:
- Exact feature/subfeature title and task IDs.
- Objective and business/technical outcome.
- Included scope and explicit exclusions.
- Verified dependencies.
- Actual inputs, schemas, source versions and permissions.
- Expected outputs, data grain, locations and contracts.
- Acceptance criteria copied from this guide.
- Risks: data loss, overwrite, privacy, licensing, permissions, external services and cost.

If source schemas, permissions or requirements are unknown, identify what must be inspected or supplied. Do not invent them.

### Stage 3 — Prepare the file plan

Classify each relevant path:

| Action | Meaning |
|---|---|
| Reuse | Existing file is suitable; no duplicate is needed |
| Modify | Existing file needs a scoped change |
| Create | No suitable file exists and a new file is justified |
| Retire | Existing file should be removed or replaced; explain and obtain approval before destructive changes |

Do not create speculative empty folders, duplicate helpers or future-feature scaffolding without a current requirement.

### Stage 4 — Plan the implementation

Provide a task-by-task plan with:
- Exact UI navigation or execution surface.
- Exact files/notebooks/SQL objects.
- Code changes and design rationale.
- Test fixtures and test cases.
- Runtime verification.
- Expected outputs and evidence.
- Risks and rollback/recovery approach.

Wait for approval before implementation when the plan introduces a material architecture/scope change, destructive write, live-data overwrite, paid service, public release or external side effect.

### Stage 5 — Implement one task increment at a time

- Implement only the approved subfeature.
- Preserve verified work and unrelated user changes.
- Follow actual repository conventions.
- Produce complete, consistent files when multiple related files change.
- Keep configuration outside business logic.
- Add/update tests with the code.
- Keep SQL parameterized or safely validated.
- Keep LLM tools read-only, typed, allowlisted and bounded.
- Treat prompts and retrieved documents as untrusted input.
- Preserve source provenance and auditable exclusions.

If the required workspace capability is unavailable, stop at the smallest useful boundary and report the blocker. Do not simulate success.

### Stage 6 — Test in increasing scope

1. Static checks and syntax/import validation.
2. Focused unit tests.
3. Contract/schema tests.
4. Relevant integration tests.
5. Actual Databricks notebook/SQL/runtime checks, when required.
6. Relevant full test suite and CI checks.

For each test, record the exact command or UI action, actual result, failure output and environment. Distinguish local, CI and Databricks runtime evidence.

### Stage 7 — Runtime verification

For Databricks work:
- Run in the actual target workspace.
- Confirm actual catalog/schema/Volume and compute.
- Use an isolated test destination first.
- Verify schema, row counts and key constraints.
- Test same-input rerun and failure/recovery where relevant.
- Record Delta version and run ID where relevant.
- Verify test operations did not overwrite live data.

A local Spark mock or local unit test does not prove Databricks runtime success.

### Stage 8 — Git review and synchronization

1. Show the changed-file list and purpose.
2. Review the diff for secrets, private data, unrelated changes and generated files.
3. Run `git diff --check` or the equivalent review in the Databricks Git changes UI.
4. Rerun relevant tests after final edits.
5. Prepare a commit message using the feature ID.
6. Commit and push only through the approved Git workflow.
7. Report the actual branch, commit SHA and PR URL if available.

Do not claim a push, merge or PR if it has not been confirmed.

### Stage 9 — Update Notion and progress

Produce copy-ready Notion child-page content containing objective, scope, dependencies, contracts, file plan, completed task IDs, tests, runtime evidence, commit/PR, known gaps and status.

Update `docs/progress.md` only with verified facts. Keep it concise and consistent with Notion.

### Stage 10 — Stop and hand off

Stop after the current subfeature exit gate. Report:
- Status.
- Completed task IDs.
- Acceptance criteria pass/fail/not-verified.
- Changed files.
- Tests and actual results.
- Runtime evidence.
- Remaining gaps.
- Latest commit and PR.
- Next subfeature ID and title.

Do not automatically start the next subfeature.

## 6. Implementing with ChatGPT

### 6.1 Step-by-step learning mode

Use this when you want to write and run the code yourself:

1. Ask ChatGPT to inspect and plan the selected subfeature.
2. Approve the plan.
3. Ask for one actionable step at a time.
4. For each step, request exact browser navigation, file path, complete code, where to paste it, how to run it and expected output.
5. Run the step and share the actual output/error.
6. Continue only after the current step is understood and verified.

ChatGPT should not assume it can see your Databricks workspace, GitHub repository or Notion pages unless you have connected or supplied the relevant context. Provide the actual file, screenshot, schema, error or result when required.

### 6.2 Code-generation mode

When asking ChatGPT to generate code:
- Supply the current file contents or allow it to inspect the repository through an available connected tool.
- Ask for exact paths and a reuse/modify/create/retire manifest.
- Request complete, consistent file contents or a precise patch.
- Include tests and commands.
- Ask it to explain how to apply the changes through the Databricks Git folder or another named environment.
- Do not accept invented paths, schemas or assumptions about existing code.

## 7. Genie Code workflow in Databricks browser

This protocol targets Genie Code inside the Databricks browser workspace, not a separate terminal-native Genie Code CLI.

### 7.1 Operating limits

Genie Code may be able to inspect and edit supported workspace files, notebooks and SQL, explore Unity Catalog metadata and run bounded workspace operations. Actual capabilities depend on workspace configuration, permissions and the current surface.

Do not assume it has unrestricted access to:
- the computer's local filesystem;
- arbitrary terminal commands;
- GitHub account settings;
- Notion workspace;
- external APIs or websites;
- every Databricks feature.

If the repository is not open as the correct Git folder, the branch is unclear or required workspace capabilities are unavailable, stop and ask the user to establish the correct context.

### 7.2 Genie Code execution stages

Use this exact sequence for each subfeature:

**A — Inspect only**
- Read Project Plan v29, this guide and `docs/progress.md`.
- Inspect repository, branch, commit, working tree, files, tests, schemas and workspace capabilities.
- Do not edit or perform write operations.

**B — Assess**
- Classify the subfeature as not started, partially implemented, implemented but unverified, verified already or blocked.
- Provide evidence and identify existing code to reuse.

**C — Propose**
- List task IDs, objective, scope, exclusions, dependencies, inputs/outputs, file plan, tests, runtime checks, risks and exit gate.
- Wait for approval for material changes or risky operations.

**D — Implement**
- Change only the approved subfeature.
- Preserve existing work.
- Add tests.
- Do not add dependencies, write to live data, publish data or invoke paid services without approval.

**E — Test**
- Run static, unit, contract and integration tests as appropriate.
- Report exact commands/actions and actual results.

**F — Verify in Databricks**
- Use the actual target workspace.
- Verify catalog/schema/Volume, isolated test writes, schema, counts, keys, reruns and recovery where relevant.
- Do not present local tests as runtime proof.

**G — Review Git**
- Show changed files and diff.
- Check for secrets, unrelated edits and missing tests.
- Prepare commit details; only claim commit/push after confirmation.

**H — Update records**
- Produce copy-ready Notion update.
- Update `docs/progress.md` only with facts supported by evidence.

**I — Stop**
- Report exit status and next roadmap item.
- Do not start the next subfeature automatically.

### 7.3 Genie Code prompt — inspect and plan only

Copy this into Genie Code and replace the bracketed fields:

```text
You are working on TripPilot using Project Plan v29 and Unified Build Guide v30.

Current roadmap item:
[Fxx.y — exact subfeature title]

Parent feature:
[Fxx — exact feature title]

Follow the strict F01–F31 order and ascending subfeature order.
Work on this subfeature only.

PHASE 1 — INSPECT ONLY. Do not edit files or execute write operations.

Inspect the actual Databricks Git folder/repository, branch, working tree,
current commit, relevant files, tests, docs/progress.md and actual workspace
capabilities. Use exact task IDs and acceptance criteria from the Unified
Build Guide v30.

Determine whether this subfeature is:
Not started / Partially implemented / Implemented but unverified /
Verified already / Blocked.

Return:
1. Current state and evidence.
2. Existing code that should be reused.
3. Exact task IDs.
4. Inputs and outputs.
5. Files to reuse, modify, create or retire.
6. Tests and runtime checks required.
7. Risks and capability blockers.
8. A step-by-step implementation plan.

Do not edit files yet. Wait for my approval.
```

### 7.4 Genie Code prompt — implement after approval

```text
I approve the implementation plan for [Fxx.y].

Implement only the approved scope in the current TripPilot Git folder.

Requirements:
- Preserve existing verified work and unrelated user changes.
- Follow the actual repository structure and naming conventions.
- Complete the existing Fxx.y-Tnn task IDs.
- Add or update tests with the code.
- Do not invent source schemas, workspace permissions or runtime results.
- Use an isolated test destination for data writes.
- Do not overwrite live tables or perform destructive operations.
- Do not add paid services or publish data without asking.
- Keep secrets and raw datasets out of Git.

After implementation:
1. Show all changed files and explain their purpose.
2. Run focused tests and relevant broader tests.
3. Perform required actual Databricks/runtime verification.
4. Report exact results and failures.
5. Review the Git diff.
6. Prepare commit/PR details; do not claim success without confirmation.
7. Produce copy-ready Notion child-page updates.
8. Update docs/progress.md only with verified facts.
9. State remaining gaps and the next roadmap item.

Do not mark the subfeature Verified without full exit evidence.
Stop after this subfeature.
```

### 7.5 Genie Code debugging prompt

```text
Debug the following TripPilot failure without expanding scope.

Feature/subfeature/task:
[Fxx.y / Fxx.y-Tnn]

Exact error:
[Paste sanitized error]

Environment:
[Databricks notebook / SQL Editor / Git folder / CI / other]

Relevant file or notebook:
[Path]

Expected result:
[Expected]

Actual result:
[Actual]

First isolate the failure. Inspect the relevant code, configuration, schema
and runtime context. Identify the root cause before changing code.

Propose the smallest fix. Explain affected files and regression tests.
Do not remove validation, suppress exceptions, weaken acceptance criteria
or claim success without rerunning the failing test.
```

### 7.6 Genie Code review prompt

```text
Review the current implementation of [Fxx.y] against the exact acceptance
criteria in Unified Build Guide v30.

Do not make changes yet.

Check:
- Task completeness and scope control.
- Code quality and maintainability.
- Source provenance and licence handling.
- Schema and data quality controls.
- Idempotency and failure recovery.
- Security and secrets.
- Test coverage and actual results.
- Databricks runtime evidence.
- Git diff and unrelated edits.
- Notion and docs/progress.md evidence.
- Portability across computers through the same GitHub remote/Git folder.

Return a criterion-by-criterion PASS / FAIL / NOT VERIFIED table.
Explain every NOT VERIFIED item. Do not infer success from code existence.
```

## 8. Standard prompts for working with ChatGPT

### 8.1 Start a new feature or subfeature

```text
We are starting TripPilot subfeature [Fxx.y — exact title], under parent
feature [Fxx — exact title].

Use trippilot-project-plan-v29.md, this Unified Build Guide v30 and the
current docs/progress.md as the project sources.

Keep Databricks browser UI as a core development environment because I may
switch computers. GitHub is the durable source-control anchor. Local tools
are optional unless this subfeature genuinely requires them.

Do not start coding yet. First:
1. Confirm the exact subfeature title, task IDs, dependencies and acceptance
   criteria from this guide.
2. Confirm it is the next eligible item using docs/progress.md.
3. Inspect actual repository files, branch, commit, working-tree state,
   existing implementation and tests. Reuse verified work.
4. Identify the Databricks browser pages/tools needed: Git folder, Workspace,
   Catalog Explorer, notebook, SQL Editor, compute or Genie Code.
5. Identify actual workspace capabilities and permissions. Do not assume
   Unity Catalog, Volumes, compute, network access or AI features.
6. Explain the subfeature in plain English and why it exists.
7. Prepare a practical plan covering scope, dependencies, contracts, task
   sequence, file plan, UI steps, code changes, tests, runtime verification,
   expected evidence and risks.
8. Tell me exactly what I need to open, click, provide or confirm.

Do not invent repository paths, schemas, permissions or test results.
Do not create new subfeature IDs unless independently justified; explain
and ask before changing the decomposition.
Wait for my approval before implementation.
```

### 8.2 Implement with me one step at a time

```text
I approve the plan for [Fxx.y]. Guide me through implementation one step
at a time. Keep Databricks browser UI central and assume I may switch
computers.

For each step:
1. Tell me exactly which browser page or tool to open.
2. Give the navigation path and menu/button names. If labels may vary,
   explain what to look for.
3. Tell me which existing file/notebook to inspect or which file to create.
4. Provide complete code for that step, not disconnected fragments unless
   the change is intentionally small.
5. Explain the code and important design decisions in plain English.
6. Tell me exactly where to paste or edit it.
7. Tell me how to run it and what output I should expect.
8. Tell me how to verify success and what evidence to capture.
9. Explain likely errors and the next diagnostic action.

Give me one actionable step and wait for me to report what I see before
continuing. Preserve existing work and the approved scope.
```

### 8.3 Generate code or implementation files

```text
For approved subfeature [Fxx.y], generate the implementation changes.

Before generating:
- Reconfirm the actual repository tree and current versions of relevant files.
- Identify exact paths and classify each as reuse, modify, create or retire.
- Check the subfeature contract, task IDs and acceptance criteria.

Then provide complete, internally consistent file contents or a precise
patch. Include targeted tests and required configuration/schema changes.
Explain where each file belongs and how to apply it through the Databricks
browser Git folder or another explicitly identified tool.

Do not assume existing file contents. If you need a file or schema that I
have not supplied, ask me to provide it. Do not implement unrelated features.
```

### 8.4 Resume after switching computers

```text
We are resuming TripPilot after switching computers.

Current subfeature: [Fxx.y — exact title]
Last known branch: [branch or unknown]
Last known commit: [SHA or unknown]
Last recorded task: [Fxx.y-Tnn or unknown]

Use Project Plan v29, Unified Build Guide v30, docs/progress.md and the
matching Notion child page if available. Keep Databricks browser UI central.

First do a resume check only:
1. Confirm which project files and prior decisions are available.
2. Ask me to open the Databricks workspace and existing TripPilot Git folder
   if you cannot inspect them directly.
3. Verify remote repository, branch, latest commit and working-tree state.
4. Identify uncommitted or workspace-only changes that may not have moved.
5. Compare actual code and progress record with the last session note.
6. Tell me the single safest next action.

Do not recreate work or assume previous-computer local files are available.
Do not edit until the current state is understood.
```

### 8.5 Debug with ChatGPT

```text
I am debugging [Fxx.y — exact title], task [Fxx.y-Tnn].

Environment:
- Databricks workspace/edition:
- Git branch and commit:
- Catalog/schema/Volume, if relevant:
- Where the error occurred:
- Exact error and relevant sanitized output:

Please:
1. Explain the likely cause in plain English.
2. Separate confirmed facts from hypotheses.
3. Identify the smallest diagnostic check.
4. Give exact UI navigation or command.
5. Explain expected results for possible outcomes.
6. Recommend the smallest safe fix.
7. Tell me which tests and runtime checks must be repeated.

Do not rewrite the entire feature or change architecture to work around
an error without explaining the trade-off. Do not ask me to expose secrets.
```

### 8.6 Review before commit

```text
Review the implementation for [Fxx.y].

Compare changed files against this guide's scope and acceptance criteria,
the approved implementation plan, existing project conventions, tests and
actual runtime evidence.

Check for:
1. Out-of-scope changes or duplicate implementations.
2. Incorrect assumptions about schemas, data grain or source coverage.
3. Missing validation, error handling, idempotency or recovery behaviour.
4. Security, secrets, privacy and licensing problems.
5. Missing or weak tests.
6. Claims that exceed the evidence.
7. Portability through the Databricks Git folder and GitHub workflow.

Return a prioritized review. Do not claim the feature is verified unless
required tests and runtime checks have actually passed.
```

### 8.7 Close out a subfeature

```text
Prepare the close-out for TripPilot subfeature [Fxx.y].

Use only actual evidence from this session and supplied outputs. Do not
invent successful tests, commit SHAs, PR links, runtime results or counts.

Produce:
1. Task-by-task status using existing task IDs.
2. Changed files and purpose.
3. Test commands/UI actions and actual results.
4. Databricks runtime evidence, distinguished from local/CI tests.
5. Acceptance-criteria checklist: PASS / FAIL / NOT VERIFIED.
6. Remaining gaps, blockers and decisions.
7. Copy-ready Notion child-page update.
8. Exact docs/progress.md update.
9. Suggested commit message and GitHub handoff status.
10. Next roadmap subfeature, but do not start it.

Include cross-computer handoff:
- remote repository and branch
- latest commit SHA
- Databricks workspace and Git folder
- uncommitted files, if any
- exact next action
```

## 9. Troubleshooting procedure

When something fails, do not immediately rewrite the code. Record:

```text
Feature/subfeature/task:
Git branch and commit:
Databricks workspace/runtime:
Notebook or file:
Exact error:
Steps to reproduce:
Expected result:
Actual result:
Last successful run:
```

Then:
1. Identify whether the error is local, Git, configuration, permissions, source, compute, schema or code related.
2. Reproduce the smallest failing step.
3. Read the full error and relevant logs.
4. Check whether the workspace capability is supported.
5. Make the smallest scoped fix.
6. Rerun the failing test.
7. Rerun relevant regression tests.
8. Record the fix and evidence.

Never paste credentials or private source data into a troubleshooting prompt.

## 10. Free Edition, workspace and agent cost guardrails

Databricks Free Edition can be suitable for learning and bounded portfolio development, but it has serverless-only compute, fair-use quotas and feature/permission limits. Verify current capabilities in the actual workspace before designing a feature around them. Do not assume large batches, outbound downloads, model endpoints, vector search or advanced deployment features will work.

Keep source data and code backed up outside the workspace. Use bounded data samples and batches. If a quota or permission warning appears, stop and reassess rather than repeatedly retrying.

Genie Code may have usage/pricing considerations separate from general workspace access. Before extensive agent use:
- Check the current Genie Code allowance and pricing shown in your account.
- Avoid repeated autonomous runs on broad prompts.
- Ask for an inspection/plan before implementation.
- Keep each prompt scoped to one subfeature.
- Use small fixtures and bounded notebook runs.
- Stop if the workspace reports quota, cost or permission warnings.

Never authorize an agent to perform destructive operations or publish data without explicit approval.

## 11. Review and completion report template

Use this at the end of each approved subfeature:

```markdown
# Implementation report — Fxx.y

## Status
Not started / In progress / Blocked / Verified / Merged / Deferred / Released

## Tasks
- [x] Fxx.y-T01
- [ ] Fxx.y-T02

## Changed files
| File | Action | Purpose |
|---|---|---|

## Tests
| Test | Environment | Actual result |
|---|---|---|

## Databricks verification
- Workspace:
- Notebook/job:
- Catalog/schema:
- Table/version:
- Run ID:
- Result:

## Git
- Branch:
- Commit:
- Pull request:

## Acceptance criteria
| Criterion | PASS / FAIL / NOT VERIFIED | Evidence |
|---|---|---|

## Known gaps
-

## Notion update
[Copy-ready child-page content]

## Progress update
[Concise docs/progress.md entry]

## Next roadmap item
[Exact next subfeature ID and title]
```

## 12. F01 and F02 restart examples

These are worked examples from the prior human implementation guide. They demonstrate how to begin from the foundation without assuming that every later feature needs the same files or code. Always inspect the repository before applying an example.

### 12.1 F01 — repository and configuration foundation

**F01.1 — Repository baseline and architecture**

- Inspect the repository tree and existing project files.
- Confirm the agreed top-level layout against Project Plan v29.
- Create only missing files/directories needed for the current baseline.
- Add README, project metadata, `.gitignore`, configuration examples and `docs/progress.md` only if missing.
- Keep credentials, API keys, tokens and raw source datasets out of Git.
- Record the initial branch and commit.

**F01.2 — Environment, city and source configuration**

Example file: `config/project.yml`

```yaml
project:
  name: trippilot
  environment: dev
  timezone: UTC

databricks:
  catalog: <actual_catalog>
  schema: <actual_schema>
  volume: <actual_volume>
```

Replace placeholders only after inspecting the actual workspace. Do not commit passwords, API keys or tokens.

Example city registry: `config/cities/cities.yml`

```yaml
cities:
  - city_id: toronto_ca
    name: Toronto
    country: Canada
    timezone: America/Toronto
    currency: CAD
    enabled: true
```

This is an example record, not a claim that the source is available for Toronto. Source eligibility must be checked independently.

Example source registry: `config/sources/sources.yml`

```yaml
sources:
  inside_airbnb:
    source_family: accommodation
    source_url: https://insideairbnb.com/get-the-data/
    licence: CC BY 4.0
    enabled: true

  overture:
    source_family: places
    enabled: true

  gtfs:
    source_family: transit
    enabled: true

  open_meteo:
    source_family: weather
    enabled: true

  official_documents:
    source_family: destination_knowledge
    enabled: true
```

Before actual ingestion, register the specific release, file, feed or document, source date, licence and attribution details. A family-level registry entry is not a substitute for file-level provenance.

Basic YAML validation example, if the project does not already use a configuration library:

```python
from pathlib import Path
import yaml

PROJECT_CONFIG = Path("config/project.yml")
CITY_CONFIG = Path("config/cities/cities.yml")
SOURCE_CONFIG = Path("config/sources/sources.yml")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    return data


def validate_project_config() -> None:
    project = load_yaml(PROJECT_CONFIG)
    cities = load_yaml(CITY_CONFIG)
    sources = load_yaml(SOURCE_CONFIG)

    assert project.get("project", {}).get("name") == "trippilot"
    assert cities.get("cities")
    assert sources.get("sources")


if __name__ == "__main__":
    validate_project_config()
    print("Configuration validation passed.")
```

Reuse an existing configuration library if present. Add tests for missing files, malformed YAML and missing required keys.

**F01.3 — Shared contracts and engineering conventions**

Example only: `src/common/contracts.py`

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SourceFileRecord:
    source_family: str
    source_id: str
    city_id: str | None
    source_version: str
    source_url: str
    file_hash: str
    file_size_bytes: int
    schema_version: str
    retrieved_at: datetime
    licence: str
    run_id: str
```

Add validation for non-empty identifiers, positive file size, valid timestamps and hash format before using this as an ingestion contract.

Do not add every future service, AI or MCP contract now. Build only shared contracts that the upcoming source ingestion actually needs.

### 12.2 F02 — Databricks migration verification runbook

F02 is not simply a notebook creation exercise. It verifies that the existing migration works safely in the actual workspace.

**F02.1 — Migration preflight**
1. Open the TripPilot Git folder in Databricks.
2. Switch to the agreed migration branch.
3. Inspect existing notebook and Python files.
4. Open the notebook and confirm the available serverless compute option.
5. Run import/configuration cells first.
6. Open Catalog and inspect actual catalog/schema permissions.
7. Record workspace runtime and target paths.
8. Run local lint and unit tests before writing any tables.
9. Create a separate test schema only if permitted and agreed.

**F02.2 — Isolated execution and recovery**

Use a small representative source fixture first.

```python
from pyspark.sql import functions as F

sample = spark.createDataFrame(
    [
        (101, "Toronto"),
        (102, "Vancouver"),
    ],
    ["listing_id", "city"]
)

result = sample.withColumn(
    "processed_at",
    F.current_timestamp()
)

display(result)
```

This checks that the notebook can execute PySpark. It does not verify the production ingestion pipeline.

For the real migration, test:
- Initial isolated write.
- Same-source rerun.
- New source snapshot.
- Invalid input.
- Interrupted/failed execution.
- Recovery without corrupting the previous successful result.

**F02.3 — Reconciliation**

Use SQL Editor to inspect:
- Source and output row counts.
- Duplicate keys.
- Null key counts.
- Accepted/excluded counts.
- Delta table versions.
- Run IDs and source hashes.

Do not mark F02 verified until the actual migration acceptance criteria in the roadmap above are satisfied.

## 13. Final project-wide guardrails

- F01 through F31 remain in strict order unless a documented dependency decision is explicitly approved.
- Subfeatures remain in ascending order.
- Task IDs are not silently renumbered.
- Existing code is inspected before implementation; verified work is reused.
- No duplicate city-specific notebooks or services.
- Bronze is source-faithful; Silver is normalized and validated; Gold is application-oriented.
- Structured queries do not get replaced by RAG.
- Vector search is for suitable unstructured content, not every structured row.
- LLM tools are read-only, typed, allowlisted and bounded.
- Source licences, provenance and attribution are respected.
- Tests, CI and runtime evidence must be real.
- No secrets or raw datasets in Git.
- No unsupported claims of live availability, booking, live arrivals or current event status.
- No feature is complete merely because generated code exists.

## 14. Official Databricks references

The original operational guide referenced these official documentation entry points. Check current documentation and the actual workspace UI because product labels and Free Edition capabilities can change:

- https://docs.databricks.com/aws/en/getting-started/free-edition
- https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- https://docs.databricks.com/aws/en/workspace/workspace-browser/
- https://docs.databricks.com/aws/en/repos/git-operations-with-repos/
- https://docs.databricks.com/aws/en/genie-code

---

**End of Unified Build Guide v30.** Use this file as the day-to-day implementation manual. Keep Project Plan v29 as its architecture companion and `docs/progress.md` as the record of actual implementation evidence.
