# TripPilot --- Unified Build Guide

**Version:** 32.0\
**Revised:** November 24, 2026\
**Architecture companion:** `trippilot-project-plan-v32.md`\
**Purpose:** one reusable manual for planning, implementing, testing,
verifying and handing off every TripPilot feature and subfeature.\
**Operating constraint:** required workflows use Databricks Free
Edition, open-source/local tooling and free-tier resources. Paid
services are never required for acceptance.

------------------------------------------------------------------------

## 1. Document role and source-of-truth rules

This is the operational implementation guide. It defines the
feature/subfeature/task hierarchy, implementation workflow, engineering
standards, test strategy, AI-agent prompts, review rules and completion
evidence.

Use it when: - planning a feature or subfeature; - implementing manually
with ChatGPT guidance; - using an AI coding agent in a
repository/workspace context; - debugging, reviewing or testing
changes; - switching computers or resuming work; - preparing a feature
handoff or release.

### 1.1 Source-of-truth hierarchy

1.  `trippilot-project-plan-v32.md` --- product purpose, scope,
    architecture, technology choices and system boundaries.
2.  This guide --- feature/subfeature/task IDs, dependencies,
    implementation standards and acceptance criteria.
3.  `docs/progress.md` --- actual implementation status and evidence.
4.  Current repository files, tests, Git history, Databricks workspace
    metadata and runtime outputs --- evidence of current reality.
5.  Notion pages --- optional working notes and evidence links; they
    must agree with the documents and repository.

If sources conflict, identify the conflict and its impact. Do not
silently overwrite one source with another. Code or documentation alone
does not prove runtime success.

### 1.2 Document separation

-   Project Plan describes the intended product and architecture.
-   Build Guide describes how to implement and verify it.
-   `docs/progress.md` records actual progress, tested commits, runtime
    evidence, blockers and the next action.
-   Notion is optional and may hold a feature parent page with
    subfeature child pages.

This guide does not record historical completion claims or a current
next feature. At the beginning of any work session, inspect the separate
progress record and repository.

## 2. Quick start and normal workflow

For every subfeature:

1.  Read the matching Project Plan section and this guide's subfeature
    specification.
2.  Inspect `docs/progress.md`, Git status, branch, latest commit,
    repository files and tests.
3.  Confirm the Databricks workspace, run mode, catalog, schema, Volume
    and compute actually available.
4.  Write a one-subfeature implementation plan with dependencies,
    contracts, file changes, tests and acceptance criteria.
5.  Wait for user approval before destructive operations, canonical data
    replacement, force reloads, schema/table deletion, source rights
    assumptions or costly external calls.
6.  Implement one task increment at a time; reuse working modules and
    conventions.
7.  Run local unit/contract checks, then isolated Databricks
    test-catalog validation where required.
8.  Review evidence and obtain explicit approval before any
    canonical/live write or promotion.
9.  Review diff, commit and push the approved change; update
    `docs/progress.md` with actual evidence.
10. Stop after the subfeature close-out. Do not begin the next
    subfeature automatically.

### 2.1 Working modes

  -----------------------------------------------------------------------
  Mode                                Appropriate use
  ----------------------------------- -----------------------------------
  ChatGPT guided implementation       Learn a concept, plan a small
                                      change, understand code or execute
                                      a browser workflow step by step

  AI coding agent                     Multi-file implementation, tests,
                                      refactoring and repository-wide
                                      inspection with a controlled scope

  Databricks browser workspace        PySpark, Spark SQL, Delta,
                                      catalog/schema inspection and
                                      runtime validation

  Local development                   dbt Core/MetricFlow, Chroma,
                                      Sentence Transformers, Streamlit,
                                      Ollama, local tests and document
                                      processing

  GitHub                              Durable source control, review, CI
                                      and handoff
  -----------------------------------------------------------------------

### 2.2 Status vocabulary

Use consistent status values in the separate progress record: -
`Not started` - `In progress` - `Blocked` -
`Implemented but unverified` - `Verified` - `Merged` - `Deferred` -
`Released`

A subfeature is not Verified merely because code exists. Required tests,
runtime checks and evidence must pass.

## 3. Free-tier and resource guardrails

### 3.1 Databricks Free Edition

Databricks Free Edition is no-cost but quota-limited, serverless-only
and intended for non-commercial personal use. It has no SLA or
guaranteed support. Current documented constraints include limited
serverless notebook usage, one SQL warehouse up to 2X-Small, a maximum
of five concurrent job tasks, restricted outbound internet, limited
active pipelines and limits on Apps and AI endpoints. Quota exhaustion
may temporarily stop compute. Features and limits can change; verify
current documentation and the workspace before designing a feature
around a capability.

Operating rules: - Do not require classic clusters, custom compute or
paid SQL warehouses. - Use serverless notebook compute and the available
SQL warehouse only where needed. - Keep jobs sequential or in small
bounded batches; avoid high concurrency. - Avoid full-city backfills
during iterative development. - Use local fixtures for rapid unit tests
and a small but representative test-catalog slice for runtime tests. -
Reserve full relevant-source validation for explicit acceptance runs. -
Download external files locally if restricted outbound internet blocks
Databricks acquisition, then upload through a supported path. - Treat
Databricks Apps and managed AI endpoints as optional, not required. -
Keep GitHub as the durable source of code and local backups for
reproducible raw files where permitted.

Official reference:
https://docs.databricks.com/aws/en/getting-started/free-edition-limitations

### 3.2 Current catalog and schema contract

The project uses physically separate catalogs, not `_test` table
suffixes.

  -------------------------------------------------------------------------
  Run mode           Catalog            Schemas           Use
  ------------------ ------------------ ----------------- -----------------
  Canonical          `trippilot_dev`    `bronze`,         Canonical
  development/live                      `silver`, `gold`, development data
                                        `ops`             and operational
                                                          records; not a
                                                          production SLA
                                                          environment

  Isolated test      `trippilot_test`   `bronze`,         Test data and
                                        `silver`, `ops`   test operational
                                                          records,
                                                          physically
                                                          separated from
                                                          development
  -------------------------------------------------------------------------

Rules: - Resolve destinations through the shared environment resolver. -
Do not hard-code catalog names in transformation logic. - Do not append
`_test` to table names as a substitute for catalog isolation. - The test
Gold schema is not assumed to exist. Add it only through an approved
schema/configuration change when a test requires Gold output. - The
current `config/project.yml` declares a source Volume under
`trippilot_dev/bronze/source_files`. Validate actual path access before
using it; never infer that the same Volume path exists in the test
catalog. - Before every write, print or inspect the resolved
catalog/schema/table and confirm the run mode. - Canonical/live writes,
force reloads, destructive DDL and cleanup require explicit approval and
a recovery plan.

### 3.3 No mandatory paid services

-   dbt Core and local MetricFlow; no dbt Cloud.
-   Chroma local persistent mode; no Chroma Cloud.
-   Sentence Transformers local embeddings; no paid embedding API.
-   Ollama local LLM as default; optional free-tier API adapter only if
    its terms and quotas are acceptable.
-   Streamlit local execution as the required application path.
-   Local MCP server/client for interoperability tests.
-   GitHub free-tier capabilities where available; no paid CI runner
    dependency.

Never commit API keys, tokens, local model weights, large source
archives or private user documents to Git.

## 4. Repository, configuration and coding standards

### 4.1 Inspect before creating

Before proposing paths, inspect the repository tree, `pyproject.toml`,
configuration, contracts, source modules, tests, notebooks and docs.
Reuse existing patterns. Do not create a duplicate framework or rename a
working module without a migration plan.

### 4.2 Configuration rules

-   YAML for declarative project, city, source and contract
    configuration.
-   Environment variables or supported secret storage for credentials.
-   No secrets in YAML, notebooks, logs, prompts or commits.
-   Stable `city_id` is distinct from display name and slug.
-   Source identity is distinct from a file path.
-   Environment/catalog resolution is centralized.
-   Validate configuration at startup and in CI.

### 4.3 Python standards

-   Type hints for public functions and service contracts.
-   Small functions with explicit inputs/outputs.
-   Structured exceptions and actionable error messages.
-   Decimal or explicitly documented numeric handling for prices/money.
-   UTC timestamps for event/provenance metadata; preserve source
    timezone where semantically relevant.
-   Deterministic functions for business rules and transformations.
-   Logging must avoid secrets and unnecessary personal information.
-   Pin dependencies and document compatibility.

### 4.4 Naming and IDs

-   Feature: `F01` through `F29`.
-   Subfeature: `Fxx.y`.
-   Task: `Fxx.y-Tnn`.
-   Branch: `feature/Fxx-y-short-description` or repository-approved
    equivalent.
-   Tests should name the behaviour and expected result, not only the
    implementation function.

## 5. Source ingestion and manifest standards

### 5.1 Identity model

Every ingestion decision must be scoped by at least: - source
family/provider; - stable city ID; - dataset identity; - source
snapshot/version; - file type and source asset identity; - content hash
where bytes exist.

A city display name or path alone is not a stable identity.

### 5.2 Availability and ingestion are separate

Availability answers: did the publisher make this city/dataset asset
available? Ingestion answers: what happened when the system attempted to
acquire and load it?

Do not encode `not_published` as a failed ingestion. Require evidence
for a not-published state. Keep unknown, invalid, disabled, available,
pending, success and failed semantics distinct in their respective
contracts.

### 5.3 Idempotency and reload rules

-   Before loading, compare the registered source identity and manifest
    state.
-   Same identity and same content hash should be a no-op when already
    successfully loaded.
-   New snapshot or changed content should create a new auditable
    ingestion event and scoped replacement/append decision.
-   A new source snapshot for one city/dataset must not reload other
    city/datasets.
-   Full reload is explicit, scoped, logged and requires a
    recovery/validation plan.
-   Failed attempts must not be mistaken for successful ingestion.
-   Preserve prior source/run lineage when reprocessing.

### 5.4 Bronze rules

-   Preserve source values and file-level provenance.
-   Avoid business cleaning in Bronze.
-   Add technical metadata consistently.
-   Record parse/schema observations and row-level validation metadata
    where applicable.
-   Keep raw file identity immutable.
-   Reconcile input/output counts with a documented parser-aware method.

## 6. Medallion implementation standards

### 6.1 Bronze

Bronze is source-faithful and auditable. It must not silently normalize
business values or drop source records. Technical parsing metadata is
allowed. Preserve source file ID, city ID, dataset, snapshot, ingestion
run and source schema identity.

### 6.2 Silver

Silver is the standardized and quality-controlled analytical foundation.
Each model must define: - grain and primary key; - required/optional
fields and types; - standardization rules; - null and invalid-value
policy; - duplicate policy; - rejected/quarantine behavior and reason
codes; - city/snapshot lineage; - relationships and cross-file rules; -
data-quality tests and reconciliation expectations.

Do not discard invalid records without a reason and count. Do not infer
values silently. Keep source-derived values and transformed values
distinguishable when auditability requires it.

### 6.3 Gold

Gold is built with dbt Core and dbt-databricks for SQL-centric
analytical models. Define model grain, dimensions, measures, business
purpose, keys, incremental strategy, tests, documentation and expected
query patterns. Avoid creating many overlapping aggregates without a
user question or service use case.

### 6.4 dbt Core and MetricFlow without dbt Cloud

Required workflow: 1. Develop the dbt project locally in the repository.
2. Pin dbt Core, dbt-databricks, MetricFlow and Python versions in a
tested dependency set. 3. Configure a profile using a supported
Databricks SQL connection and a Free Edition-compatible SQL warehouse.
4. Run dbt parse/compile and targeted model builds locally. 5. Run dbt
tests and documentation generation locally. 6. Define semantic
models/metrics in YAML and validate them using local MetricFlow
commands. 7. Query metrics locally through MetricFlow CLI where the
installed versions support the selected Databricks adapter path. 8.
Compare generated metric SQL/results with trusted SQL fixtures and
expected values.

Important constraints: - dbt Cloud is not required. - The hosted dbt
Semantic Layer API and hosted integrations are not available in this
free/local design. - MetricFlow local CLI capabilities are not
equivalent to a managed downstream API. - MetricFlow compatibility must
be proven with a small adapter/runtime spike. Pin working versions; do
not upgrade dependencies casually. - MetricFlow documentation notes
limitations around dbt built-in functions/packages. Keep semantic model
SQL simple and verify the supported feature set. - If local MetricFlow
cannot execute against the selected Databricks Free Edition SQL
endpoint, keep semantic definitions and validation, and implement a
clearly documented Python service that executes approved
dbt-generated/maintained SQL. Do not claim the Python fallback is a
MetricFlow hosted API.

Official references: -
https://docs.getdbt.com/docs/build/metricflow-commands -
https://docs.getdbt.com/docs/build/about-metricflow -
https://docs.getdbt.com/docs/use-dbt-semantic-layer/sl-faqs

## 7. Semantic metric contract

Every published metric must document: - metric name and business
definition; - source Gold model and grain; - entity relationships; -
numerator/denominator or aggregation; - dimensions and supported time
dimensions; - default filters and exclusions; - currency and unit; -
snapshot/date interpretation; - null and duplicate treatment; - known
caveats and unsupported interpretations; - test query and expected
result.

Example metric definitions to consider: listing count, median observed
nightly price, entire-home listing share, average review score, review
count, neighbourhood listing count, calendar available-day share and new
listing count between snapshots. Do not publish until the metric has a
tested business definition.

## 8. Document processing and knowledge engineering standards

### 8.1 Source registration

Record canonical URL, publisher, city coverage, language, document type,
publication/update date, retrieval time, valid/event dates,
licence/terms decision, content hash, source status and review/expiry
policy.

### 8.2 Extraction

-   Support PDF and approved HTML pages.
-   Preserve page number, title, heading hierarchy, table context and
    source links where possible.
-   Detect scanned pages and use OCR only when needed.
-   Record extraction library/version and quality warnings.
-   Never silently treat failed extraction as an empty valid document.
-   Normalize whitespace and artifacts without destroying semantic
    structure.

### 8.3 Canonical records and chunking

Keep canonical extracted text and chunk records in a durable non-vector
source of truth (local files/structured records under an approved data
location). Each chunk should include stable chunk ID, document
ID/version, city, publisher, document type, page/section, heading path,
dates, URL, licence/status and text hash.

Prefer heading/section-aware chunks. Evaluate chunk size and overlap on
a labelled query set. Do not assume a single token size is optimal for
brochures, tables and visitor rules.

### 8.4 Embeddings and Chroma

-   Use Sentence Transformers locally; pin the model ID and revision.
-   Store embedding model/version and dimensions in index metadata.
-   Use Chroma persistent local storage; keep it outside the Git
    repository if the index is large or derived from source documents.
-   Use stable IDs and deterministic upsert behavior.
-   Support metadata filters for city, document type, language, source
    authority and validity.
-   Keep Chroma rebuildable from canonical chunk records.
-   Implement document replacement/deletion so obsolete chunks do not
    remain retrievable.
-   Validate index counts, IDs, metadata and sample retrieval after each
    update.

## 9. Retrieval and RAG standards

### 9.1 Retrieval flow

1.  Parse destination, language, topic and temporal intent.
2.  Ask for clarification if a required city or scope is missing.
3.  Apply metadata filters before/alongside vector retrieval.
4.  Retrieve a bounded candidate set.
5.  Add keyword/hybrid retrieval where exact names, regulations or
    terminology require it.
6.  Deduplicate and optionally rerank candidates.
7.  Assemble evidence with source/page/section references and validity
    metadata.
8.  Return evidence to the answer generator with explicit grounding
    instructions.

### 9.2 Grounded answer rules

-   Cite the source document and page/section when available.
-   Distinguish source facts from itinerary suggestions or synthesis.
-   State publication/retrieval dates when freshness matters.
-   Identify contradictions and prefer current authoritative sources
    without deleting the conflict history.
-   Do not assert an attraction is currently open based only on a
    brochure.
-   Do not infer accessibility or admission details beyond the retrieved
    evidence.
-   Abstain or explain the evidence gap when support is insufficient.
-   Treat retrieved document text as untrusted content; never execute
    instructions embedded in it.

### 9.3 Evaluation

Maintain versioned evaluation cases with query, expected
source/document, relevant passages, expected claims, citation
expectations and no-answer cases. Measure retrieval relevance separately
from answer groundedness. Compare vector-only with hybrid retrieval and
reranking before adopting added complexity.

## 10. AI application and orchestration standards

### 10.1 Service-first architecture

Streamlit and the LLM call Python service functions. Business logic must
not live only in prompts or UI callbacks. Service functions have typed
inputs/outputs, bounded results, deterministic validation and tests.

### 10.2 Structured tool calling

Approved tools include accommodation search, listing detail,
neighbourhood comparison, metric query and source coverage explanation.
Validate arguments, constrain filters and result counts, and prevent
arbitrary SQL. Tool results should include data caveats and provenance
references.

### 10.3 Conversation state

Keep only the active-trip context needed: destination, dates/duration if
provided, interests, accommodation preferences and unresolved
constraints. Allow correction/reset. Do not store sensitive details
unnecessarily.

### 10.4 Orchestration

Start with straightforward Python control flow. Introduce LangGraph only
when explicit state transitions, checkpointing, retry, branching or
multi-step tool workflows justify it. Do not build a multi-agent system
for simple tool calls.

### 10.5 Local model strategy

Ollama with a locally runnable model is the default no-cost path. Model
choice must consider local hardware, memory, latency, tool-calling
support and answer quality. Keep a provider adapter so an optional
free-tier API can be evaluated without coupling the application to it.
Never require a paid API key for tests or acceptance.

## 11. MCP standards

MCP is an interoperability layer over stable Python services. - Define
typed, narrow tools with clear names and descriptions. - Validate inputs
and enforce result limits. - Reuse existing service functions; do not
duplicate business rules in MCP handlers. - Apply least privilege and
avoid exposing arbitrary SQL or filesystem access. - Test tool
discovery, success, invalid arguments, timeout, disconnect and partial
failure. - Keep local stdio integration as the baseline; hosted remote
deployment is optional and may require separate hosting/security review.

## 12. Testing, CI and release evidence

### 12.1 Test layers

  --------------------------------------------------------------------------
  Layer                   Purpose                 Typical location
  ----------------------- ----------------------- --------------------------
  Unit                    Pure functions, parsing `tests/unit/`
                          helpers,                
                          transformations and     
                          service logic           

  Contract                YAML/config/schema and  `tests/contract/`
                          input/output contract   
                          checks                  

  Fixture integration     Multi-module behavior   `tests/integration/`
                          using small             
                          deterministic fixtures  

  Databricks test runtime Spark/Delta/catalog     Runtime notebooks/scripts
                          behavior in             and recorded evidence
                          `trippilot_test`        

  Canonical runtime       Approved canonical      Explicitly approved run
                          development execution   and verification evidence
                          in `trippilot_dev`      

  dbt                     Model build, tests,     dbt project test workflow
                          compile and docs        

  Semantic                Metric definition       Semantic evaluation
                          validation and result   fixtures
                          reconciliation          

  Retrieval               Relevant document/chunk `evals/retrieval/`
                          retrieval and filtering 

  RAG/AI                  Grounded answers,       `evals/rag/`,
                          citations, abstention,  `evals/tools/`,
                          tool selection and      `evals/conversations/`
                          context                 

  MCP                     Protocol and tool       `tests/integration/mcp/`
                          contract behavior       
  --------------------------------------------------------------------------

### 12.2 Promotion policy

Test-catalog runtime is the default for data write validation. A
successful test does not automatically authorize a canonical write.
Canonical writes, force reloads, table replacement, destructive DDL and
cleanup require explicit user approval, verified target resolution and a
recovery plan.

### 12.3 CI expectations

Use free GitHub Actions allowances. Run formatting, lint, unit tests,
contract/config validation, notebook validation, dbt parse/compile where
secrets are not required, and evaluation smoke tests with deterministic
fixtures. Runtime integration tests that require Databricks credentials
must use secure repository secrets only if available and should not
block all local development when the free workspace is unavailable;
report them as a separate evidence gate.

## 13. Feature/subfeature/task workflow

### 13.1 Work hierarchy

-   Feature = a coherent product or engineering outcome.
-   Subfeature = a reviewable implementation increment with its own
    contracts and exit gate.
-   Task = a concrete code, test, configuration, documentation or
    runtime action.

A feature may contain many subfeatures; a subfeature may contain
multiple tasks. Not every coding action needs a separate Notion page.

### 13.2 Recommended Notion hierarchy

-   Project page: TripPilot.
-   Feature parent page: Fxx --- exact feature title.
-   Subfeature child page: Fxx.y --- exact subfeature title.
-   Task checklist inside the subfeature page unless tasks have
    independent ownership/review requirements.

### 13.3 Subfeature specification template

``` markdown
# Fxx.y — Exact subfeature title

## Objective and learning outcomes
## User/system problem
## Included scope
## Exclusions
## Dependencies
## Input contracts
## Output contracts
## Data model and technical design
## Repository inspection findings
## File plan (reuse / modify / create / retire)
## Implementation tasks (Fxx.y-Tnn)
## Test plan and expected results
## Databricks/local runtime steps
## Security, cost and free-tier considerations
## Acceptance criteria
## Required evidence
## Risks, limitations and decisions
## Exit status
```

## 14. Standard implementation workflow

### Stage 1 --- Resume and inspect

-   Read Project Plan, this guide and `docs/progress.md`.
-   Check branch, commit, working tree and open changes.
-   Inspect existing modules, tests, configuration, schemas and runtime
    state.
-   Confirm actual Databricks workspace/catalog/schema/compute
    availability.
-   Identify reuse and gaps; do not assume documentation reflects
    current code.

### Stage 2 --- Confirm scope and contracts

-   State the exact feature/subfeature/task IDs.
-   Define included/excluded behavior.
-   Define input/output, data grain, keys, state transitions and error
    semantics.
-   Identify dependencies and resource limits.
-   Identify operations requiring explicit approval.

### Stage 3 --- Prepare file plan

Classify each proposed path as reuse, modify, create or retire. Explain
why each change is needed. Avoid unrelated refactoring.

### Stage 4 --- Plan tests before implementation

List unit, contract, integration, runtime, data-quality and evaluation
tests. Include positive, negative, boundary, duplicate, missing, stale
and failure cases where relevant.

### Stage 5 --- Implement incrementally

Implement one task at a time. Keep functions small, contracts explicit
and changes reviewable. Do not add a framework unless a concrete
requirement justifies it.

### Stage 6 --- Validate locally

Run targeted tests first, then the relevant full test suite, formatter,
linter, configuration and notebook validators. Record exact commands and
results.

### Stage 7 --- Validate external/runtime behavior

Use `trippilot_test` for isolated Databricks writes. For dbt/MetricFlow,
run local parse/compile/tests and a small supported query against the
configured SQL endpoint. For Chroma/RAG, verify persistence, IDs,
metadata filters and retrieval. For LLM/MCP, use deterministic mocked
tests before live local-model integration.

### Stage 8 --- Review and approval gates

Review diff, destination resolution, source rights, data quality,
resource consumption and recovery plan. Obtain explicit approval for
canonical writes, destructive operations, force reloads or optional
external API calls.

### Stage 9 --- Commit and evidence

Commit the tested change. Record branch, commit SHA, CI status, tests,
runtime destination, source identities, row counts, quality results,
evaluation outcomes and known gaps.

### Stage 10 --- Stop and hand off

Update `docs/progress.md` and optional Notion page. State one next
action. Do not start the next subfeature automatically.

## 15. AI coding-agent workflow

### 15.1 Agent inputs

Provide: - exact feature/subfeature/task IDs; - Project Plan and Build
Guide versions; - repository and branch context; - current progress
evidence; - allowed scope and prohibited operations; - test commands and
acceptance criteria.

### 15.2 Agent operating rules

1.  Inspect before editing.
2.  Report repository state and relevant existing patterns.
3.  Propose a file plan and implementation plan.
4.  Wait for approval before code changes when the task has material
    design choices or risky operations.
5.  Implement only approved scope.
6.  Run available tests and report unavailable checks honestly.
7.  Never fabricate Databricks runtime evidence, API results, evaluation
    scores or successful deployment.
8.  Do not perform canonical writes or destructive operations without
    explicit approval.
9.  Review the diff and summarize residual risks.

### 15.3 Prompt --- inspect and plan

``` text
We are working on TripPilot under Project Plan v32 and Unified Build Guide v32.
Target: [Fxx.y — exact title].
First inspect the repository, current branch/commit, progress record, relevant code,
configuration, contracts and tests. Do not edit files or run destructive operations.
Explain the current design, identify reuse and gaps, propose a file plan, task list,
input/output contracts, test plan, resource/free-tier considerations and acceptance
evidence. Flag any conflict with the two project documents. Wait for approval.
```

### 15.4 Prompt --- implement after approval

``` text
Implement only the approved scope for [Fxx.y]. Follow Project Plan v32 and
Unified Build Guide v32. Reuse existing patterns. Implement tasks in small increments,
add tests before or alongside code, and run the approved local checks. Do not perform
canonical Databricks writes, force reloads, destructive DDL, paid API calls or external
publishing. Report changed files, commands/results, unverified runtime checks, risks
and evidence needed for acceptance.
```

### 15.5 Prompt --- debug

``` text
Debug the reported failure for [Fxx.y]. Reproduce or inspect the failure first.
Trace the root cause through contracts, configuration, code and tests. Do not mask
errors or change unrelated behavior. Propose the smallest safe fix and regression test.
Do not write to canonical data or perform destructive operations without approval.
```

### 15.6 Prompt --- review

``` text
Review the implementation of [Fxx.y] against the exact v32 acceptance criteria.
Inspect the diff, tests, contracts, error paths, idempotency, data provenance, security,
free-tier assumptions and runtime evidence. Identify correctness defects and missing
tests. Do not modify files. Return findings by severity and a clear pass/block decision.
```

## 16. Standard ChatGPT prompts

### 16.1 Start a subfeature

``` text
Let's work on [Fxx.y — title] in TripPilot.
Use Project Plan v32 and Unified Build Guide v32 as the design baseline.
First inspect the repository and docs/progress.md. Explain the subfeature's purpose,
prerequisites, current implementation evidence, exact scope, contracts, tasks, file plan,
tests, Databricks/local steps and acceptance criteria. Do not assume current progress
or edit files before we agree on the implementation plan.
```

### 16.2 Learn while implementing

``` text
Guide me through [Fxx.y] one step at a time. Explain the engineering concept first,
why it is needed in TripPilot, then show the smallest implementation step. Wait for
my result before moving on. Keep the code aligned with the repository and v32 guide.
```

### 16.3 Generate or revise code

``` text
Implement the agreed task [Fxx.y-Tnn]. Inspect existing files and return complete
updated files when editing code. Explain the important design decisions, tests to run,
and any Databricks or local verification required. Do not invent paths or claim a test
passed unless it was executed.
```

### 16.4 Resume or switch computers

``` text
Help me resume TripPilot. Inspect the current Git branch/commit and working tree,
read docs/progress.md, compare it with Project Plan v32 and Build Guide v32, and inspect
the relevant code/tests. Confirm the exact subfeature/task and what is verified versus
unverified. Do not assume local files or Databricks state synchronized automatically.
```

### 16.5 Close a subfeature

``` text
Review [Fxx.y] against its v32 exit criteria. Summarize tasks, changed files, exact
commands and test results, Databricks test-catalog evidence, canonical-write approval
status, CI/commit details, limitations and outstanding risks. Draft the concise
progress.md update and identify one next action. Do not mark unverified work complete.
```

## 17. Troubleshooting procedure

1.  Capture the exact error, command/cell, timestamp and environment.
2.  Identify whether the failure is configuration, source acquisition,
    parsing, schema, Spark/Delta, permissions, quota, dbt/MetricFlow
    compatibility, document extraction, embedding, Chroma, model, tool
    or UI related.
3.  Reproduce with the smallest safe fixture or test-catalog slice.
4.  Inspect logs and state before retrying; do not repeat a write
    blindly.
5.  Check idempotency and manifest state before rerunning ingestion.
6.  Check catalog/schema resolution before Spark writes.
7.  Check pinned dependency versions before changing
    dbt/MetricFlow/adapter packages.
8.  For RAG, inspect source text, chunk metadata, embedding version,
    index IDs and retrieved candidates before changing prompts.
9.  Add a regression test for the root cause.
10. Record the fix and evidence; escalate if the failure requires a paid
    capability or unsupported Free Edition feature.

## 18. Completion report template

``` markdown
# Implementation report — Fxx.y

## Status
- Not started / In progress / Blocked / Implemented but unverified / Verified

## Tasks
- Fxx.y-Tnn: result

## Changed files
- Reused:
- Modified:
- Created:
- Retired:

## Tests
- Commands:
- Results:
- Failures/limitations:

## Runtime verification
- Workspace/catalog/schema:
- Test/live mode:
- Source identity/version:
- Counts/quality/reconciliation:
- Run ID/Delta version:

## AI/dbt evaluation (if applicable)
- Version/model/index:
- Evaluation dataset:
- Measured result:
- Known gaps:

## Git/CI
- Branch:
- Commit:
- CI:

## Acceptance criteria
- Passed:
- Not passed:

## Risks and next action
- One next action:
```

## 19. Project-wide definition of done

A subfeature can be marked Verified only when: - scope and dependencies
match the roadmap; - code/configuration/contracts are reviewed; -
relevant unit and contract tests pass; - required integration/runtime
checks pass in the correct environment; - data/source/metric/document
provenance is preserved; - idempotency, retry and failure behavior are
tested where relevant; - free-tier and cost assumptions are valid; -
security and privacy checks pass; - acceptance evidence is recorded with
the tested commit; - known limitations and next dependencies are
explicit.

A feature is complete only when all required subfeatures are Verified
and feature-level acceptance criteria pass.

------------------------------------------------------------------------

# Roadmap and implementation register

The following register defines the complete feature and subfeature
structure. Each subfeature is a separate reviewable unit. Task IDs are
created in the implementation plan for that subfeature using
`Fxx.y-Tnn`; task decomposition should be detailed enough to implement
and test, but should not create a separate task for every trivial code
edit.

# Part A --- Shared data engineering foundation

## F01 --- Project architecture and source registries

**Goal:** establish a reusable repository, configuration and source
identity foundation.

-   **F01.1 --- Repository architecture and module boundaries:** define
    source, transformation, service, app, test and documentation
    boundaries; document dependency direction and naming.
-   **F01.2 --- Environment, city and source configuration:** define
    stable city IDs, environment configuration, source provider/dataset
    identity and validated configuration loading.
-   **F01.3 --- Shared contracts and engineering conventions:**
    establish typed contracts, schema/config validation, logging,
    errors, time handling and coding conventions.

**Acceptance criteria:** configuration is validated; stable IDs are
independent of display names; source and environment responsibilities
are explicit; modules have clear boundaries; tests cover invalid
configuration and identity collisions.

## F02 --- Databricks lakehouse foundation

**Goal:** define and validate the Databricks Free Edition environment
and isolated catalog layout.

-   **F02.1 --- Workspace and Free Edition capability validation:**
    inspect workspace, serverless compute, SQL warehouse, outbound
    access, Volumes and quota constraints.
-   **F02.2 --- Catalog/schema and Delta conventions:** establish
    `trippilot_dev` and `trippilot_test` separation, approved schemas,
    table naming, Delta write and metadata conventions.
-   **F02.3 --- Environment resolver and destination safety:**
    centralize catalog/schema/Volume resolution and prevent test-mode
    writes to canonical destinations.

**Acceptance criteria:** actual workspace resources are verified;
development and test catalogs are physically separate; all write paths
resolve through configuration; destination guards have tests; no paid
feature is required.

## F03 --- CI/CD and automated quality foundation

**Goal:** establish low-cost automated checks and safe repository
collaboration.

-   **F03.1 --- Local developer checks:** formatting, lint, type/static
    checks where adopted, unit tests and deterministic scripts.
-   **F03.2 --- Contract, fixture and notebook validation:** validate
    YAML, schemas, notebook source and small test fixtures.
-   **F03.3 --- GitHub Actions and delivery controls:** configure
    free-tier CI checks, branch/PR conventions and evidence reporting
    without requiring paid runners.

**Acceptance criteria:** checks run reproducibly; failures block the
relevant PR workflow; secrets are not committed; CI does not require
Databricks credentials for ordinary unit tests.

## F04 --- Shared source acquisition and ingestion framework

**Goal:** provide reusable acquisition, provenance, manifests and safe
load decisions.

-   **F04.1 --- Source manifest and provenance contract:** define
    immutable source-file identity, content hash, provider, city,
    dataset, snapshot, file type, licence and retrieval metadata.
-   **F04.2 --- Acquisition, validation and immutable landing:** stage
    source files, validate bytes/format, land immutably and preserve
    evidence.
-   **F04.3 --- Run controls, idempotency and recovery:** record
    ingestion runs, scope decisions, retries, failures, replacement and
    explicit force reload.

**Acceptance criteria:** source file identity is deterministic;
duplicate acquisition is controlled; immutable landing is enforced;
failures are recorded accurately; full reload is explicit; test and live
destinations cannot be confused.

# Part B --- Airbnb ingestion and Medallion architecture

## F05 --- Airbnb detailed listings Bronze

-   **F05.1 --- Listing source contract and registration:** inspect
    source fields, keys, snapshot metadata, licensing and schema
    evolution.
-   **F05.2 --- Source-faithful Bronze ingestion:** preserve raw values,
    source identity, technical metadata and row counts.
-   **F05.3 --- Idempotency, schema drift and reprocessing:** test
    same-file no-op, new snapshot, changed bytes, malformed input and
    explicit replacement.

**Acceptance criteria:** raw listing observations are traceable to
immutable source identity; counts reconcile; reruns are safe; no
business cleaning occurs in Bronze.

## F06 --- Airbnb calendar and reviews Bronze

-   **F06.1 --- Calendar/review contracts and availability:** define
    independent dataset contracts, expected keys, temporal fields and
    source availability.
-   **F06.2 --- Separate Bronze ingestion paths:** ingest calendar and
    detailed reviews as independent products using shared framework
    components.
-   **F06.3 --- Quality, failure isolation and rerun validation:**
    validate file-level parsing, row counts, dataset-scoped reruns and
    failure handling.

**Acceptance criteria:** calendar and reviews remain separate; large
inputs are handled within Free Edition constraints; invalid
rows/failures are observable; one dataset failure does not silently
corrupt another.

## F07 --- Airbnb summary and neighbourhood Bronze

-   **F07.1 --- Summary source registration and ingestion:** register
    summary listings/reviews independently and preserve source identity.
-   **F07.2 --- Neighbourhood CSV and GeoJSON ingestion:** validate CSV
    and FeatureCollection structures; preserve complete geometry
    representation.
-   **F07.3 --- Geometry, availability and replacement validation:**
    reconcile feature counts, represent unavailable files explicitly and
    test scoped replacement.

**Acceptance criteria:** summary files are separate assets; geometry is
not truncated; source availability and ingestion failure are distinct;
all products have provenance and rerun evidence.

## F08 --- Multi-city registry and ingestion control plane

**Goal:** make city/dataset execution independently configurable and
auditable before broad city expansion.

-   **F08.1 --- Stable city registry:** define immutable `city_id`,
    canonical slug, display name, country, region, timezone, currency,
    coordinates/boundary reference and enabled state.
-   **F08.2 --- City/dataset source registry:** represent each source
    dataset independently for each city, including provider, expected
    file type, snapshot identity and source URL/discovery metadata.
-   **F08.3 --- Availability and ingestion state model:** keep
    `available`, `not_published`, `unknown`, `invalid` and `disabled`
    separate from ingestion `pending`, `success`, `failed` and reprocess
    states.
-   **F08.4 --- Manifest identity and scoped execution:** ensure
    manifest records identify city, dataset, source version/hash, run
    and target; execute only selected city/dataset slices.
-   **F08.5 --- Idempotency, snapshot change and explicit full reload:**
    prove same identity is a no-op, a new snapshot affects only its
    scoped dataset, and full reload requires an explicit mode and audit
    record.
-   **F08.6 --- Control-plane acceptance and coverage reporting:**
    produce city-by-dataset availability, ingestion and layer status
    with failure isolation.

**Acceptance criteria:** every city has a stable ID independent of its
display name; every dataset has independent city-level availability and
ingestion status; manifest identifies city/dataset/source
version/result; reruns compare manifest and source identity; new
snapshots do not reload unrelated cities/datasets; full reload is
explicit; all state transitions have tests and runtime evidence.

## F09 --- Airbnb listings Silver

-   **F09.1 --- Silver contract and normalization:** define grain,
    stable key, types, standard names and source lineage.
-   **F09.2 --- Business validation, exclusions and deduplication:**
    implement field rules, valid ranges, duplicate resolution and
    rejected-record reasons.
-   **F09.3 --- Silver tests and reconciliation:** validate uniqueness,
    required fields, source-to-Silver counts and repeatability.

**Acceptance criteria:** one documented record grain; no silent loss;
invalid/rejected records are explained; transformations are
deterministic and testable.

## F10 --- Airbnb calendar and reviews Silver

-   **F10.1 --- Calendar Silver model:** standardize dates, availability
    flags and observed prices while preserving snapshot context.
-   **F10.2 --- Review Silver model and privacy minimization:**
    normalize review dates/content fields and avoid exposing unnecessary
    reviewer personal information.
-   **F10.3 --- Relationships, history and quality validation:**
    validate listing references, temporal ranges, duplicates and
    reconciliation.

**Acceptance criteria:** calendar and reviews have documented grains and
temporal semantics; source links are validated; price/availability
caveats remain explicit.

## F11 --- Airbnb summary and spatial Silver

-   **F11.1 --- Summary reconciliation products:** compare detailed and
    summary data without blindly unioning them; document expected
    differences.
-   **F11.2 --- Neighbourhood and geometry normalization:** create
    consistent neighbourhood identifiers, names and valid geometry
    representations.
-   **F11.3 --- Spatial linkage and audit validation:** link listings to
    neighbourhoods where evidence supports it and test geometry validity
    and unmatched records.

**Acceptance criteria:** summary/reference roles are clear; spatial
relationships are reproducible; unmatched or invalid geometries are
reported.

## F12 --- Cross-file quality, snapshot history and monitoring

-   **F12.1 --- Cross-file reconciliation:** compare
    listing/calendar/review/summary/neighbourhood relationships and
    report expected versus unexpected differences.
-   **F12.2 --- Snapshot history and freshness:** model source snapshot
    chronology, coverage and freshness without claiming CDC semantics.
-   **F12.3 --- Quality reporting and recovery:** provide actionable
    quality outputs, failure states and repeatable recovery procedures.

**Acceptance criteria:** dataset-level and cross-file quality are
measurable; source freshness and missing files are visible; reruns and
snapshot changes are auditable.

# Part C --- Gold and semantic layer

## F13 --- Airbnb Gold analytical data products

**Goal:** publish reusable business-ready products with explicit grain
and business meaning. Use dbt Core/dbt-databricks for SQL-centric
models; use PySpark only where complexity or runtime constraints justify
it.

-   **F13.1 --- Gold architecture and product contracts:** define model
    grains, keys, dimensions, measures, source dependencies, incremental
    strategy and acceptance tests.
-   **F13.2 --- Listing and accommodation analytical models:** build
    listing snapshot facts and reusable city/accommodation profiles.
-   **F13.3 --- Calendar and availability analytical models:** model
    listing/date observations and observed-price/availability indicators
    with clear caveats.
-   **F13.4 --- Review and listing performance analytics:** model review
    measures and listing performance without unnecessary personal data.
-   **F13.5 --- Neighbourhood and city analytical profiles:** build
    neighbourhood-level supply, price summaries, room-type mix and
    geographic products.
-   **F13.6 --- Snapshot intelligence and Gold validation:** compare
    source snapshots, model listing changes and validate product quality
    and query performance.

**Acceptance criteria:** all products have documented grain, keys and
business purpose; tests cover uniqueness, relationships and accepted
ranges; data lineage is traceable; output supports real application
questions; builds are repeatable and resource-aware.

## F14 --- Semantic layer and governed metrics using MetricFlow

-   **F14.1 --- Business glossary and metric definitions:** define
    terms, formulas, units, currency, denominator, filters,
    time/snapshot meaning and caveats.
-   **F14.2 --- MetricFlow semantic models and relationships:** define
    source models, entities, dimensions, measures and metrics in
    versioned YAML.
-   **F14.3 --- Local governed metric query interface:** validate and
    query metrics with local MetricFlow CLI where the pinned Databricks
    adapter path supports it; expose an allowlisted Python service.
-   **F14.4 --- Semantic validation and evaluation:** compare
    MetricFlow-generated results with trusted SQL fixtures; test joins,
    fanout, filters, time dimensions and metric consistency.

**Acceptance criteria:** dbt Cloud is not required; dependency versions
are pinned; local CLI validation is reproducible; metric definitions
have business documentation; query results reconcile with trusted SQL;
no hosted API capability is falsely claimed.

# Part D --- Structured services and conversational application

## F15 --- Python accommodation and analytics services

-   **F15.1 --- Service contracts and data access foundation:** define
    typed request/response objects, repository/query boundaries and
    error contracts.
-   **F15.2 --- Accommodation search and comparison:** implement
    validated filters, listing detail, neighbourhood comparison and
    bounded results.
-   **F15.3 --- Metric and coverage services:** expose approved
    MetricFlow metrics and source coverage/freshness explanations
    through controlled interfaces.
-   **F15.4 --- Service testing and resilience:** test invalid filters,
    empty results, unavailable metrics, query errors, timeouts and
    result limits.

**Acceptance criteria:** service logic is independent of Streamlit and
LLM prompts; outputs are typed and tested; structured provenance/caveats
are included.

## F16 --- Streamlit travel discovery application

-   **F16.1 --- Application shell and navigation:** establish app
    configuration, pages, session handling and error presentation.
-   **F16.2 --- Accommodation discovery and comparison:** build filters,
    result tables/cards, listing details and neighbourhood/city
    comparisons.
-   **F16.3 --- Conversation interface and context presentation:**
    provide chat UI, active trip context, source/caveat display and
    reset/edit controls.
-   **F16.4 --- Usability and integration validation:** test empty
    states, invalid inputs, slow responses, local setup and
    accessibility basics.

**Acceptance criteria:** the application calls Python services rather
than embedding business logic in UI code; users can understand data
dates, currency and limitations; local execution is reproducible.

## F17 --- Structured conversational AI assistant

-   **F17.1 --- Model/provider adapter and prompt foundation:**
    configure local Ollama as default and an optional provider
    interface; version prompts and model settings.
-   **F17.2 --- Typed tool calling and clarification:** expose
    accommodation, comparison and metric tools; validate arguments and
    ask for missing required inputs.
-   **F17.3 --- Grounded structured responses and failure handling:**
    explain tool results, cite data context, handle empty/partial
    failures and avoid invented values.

**Acceptance criteria:** assistant uses approved tools; arbitrary SQL is
prohibited; tool arguments/results are validated; local-model path works
without paid API keys.

## F18 --- Structured AI evaluation and tracing

-   **F18.1 --- Evaluation dataset and expected tool behavior:** create
    representative accommodation and analytical questions with expected
    tools/arguments/results.
-   **F18.2 --- Tool, metric and answer evaluation:** measure tool
    selection, argument validity, query correctness, answer faithfulness
    and clarification behavior.
-   **F18.3 --- Tracing, privacy and regression reporting:** trace
    request/tool/model versions and durations while redacting sensitive
    content; run regression checks.

**Acceptance criteria:** evaluations are repeatable and versioned;
measured results come from actual runs; privacy and failure cases are
tested.

# Part E --- Official destination knowledge and RAG

## F19 --- Official destination knowledge registry and acquisition

-   **F19.1 --- Source registry and rights review:** define approved
    publishers, canonical URLs, collection rules and
    retention/redistribution constraints.
-   **F19.2 --- City/document coverage model:** track city, language,
    document type, publisher, publication/update date and validity.
-   **F19.3 --- Acquisition, version and freshness tracking:** download
    approved documents/pages, hash content, preserve versions and record
    changes/expiry.

**Acceptance criteria:** only approved sources are acquired; every item
has provenance and rights status; updates do not erase prior versions;
failures and unavailable sources are visible.

## F20 --- Document extraction and processing pipeline

-   **F20.1 --- PDF/HTML extraction:** extract text, headings, page
    numbers, links and document metadata.
-   **F20.2 --- OCR, layout and table handling:** detect scanned pages;
    apply OCR when required; preserve table context and extraction
    warnings.
-   **F20.3 --- Normalization, deduplication and extraction quality:**
    normalize text, compare hashes, validate extraction completeness and
    retain canonical source text.

**Acceptance criteria:** extraction method/version is recorded;
page/section traceability is preserved where possible; failures are not
treated as empty valid documents; duplicate versions are handled
explicitly.

## F21 --- Chunking, metadata enrichment and embeddings

-   **F21.1 --- Heading-aware chunking strategy:** evaluate
    section-based and bounded chunking with overlap where useful;
    preserve page/heading boundaries.
-   **F21.2 --- Metadata enrichment and canonical chunk records:**
    attach city, publisher, source URL, document/version, language,
    type, validity, page and heading metadata.
-   **F21.3 --- Local embedding generation and versioning:** use
    Sentence Transformers locally; pin model/revision/dimensions and
    generate deterministic chunk embeddings.

**Acceptance criteria:** chunk IDs are stable for a document version;
chunk boundaries preserve meaning; metadata supports filtering/citation;
embeddings can be regenerated.

## F22 --- Chroma vector database and indexing management

-   **F22.1 --- Chroma architecture and collection contracts:** define
    persistent local storage, collection naming, ID and metadata
    schemas.
-   **F22.2 --- Index creation and incremental upsert:** index canonical
    chunks; update only changed document versions; verify counts and
    metadata.
-   **F22.3 --- Deletion, versioning, integrity and rebuild:** remove
    superseded chunks, preserve version history outside Chroma and
    rebuild the index from canonical records.

**Acceptance criteria:** Chroma is persistent and rebuildable; duplicate
upserts are safe; old content is not returned after approved
replacement/deletion; no cloud service is required.

## F23 --- Retrieval optimization and ranking

-   **F23.1 --- Query understanding and rewriting:** identify
    city/topic/language/temporal intent and clarify missing scope.
-   **F23.2 --- Metadata-filtered vector and lexical retrieval:** filter
    by city, document type, authority and validity; support exact
    keyword retrieval for names/terms.
-   **F23.3 --- Hybrid retrieval, reranking and evaluation:** compare
    vector-only, lexical/hybrid and optional reranking using a labelled
    evaluation set; retain only justified complexity.

**Acceptance criteria:** retrieval is city-aware and traceable;
exact-name and semantic queries are tested; candidate ranking is
measured; no unsupported reranker dependency is mandatory.

## F24 --- Grounded RAG answer generation

-   **F24.1 --- Evidence assembly and context management:** select
    bounded, non-duplicate passages and preserve provenance.
-   **F24.2 --- Citation and source attribution:** produce
    document/page/section references and source dates where available.
-   **F24.3 --- Grounded generation, conflict handling and abstention:**
    distinguish facts from suggestions, surface conflicts/freshness, and
    abstain when evidence is insufficient.

**Acceptance criteria:** claims are supported by retrieved passages;
citations resolve to source records; old brochures are not treated as
proof of current operations; no-answer behavior is tested.

## F25 --- RAG evaluation, safety and observability

-   **F25.1 --- Retrieval evaluation:** measure recall/ranking
    relevance, city filter correctness, source authority and freshness.
-   **F25.2 --- Answer-quality evaluation:** measure groundedness,
    citation accuracy, completeness, contradiction handling and
    abstention.
-   **F25.3 --- Safety, tracing and regression:** test prompt injection
    in retrieved documents, sensitive-data leakage, trace metadata and
    regression after model/index/prompt changes.

**Acceptance criteria:** evaluation datasets are versioned; results are
reproducible; retrieved text is treated as untrusted; traces are useful
without storing unnecessary personal data.

# Part F --- Integrated travel planning and interoperability

## F26 --- Multi-tool travel planning and conversational orchestration

-   **F26.1 --- Conversation context and travel preferences:** manage
    destination, duration/dates if supplied, interests and accommodation
    constraints.
-   **F26.2 --- Tool selection and orchestration:** route structured
    questions to accommodation/MetricFlow services and destination
    questions to RAG.
-   **F26.3 --- Itinerary generation and constraint checking:** organize
    supported attractions and accommodation choices into a trip outline;
    identify missing routing/opening-hour evidence.
-   **F26.4 --- Multi-turn refinement and recovery:** update
    preferences, handle tool failure and explain partial results.

**Acceptance criteria:** multi-tool responses combine structured and
document evidence correctly; itinerary suggestions do not imply verified
routes or live opening status; conversation context can be
corrected/reset; partial failures are explicit.

## F27 --- MCP server and tool contracts

-   **F27.1 --- MCP tool selection and protocol contracts:** select
    stable services and define typed MCP schemas/descriptions.
-   **F27.2 --- Thin server handlers and service integration:** expose
    existing Python service functions without duplicating business
    logic.
-   **F27.3 --- Security, limits and parity tests:** validate
    permissions, input bounds, errors and parity with direct service
    results.

**Acceptance criteria:** local MCP server exposes only approved tools;
no arbitrary SQL/filesystem access; invalid arguments and failures are
tested.

## F28 --- MCP client and compatible host integration

-   **F28.1 --- MCP client and tool discovery:** connect to the local
    server and inspect tool definitions.
-   **F28.2 --- Host integration and controlled execution:** integrate
    with a compatible host and verify user-visible tool behavior.
-   **F28.3 --- Timeout, disconnect and partial-failure validation:**
    test lifecycle, reconnect, cancellation and unavailable tools.

**Acceptance criteria:** client/host behavior is documented; tool calls
remain permission-bounded; direct service and MCP results are
consistent; hosted deployment is optional.

## F29 --- Production readiness and portfolio release

-   **F29.1 --- Release and deployment controls:** define versioning,
    configuration, local deployment and optional free hosting
    boundaries.
-   **F29.2 --- Unified data, application and AI observability:**
    consolidate source freshness, pipeline status, service latency,
    retrieval quality and AI traces.
-   **F29.3 --- Runbooks, recovery and operational readiness:** document
    and test source failure, schema drift, quota exhaustion, failed
    ingestion, dbt/MetricFlow incompatibility, index rebuild, model/tool
    failure and rollback.
-   **F29.4 --- Portfolio evidence and release sign-off:** prepare
    architecture, data dictionary, source/rights inventory, coverage
    report, dbt/MetricFlow examples, RAG evaluation, demo and known
    limitations.

**Acceptance criteria:** a fresh setup can reproduce the core workflow
within free-tier constraints; recovery is demonstrated; project claims
match evidence; no paid service is required for the portfolio
demonstration.

------------------------------------------------------------------------

# Appendix A --- Cross-cutting checklists

## Every feature

-   [ ] Scope, dependencies and acceptance criteria match v32.
-   [ ] Source/schema/model/document version and rights are recorded
    where applicable.
-   [ ] Data grain, keys, contracts and provenance are documented.
-   [ ] Invalid, duplicate, missing, stale and boundary cases are
    considered.
-   [ ] Idempotency, replacement, retry and recovery are tested where
    relevant.
-   [ ] Free-tier resource assumptions are validated.
-   [ ] Security, privacy and secret handling are reviewed.
-   [ ] CI and relevant runtime/evaluation evidence are recorded.

## Every subfeature

-   [ ] Existing repository patterns were inspected.
-   [ ] File plan classifies reuse/modify/create/retire.
-   [ ] Task IDs are stable and scoped.
-   [ ] Unit/contract/integration tests are defined.
-   [ ] Runtime checks use the correct catalog or local environment.
-   [ ] No canonical write/destructive operation occurred without
    approval.
-   [ ] Tested commit and evidence are recorded.
-   [ ] Known limitations and one next action are explicit.

## Cross-computer handoff

-   [ ] Save intended changes and inspect working tree.
-   [ ] Record branch and latest commit.
-   [ ] Commit/push where safe; identify uncommitted work explicitly.
-   [ ] Update `docs/progress.md` with verified facts only.
-   [ ] Record Databricks workspace/catalog/schema and run evidence
    needed to resume.
-   [ ] State one next action.

# Appendix B --- `docs/progress.md` suggested structure

``` markdown
# TripPilot Progress

## Current work
- Feature/subfeature/task:
- Status:
- Next action:

## Git / CI
- Branch / PR / tested commit:
- CI status/link:
- Changed files (summary):

## Validation evidence
- Unit/contract test command and result:
- Test-catalog validation: source identity, destination, counts and quality:
- Canonical run: explicit approval, destination, run ID/Delta version and result:
- dbt/MetricFlow versions and query reconciliation:
- Document/index version and integrity:
- AI evaluation dataset/version and measured outcomes:

## Verified milestone summary
- Feature/subfeature | status | tested commit | evidence | known gap

## Blockers and next action
-
```

# Appendix C --- Official references

-   Databricks Free Edition:
    https://docs.databricks.com/aws/en/getting-started/free-edition
-   Databricks Free Edition limits:
    https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
-   dbt MetricFlow commands:
    https://docs.getdbt.com/docs/build/metricflow-commands
-   dbt MetricFlow overview:
    https://docs.getdbt.com/docs/build/about-metricflow
-   Chroma: https://docs.trychroma.com/
-   Sentence Transformers: https://www.sbert.net/
-   Ollama: https://ollama.com/
-   Streamlit: https://docs.streamlit.io/
-   MCP: https://modelcontextprotocol.io/
