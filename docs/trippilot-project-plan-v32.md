# TripPilot --- Project Plan

**Version:** 32.0\
**Revised:** November 24, 2026\
**Companion:** `trippilot-unified-build-guide-v32.md`\
**Planning horizon:** 6--8 months, subject to source availability,
free-tier quotas and implementation complexity\
**Delivery principle:** build one integrated travel discovery and
planning product from reusable structured-data and destination-knowledge
foundations.\
**Document status:** project blueprint. Feature descriptions define
intended outcomes; they do not assert implementation status.

------------------------------------------------------------------------

## 1. Project vision

Build **TripPilot**, an AI-powered travel discovery and planning
assistant backed by a reusable Analytics Engineering platform and an
authoritative destination-knowledge system.

TripPilot helps travellers:

-   discover and compare Airbnb accommodation options;
-   understand neighbourhood and city-level accommodation
    characteristics;
-   explore attractions and visitor information documented by official
    destination sources;
-   compare accommodation and destination options using consistent
    analytical metrics;
-   create and refine practical trip outlines through conversation; and
-   understand where information came from, how current it is, and what
    the system cannot verify.

### Primary portfolio objective

Demonstrate the ability to design and build a governed lakehouse,
transform source data into trusted analytical products, define reusable
business metrics, engineer a document retrieval pipeline, and deliver an
evaluated conversational AI application that uses both structured and
unstructured information.

### Product positioning

> TripPilot is an accommodation discovery and destination-planning
> assistant that combines observed Airbnb data with curated official
> visitor information. It helps users compare options, explore
> documented attractions and guidance, and organize personalized trip
> outlines with transparent evidence and limitations.

TripPilot is not a general-purpose travel concierge, booking platform,
live navigation service or guarantee of current attraction operations.

## 2. Product definition and supported questions

### 2.1 Core user journeys

  -----------------------------------------------------------------------
  User need               Information source      Application capability
  ----------------------- ----------------------- -----------------------
  Find accommodation      Inside Airbnb listings  Structured listing
  matching filters                                search

  Compare listing prices  Airbnb Gold products    Governed metric queries
  and characteristics                             and comparisons

  Understand              Airbnb Silver/Gold and  Neighbourhood and city
  neighbourhood           neighbourhood geometry  analysis
  accommodation profiles                          

  Explore attractions and Official destination    RAG with source
  activities              guides, attraction      citations
                          documents and approved  
                          official pages          

  Understand documented   Official park, museum,  Filtered retrieval with
  visitor rules and       government and          validity and evidence
  accessibility           attraction publications checks
  information                                     

  Combine accommodation   Airbnb services plus    Multi-tool
  and destination         official knowledge      recommendations
  interests                                       

  Organize a short trip   Structured results plus Conversational planning
  outline                 retrieved official      and itinerary
                          information             composition
  -----------------------------------------------------------------------

### 2.2 Representative questions

**Accommodation discovery** - Find two-bedroom listings in a selected
city or neighbourhood. - Compare entire homes and private rooms using
observed listing characteristics. - Show listings within an observed
nightly-price range. - Compare review scores or review counts when
source fields support the calculation.

**Neighbourhood and city analysis** - Which neighbourhoods have the most
listings? - Compare average or median observed listing prices across
neighbourhoods. - Compare the share of entire-home listings across
areas. - How has listing supply changed between available snapshots?

**Destination knowledge** - What attractions does the official visitor
guide recommend? - Which cultural attractions are described in the
collected official documents? - What visitor rules or accessibility
details does an official publication mention? - What activities are
described for families or visitors interested in nature?

**Combined planning** - Suggest an area to stay and official attractions
to explore during a three-day visit. - Find accommodation matching a
budget and organize documented attractions into a relaxed itinerary. -
Compare neighbourhood accommodation characteristics and attractions
documented for the destination. - Refine an itinerary when the traveller
changes interests or accommodation preferences.

### 2.3 Product truthfulness and limitations

-   Inside Airbnb is observational data, not live booking inventory.
    Calendar records are not confirmed bookings, actual occupancy or
    guaranteed future availability.
-   Observed prices are not guaranteed prices for future dates. Preserve
    currency and snapshot context; do not compare currencies without an
    explicitly approved FX source and conversion timestamp.
-   Official documents can be old, incomplete or inconsistent. A
    brochure does not prove an attraction is open today or that an event
    is still happening.
-   Accessibility claims must be directly supported by sufficiently
    specific source evidence. Do not infer accessibility from an
    attraction name or category.
-   Without a live routing source, the application may organize an
    itinerary but must not claim transit-optimized travel times or
    verified walking distances.
-   Restaurant availability, live business hours, weather, transit
    arrivals, booking and payments are outside the initial product
    scope.
-   When evidence is missing, stale, ambiguous or contradictory, explain
    the limitation and abstain from unsupported claims.

## 3. Product and engineering principles

1.  **Medallion architecture is a core Analytics Engineering
    responsibility.** Bronze preserves source evidence; Silver
    standardizes and validates it; Gold creates business-ready
    analytical products.
2.  **Gold and the semantic layer have different responsibilities.**
    Gold defines reusable data products and grains; MetricFlow defines
    governed metric semantics and generates metric queries.
3.  **Structured queries and RAG are complementary.** Use SQL/semantic
    services for measurable structured facts; use retrieval for evidence
    in official documents.
4.  **The LLM does not own business logic.** Deterministic services
    calculate, filter, validate and retrieve. The model interprets
    intent, selects tools and explains supported results.
5.  **Provenance is part of the product.** Data rows, metrics and
    retrieved passages must be traceable to source identity and version.
6.  **Incremental and idempotent operations are defaults.** Full reloads
    and index rebuilds are explicit, controlled operations.
7.  **Free-tier constraints shape the design.** Avoid paid managed
    services as required dependencies; keep local/open-source
    alternatives and resource-aware execution.
8.  **Evaluate before adding complexity.** Hybrid retrieval, reranking,
    agents and orchestration frameworks must solve measured problems.
9.  **One integrated product.** Structured accommodation, destination
    knowledge and conversational planning share one application and
    service architecture.

## 4. Source strategy and governance

### 4.1 Structured source --- Inside Airbnb

Inside Airbnb is the initial structured source family. Source assets may
include:

  --------------------------------------------------------------------------
  Source file                Meaning                 Intended use
  -------------------------- ----------------------- -----------------------
  `listings.csv.gz`          Detailed listing        Main accommodation
                             observations for a      search and listing
                             source snapshot         analytics

  `calendar.csv.gz`          Listing/date            Calendar and
                             observations            observed-price analysis
                                                     with caveats

  `reviews.csv.gz`           Individual review       Review history and
                             records                 listing-level review
                                                     analytics

  `listings.csv`             Summary listing records Reference and
                                                     reconciliation; not a
                                                     duplicate detailed fact

  `reviews.csv`              Summary review records  Reference and
                                                     reconciliation where
                                                     definitions align

  `neighbourhoods.csv`       Neighbourhood reference Neighbourhood dimension
                             list                    

  `neighbourhoods.geojson`   Neighbourhood           Spatial enrichment and
                             boundaries              mapping
  --------------------------------------------------------------------------

Source availability is independent for each city and dataset. Do not
assume every city publishes every file or uses the same snapshot date.

Requirements: - retain source URL, publisher, retrieval timestamp,
source snapshot date, file hash, file size, file type, schema identity,
licence/attribution metadata and ingestion run identity; - preserve raw
source values in Bronze and preserve the source snapshot identity
through downstream layers; - validate keys, uniqueness, nulls, data
types, ranges and relationships before accepting Silver products; - keep
detailed and summary assets separate and reconcile them rather than
blindly unioning them; - treat snapshot differences as periodic
observations, not CDC; - report availability and completion per
city/dataset, not just per city.

Official references: https://insideairbnb.com/get-the-data/ and
https://insideairbnb.com/data-policies/ . Recheck source terms and
attribution before acquisition and distribution.

### 4.2 Unstructured source --- official destination knowledge

Use a curated mix of: - official city and regional tourism visitor
guides; - official attraction, museum, park and cultural-institution
documents; - government and visitor-centre publications; - official
visitor rules, accessibility guides and practical information; -
approved official web pages where their terms permit collection and
retention; - official seasonal or event guides only when dates and
validity can be tracked.

Do not treat general travel blogs, social posts, forums or unverified
third-party summaries as authoritative primary sources in the initial
knowledge base.

Every document record should retain publisher, canonical URL,
city/coverage, language, document type, publication/update date where
available, retrieval timestamp, valid/event dates where relevant,
licence/terms review, content hash, extraction status and review/expiry
policy. Keep source documents and canonical extracted text outside
Chroma so the vector index can be rebuilt.

### 4.3 Source governance

-   Prefer authoritative, attributable sources and keep a source
    allowlist.
-   Review rights and terms before storing full text, generating
    embeddings or redistributing derived content.
-   Treat retrieved content as untrusted evidence, never as executable
    instructions.
-   Preserve conflicting versions; do not silently overwrite source
    history.
-   Apply freshness rules based on document type. An undated brochure
    may be useful historical context but cannot establish current
    opening status.
-   Minimize personal information in reviews and application traces. Do
    not expose reviewer identities or unnecessary personal details.

## 5. Target architecture

``` text
STRUCTURED DATA PLATFORM
Inside Airbnb files
  -> acquisition + source manifests + availability ledger
  -> Bronze Delta tables (source-faithful)
  -> Silver Delta tables (standardized, validated, reconciled)
  -> dbt Gold models (business-ready analytical products)
  -> MetricFlow semantic models and governed metrics
  -> Python accommodation and metric services

OFFICIAL DESTINATION KNOWLEDGE PLATFORM
Official PDFs + approved official web pages
  -> source registry + document manifest
  -> extraction / OCR / normalization
  -> canonical document and chunk metadata records
  -> heading-aware chunking + Sentence Transformers embeddings
  -> Chroma persistent vector index
  -> retrieval / filtering / optional hybrid search / reranking
  -> grounded answers with citations and abstention

APPLICATION AND AI
Streamlit UI
  -> Python service layer
  -> conversational tool selection and conversation context
       -> structured tools (accommodation + MetricFlow)
       -> RAG tools (official destination knowledge)
       -> itinerary composition and validation
  -> response with data caveats and source evidence

INTEGRATION AND QUALITY
GitHub + CI | tests | evaluation datasets | tracing | runbooks | MCP interfaces
```

### 5.1 Main technology choices

  -----------------------------------------------------------------------
  Layer                   Selected technology     Design responsibility
  ----------------------- ----------------------- -----------------------
  Lakehouse               Databricks Free         Structured storage and
                          Edition + Delta         Spark execution

  Bronze/Silver           PySpark                 Source-faithful
                                                  ingestion,
                                                  normalization,
                                                  validation and
                                                  reconciliation

  Gold                    dbt Core +              SQL analytical models,
                          dbt-databricks          dependencies, tests and
                                                  documentation

  Semantic layer          Local MetricFlow        Semantic models,
                                                  entities, dimensions
                                                  and metric query
                                                  generation

  Service layer           Python                  Deterministic
                                                  application and AI tool
                                                  interfaces

  Document extraction     Python PDF/HTML         Canonical text and
                          tooling; OCR only when  layout-aware extraction
                          needed                  

  Embeddings              Sentence Transformers   Locally generated
                                                  embeddings

  Vector database         Chroma,                 Persistent vector index
                          locally/self-hosted     and metadata filtering

  LLM                     Local Ollama model as   Natural-language
                          default; optional       interpretation and
                          free-tier API adapter   response generation

  Orchestration           Python; LangGraph only  Tool routing and
                          where stateful          multi-step conversation
                          workflows justify it    state

  UI                      Streamlit               User-facing discovery
                                                  and assistant
                                                  experience

  Protocol integration    MCP                     Optional standard tool
                                                  interface for
                                                  compatible hosts

  Version control/CI      GitHub and GitHub       Source control, checks
                          Actions free-tier usage and release evidence
  -----------------------------------------------------------------------

### 5.2 Free-resource policy

The required project path must not depend on paid subscriptions or paid
managed services.

-   **Databricks:** Databricks Free Edition only. It is serverless-only,
    quota-limited and intended for non-commercial personal use. Do not
    design around classic clusters, custom compute, guaranteed uptime or
    unlimited jobs. Use the available serverless notebook compute and
    the single small SQL warehouse where supported. Check current quotas
    and feature availability before each major runtime design.
-   **dbt:** dbt Core and open-source adapters run locally. dbt Cloud is
    not required. MetricFlow can be defined, validated and queried
    locally through supported CLI commands; the hosted dbt Semantic
    Layer API and managed integrations are not part of this design.
-   **MetricFlow compatibility:** pin mutually compatible dbt Core,
    MetricFlow and dbt-databricks versions. Validate the exact
    adapter/runtime combination with a small proof of concept before
    relying on MetricFlow for application queries. If a supported local
    MetricFlow-to-Databricks execution path is unavailable in the
    selected versions, keep MetricFlow definitions and local CLI
    validation, and expose a documented Python/dbt SQL fallback rather
    than claiming a hosted API exists.
-   **Vector database and embeddings:** Chroma and Sentence Transformers
    run locally; no Chroma Cloud or paid embedding API is required.
-   **LLM:** local Ollama is the default to avoid mandatory API charges.
    A free-tier hosted model may be an optional adapter, never a
    required dependency. Free quotas, model availability and terms can
    change.
-   **Application:** Streamlit runs locally for the required
    demonstration. Free hosting may be optional but must not be required
    for project acceptance.
-   **CI:** use GitHub Actions free-tier allowances carefully; do not
    require paid runners or paid secrets-management products.
-   **External source access:** Databricks Free Edition outbound
    internet is restricted. Download source files locally or through
    permitted official access and upload them using supported workspace
    paths when direct retrieval is blocked.
-   **Scale:** process city batches sequentially or in small bounded
    batches. The 20-city and 50+ targets are coverage goals, not
    promises of one large concurrent job.

Databricks Free Edition is for personal, non-commercial use. A future
commercial deployment would require a separate review of licensing,
source rights, hosting and service costs.

### 5.3 Current Databricks environment contract

The environment configuration must reflect the following catalog
separation and must be verified against the live workspace before any
write:

  -------------------------------------------------------------------------
  Purpose            Catalog            Schemas           Meaning
  ------------------ ------------------ ----------------- -----------------
  Canonical          `trippilot_dev`    `bronze`,         Canonical
  development/live                      `silver`, `gold`, development data
  dataset                               `ops`             and operational
                                                          metadata; "live"
                                                          here does not
                                                          mean a production
                                                          service

  Isolated test      `trippilot_test`   `bronze`,         Physically
  dataset                               `silver`, `ops`   separate test
                                                          data and
                                                          operational
                                                          metadata; no
                                                          development data
                                                          is copied
                                                          automatically
  -------------------------------------------------------------------------

The test catalog does not require a Gold schema unless a feature
explicitly needs one and the schema is deliberately added. Resolve
catalog and schema destinations through the environment resolver; never
append `_test` to table names as a substitute for catalog isolation.
Verify the actual workspace and configuration before execution because
free-tier features and account configuration can change.

The current repository configuration also declares a source Volume under
`trippilot_dev/bronze/source_files`. Do not assume that the same Volume
path is available in the test catalog; resolve and validate paths
through the project's approved environment configuration.

## 6. Medallion and Analytics Engineering design

### 6.1 Bronze

Purpose: preserve what the source supplied and make every landed dataset
traceable.

Responsibilities: - immutable source-file identity and content hash; -
source/city/dataset/snapshot/run provenance; - source-faithful raw
values and minimal parsing metadata; - schema and parse observations
without silently cleaning source values; - idempotent load decisions and
explicit force-reload behavior; - separate source manifest and ingestion
manifest responsibilities.

### 6.2 Silver

Purpose: turn raw source records into standardized, validated and
analytically consistent datasets.

Responsibilities: - explicit contracts and stable types; - naming and
categorical standardization; - null, range, duplicate and key
validation; - rejection/quarantine policy with reason codes; - city,
snapshot and dataset identity preservation; - cross-file reconciliation
and valid relationships; - neighbourhood and spatial normalization; -
documented temporal and price semantics; - repeatable transformation and
quality evidence.

Silver is a major Analytics Engineering deliverable, not a temporary
staging layer.

### 6.3 Gold

Purpose: create reusable business-ready products with explicit grain,
keys and business definitions.

Gold products should include: - listing-level analytical model; -
accommodation/city profile; - calendar/availability observation model; -
review and listing-performance model; - neighbourhood profile and
spatial summary; - snapshot-change and coverage model.

Use dbt for modular SQL models, model dependencies, tests, documentation
and repeatable builds. PySpark may remain appropriate for
transformations that are genuinely complex or spatially intensive, but
avoid splitting ownership of the same model between two frameworks
without a reason.

### 6.4 Semantic layer

MetricFlow sits above Gold. It defines: - semantic models and their
source models; - entities and relationships; - dimensions and time
dimensions; - measures and reusable metrics; - metric descriptions,
filters and calculation semantics.

The semantic layer is not a replacement for Gold tables. It provides a
consistent interface for questions such as average observed listing
price, listing count, entire-home share and review score summaries.
Metric definitions must document grain, currency, snapshot scope,
filters and caveats.

## 7. Gold data products and example metrics

  -----------------------------------------------------------------------------
  Gold product                  Grain                   Example analytical
                                                        questions
  ----------------------------- ----------------------- -----------------------
  `fct_listing_snapshot`        One listing per         Listing count, observed
                                city/source snapshot    price, room type,
                                                        minimum nights,
                                                        host/listing
                                                        characteristics

  `fct_calendar_observation`    One listing per         Observed availability
                                calendar date per       indicators and observed
                                snapshot                calendar price

  `fct_review`                  One review per source   Review volume and time
                                review record           distribution, with
                                                        privacy minimization

  `dim_neighbourhood`           One neighbourhood per   Neighbourhood name,
                                city/reference version  boundary and stable
                                                        city relationship

  `agg_neighbourhood_profile`   One neighbourhood per   Listing supply, price
                                city/snapshot           summaries, room-type
                                                        mix and listing density

  `agg_city_profile`            One city per source     City accommodation
                                snapshot                profile and coverage
                                                        indicators

  `fct_snapshot_change`         One listing change      New, removed and
                                between comparable      changed listing
                                snapshots               observations

  `agg_source_coverage`         One                     Source availability,
                                city/dataset/snapshot   freshness, row counts
                                                        and quality status
  -----------------------------------------------------------------------------

MetricFlow metric examples (subject to approved definitions): -
`listing_count`; - `median_observed_nightly_price` and
`average_observed_nightly_price` (with currency and snapshot filters); -
`entire_home_listing_share`; - `average_review_score` where the source
field is populated and definitionally comparable; - `review_count`; -
`neighbourhood_listing_count`; - `calendar_available_day_share`
(explicitly an observed calendar indicator, not actual occupancy); -
`new_listing_count_between_snapshots`.

Do not expose a metric until its grain, denominator, null treatment,
time scope, currency and limitations are documented and tested.

## 8. City coverage and ingestion control plane

### 8.1 City registry

Every city has a stable `city_id` independent of its display name. The
registry should include canonical slug, display name, country code,
region, timezone, currency where relevant, coordinates or geographic
boundary reference, enabled state and metadata version.

### 8.2 Dataset/source availability

Each source dataset has an independent city-specific state. Distinguish
at least: - `available` --- a valid source asset is identified; -
`not_published` --- evidence shows the publisher did not publish the
expected asset; - `unknown` --- availability has not been established; -
`invalid` --- a discovered source asset fails required validation; -
`disabled` --- intentionally excluded by configuration.

Ingestion state is separate from source availability. A dataset may be
available but not yet ingested, ingested successfully, failed, or
require reprocessing.

### 8.3 Manifest and execution requirements

The ingestion manifest must identify city, dataset, source provider,
source snapshot/version, source file identity/hash, run identity,
target, result, row counts, timestamps and controlled failure
information. Rerun decisions must compare the manifest and source
identity before loading. A new source snapshot for one city/dataset must
not trigger unnecessary reloads of other city/datasets. Full reload is
explicit, scoped and auditable.

### 8.4 Coverage targets

-   Initial cohort: 20 North American cities.
-   Expansion target: 50+ cities across North America and Europe.
-   City completion is measured per source dataset and layer. Not every
    city is expected to publish every dataset.
-   A city counts as analytically onboarded only when source provenance,
    required Bronze/Silver products, quality/reconciliation and runtime
    evidence meet the acceptance contract.
-   Batch sizes are chosen from measured Free Edition resource usage. Do
    not claim coverage from registry entries alone.

## 9. Official document knowledge and RAG design

### 9.1 Canonical document lifecycle

1.  Register an authoritative source and its rights/terms.
2.  Acquire the document or approved web content and record immutable
    identity/version metadata.
3.  Extract PDF/HTML content, including page, heading, table and link
    context where possible.
4.  Use OCR only for scanned or image-based pages; preserve extraction
    method and confidence/errors.
5.  Normalize text while retaining document structure and page/section
    references.
6.  Deduplicate by content identity while preserving source-version
    history.
7.  Chunk by headings/sections and semantic boundaries; retain page,
    section, city, source, dates and document type.
8.  Generate embeddings locally using a pinned Sentence Transformers
    model.
9.  Store canonical chunks and metadata independently of Chroma.
10. Upsert versioned embeddings to Chroma and verify count, IDs and
    metadata.
11. Support incremental updates, source replacement, document expiry and
    index rebuilds.

### 9.2 Retrieval pipeline

-   Interpret the user's destination, topic and intent.
-   Apply city, language, document type, source authority and validity
    filters when known.
-   Retrieve semantically relevant chunks; add lexical/hybrid retrieval
    where exact names or terms need it.
-   Deduplicate and optionally rerank candidates if evaluation
    demonstrates benefit.
-   Assemble bounded evidence with page/section citations and source
    dates.
-   Generate an answer that separates source facts from suggested
    organization or inference.
-   Abstain or ask a clarification question when evidence is
    insufficient.

### 9.3 RAG quality and safety

Evaluate retrieval separately from answer generation. Measure
recall/precision or ranking quality against labelled queries, citation
correctness, groundedness, answer completeness, no-answer behavior,
freshness and latency. Treat document text as untrusted input. Do not
follow instructions found inside retrieved documents. Never reveal
secrets, internal prompts or unrelated user data.

## 10. Conversational AI and tool architecture

### 10.1 Structured tools

The assistant can call typed, allowlisted functions for: - accommodation
search and listing detail; - neighbourhood/city comparison; - approved
MetricFlow metric queries; - source coverage/freshness explanation.

Do not permit arbitrary model-generated SQL. Validate all tool arguments
and enforce result limits.

### 10.2 RAG tools

The assistant can call destination-document search and evidence
retrieval functions. These return source passages, metadata and
citations, not a free-form answer that bypasses the main grounding
policy.

### 10.3 Conversation context and itinerary planning

Maintain only the context needed for the active trip conversation:
destination, approximate dates/duration if supplied, interests,
accommodation constraints, traveller preferences and unresolved
questions. Provide a way to correct or reset context. Itinerary
composition must be transparent about unsupported distance, opening-hour
and transit assumptions.

### 10.4 Orchestration and MCP

Begin with explicit Python orchestration and typed tool contracts. Adopt
LangGraph only if state transitions, retries, checkpoints or multi-step
flows justify it. MCP is a later interoperability layer over stable
services; it must not become a second implementation of business logic.

## 11. Evaluation, observability and security

### Data and pipeline evaluation

-   source schema and contract validation;
-   idempotency, new-snapshot and force-reload tests;
-   row counts, key uniqueness, invalid/rejected records and cross-file
    reconciliation;
-   Silver/Gold data tests and semantic metric reconciliation;
-   city/dataset coverage, freshness and failed-run reporting.

### AI evaluation

-   service correctness;
-   tool selection and argument validity;
-   metric query correctness;
-   retrieval relevance and city/document filtering;
-   citation accuracy and groundedness;
-   answer completeness and abstention;
-   multi-turn context handling and partial-tool failure;
-   prompt-injection resistance and latency.

### Observability

Trace request ID, tool name, duration, status, bounded result metadata,
model/prompt version and source IDs. Avoid storing secrets, unnecessary
personal data, full review text or raw traveller profiles. Keep
evaluation datasets separate from ordinary user traces.

## 12. Feature roadmap

The roadmap is the project-wide feature hierarchy. Detailed subfeature
implementation instructions, tasks, dependencies and acceptance criteria
are maintained in the companion Unified Build Guide. Both documents must
use the same IDs.

### Part A --- Shared data engineering foundation

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F01 --- Project architecture and  Repository architecture,
  source registries**                 configuration, stable city/source
                                      identity and engineering contracts.

  **F02 --- Databricks lakehouse      Free Edition workspace, catalogs,
  foundation**                        schemas, Volumes, Delta conventions
                                      and environment separation.

  **F03 --- CI/CD and automated       Local checks, GitHub Actions,
  quality foundation**                contracts, fixtures and controlled
                                      delivery.

  **F04 --- Shared source acquisition Acquisition, immutable landing,
  and ingestion framework**           manifests, availability,
                                      idempotency, scoped reruns and
                                      recovery.
  -----------------------------------------------------------------------

### Part B --- Airbnb source ingestion and Medallion architecture

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F05 --- Airbnb detailed listings  Source contracts, acquisition and
  Bronze**                            source-faithful listings Bronze.

  **F06 --- Airbnb calendar and       Independent acquisition and Bronze
  reviews Bronze**                    products for calendar and detailed
                                      reviews.

  **F07 --- Airbnb summary and        Summary, neighbourhood CSV and
  neighbourhood Bronze**              geometry Bronze products.

  **F08 --- Multi-city registry and   Stable city IDs, per-city/dataset
  ingestion control plane**           availability, manifest identity,
                                      scoped incremental execution and
                                      explicit full reload.

  **F09 --- Airbnb listings Silver**  Standardized listing records,
                                      validation, deduplication and
                                      rejection handling.

  **F10 --- Airbnb calendar and       Temporal calendar and review
  reviews Silver**                    models, relationships and quality.

  **F11 --- Airbnb summary and        Summary reconciliation,
  spatial Silver**                    neighbourhood normalization and
                                      spatial relationships.

  **F12 --- Cross-file quality,       Reconciliation, temporal history,
  snapshot history and monitoring**   freshness, coverage and operational
                                      quality.
  -----------------------------------------------------------------------

### Part C --- Gold and semantic layer

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F13 --- Airbnb Gold analytical    Six reusable analytical products
  data products**                     with explicit grain, business
                                      meaning and tests.

  **F14 --- Semantic layer and        Business glossary, semantic models,
  governed metrics using MetricFlow** metric query interface and semantic
                                      validation.
  -----------------------------------------------------------------------

### Part D --- Structured services and conversational application

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F15 --- Python accommodation and  Reusable structured query,
  analytics services**                comparison and metric services.

  **F16 --- Streamlit travel          Accommodation discovery,
  discovery application**             neighbourhood comparison and
                                      conversational UI foundation.

  **F17 --- Structured conversational Natural-language structured
  AI assistant**                      queries, typed tool calling,
                                      clarification and grounded
                                      responses.

  **F18 --- Structured AI evaluation  Tool, metric, answer and
  and tracing**                       request-trace evaluation.
  -----------------------------------------------------------------------

### Part E --- Official destination knowledge and RAG

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F19 --- Official destination      Source allowlist, rights review,
  knowledge registry and              city coverage, document identity
  acquisition**                       and acquisition.

  **F20 --- Document extraction and   PDF/HTML extraction, OCR when
  processing pipeline**               needed, normalization, structure
                                      preservation and quality.

  **F21 --- Chunking, metadata        Chunk strategies, contextual
  enrichment and embeddings**         metadata and local embedding
                                      generation/versioning.

  **F22 --- Chroma vector database    Persistent local vector store,
  and indexing management**           incremental upsert, versioning,
                                      deletion and rebuild.

  **F23 --- Retrieval optimization    Query understanding, metadata
  and ranking**                       filters, lexical/vector retrieval,
                                      optional hybrid search and
                                      reranking.

  **F24 --- Grounded RAG answer       Evidence assembly, citation, source
  generation**                        conflict/freshness handling and
                                      abstention.

  **F25 --- RAG evaluation, safety    Retrieval/answer evaluation,
  and observability**                 prompt-injection controls, tracing
                                      and regression tests.
  -----------------------------------------------------------------------

### Part F --- Integrated travel planning and interoperability

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
  **F26 --- Multi-tool travel         Combine accommodation, MetricFlow
  planning and conversational         and RAG tools into contextual
  orchestration**                     itinerary planning.

  **F27 --- MCP server and tool       Expose approved TripPilot services
  contracts**                         through typed MCP tools.

  **F28 --- MCP client and compatible Connect to a compatible host and
  host integration**                  validate lifecycle, permissions and
                                      failure handling.

  **F29 --- Production readiness and  Reproducibility, deployment,
  portfolio release**                 observability, runbooks, evaluation
                                      evidence and final demonstration.
  -----------------------------------------------------------------------

### F13 --- Gold subfeature summary

-   **F13.1 --- Gold architecture and product contracts:** grains, keys,
    dimensions, measures and product acceptance.
-   **F13.2 --- Listing and accommodation analytical models:**
    listing-level and city-level accommodation products.
-   **F13.3 --- Calendar and availability analytical models:** temporal
    observations and observed-price products.
-   **F13.4 --- Review and listing performance analytics:** review and
    listing-performance products with privacy minimization.
-   **F13.5 --- Neighbourhood and city analytical profiles:** spatial
    and comparative products.
-   **F13.6 --- Snapshot intelligence and Gold validation:** change
    analysis, source coverage and Gold quality.

### F14 --- MetricFlow subfeature summary

-   **F14.1 --- Business glossary and metric definitions.**
-   **F14.2 --- MetricFlow semantic models and relationships.**
-   **F14.3 --- Governed metric query interface using local MetricFlow
    capabilities.**
-   **F14.4 --- Semantic validation and evaluation against trusted SQL
    results.**

### F19--F25 --- RAG subfeature summary

  -----------------------------------------------------------------------
  Feature                             Subfeatures
  ----------------------------------- -----------------------------------
  F19                                 F19.1 Source registry and rights
                                      review; F19.2 city/document
                                      coverage; F19.3 acquisition,
                                      version and freshness tracking

  F20                                 F20.1 PDF/HTML extraction; F20.2
                                      OCR/layout/table handling; F20.3
                                      normalization, deduplication and
                                      extraction quality

  F21                                 F21.1 heading-aware chunking; F21.2
                                      metadata enrichment; F21.3
                                      embedding model selection,
                                      generation and versioning

  F22                                 F22.1 Chroma architecture and
                                      collection contracts; F22.2
                                      incremental index creation/upsert;
                                      F22.3 deletion, versioning,
                                      integrity and rebuild

  F23                                 F23.1 query understanding/rewrite;
                                      F23.2 metadata-filtered vector and
                                      lexical retrieval; F23.3 hybrid
                                      retrieval/reranking experiments and
                                      evaluation

  F24                                 F24.1 evidence assembly/context
                                      management; F24.2 citations and
                                      source attribution; F24.3 grounded
                                      generation, conflict handling and
                                      abstention

  F25                                 F25.1 retrieval evaluation; F25.2
                                      answer-quality evaluation; F25.3
                                      safety, tracing and regression
                                      reporting
  -----------------------------------------------------------------------

## 13. Target repository architecture

This is a logical target, not a mandate to create every directory in
advance. Reuse existing repository conventions and introduce modules
only when a feature needs them.

``` text
trippilot/
  .github/workflows/
  config/
    project.yml
    city_registry.yml
    sources/
    environments/
  contracts/
    airbnb/ operations/ services/ documents/ semantic/ ai/
  src/
    common/ acquisition/ airbnb/ quality/ observability/
    services/ semantic/ documents/ embeddings/ retrieval/
    ai/ tools/ orchestration/ evaluation/ tracing/
    mcp/
  dbt/
    dbt_project.yml
    models/ staging/ intermediate/ marts/ semantic_models/
    tests/ macros/
  notebooks/
    ops/ bronze/ silver/ verification/
  app/streamlit/
  data_contracts/
  evals/
    structured/ retrieval/ rag/ tools/ conversations/
  tests/
    unit/ contract/ integration/ fixtures/
  docs/
    architecture/ decisions/ sources/ verification/ progress.md
  runbooks/
  scripts/
  pyproject.toml
```

Databricks catalogs/schemas are runtime resources, not repository
directories. Keep test/live destination resolution in configuration and
shared resolver code.

## 14. Project-wide acceptance principles

A feature is complete only when its subfeatures meet their acceptance
criteria and evidence is recorded. Across the project:

-   source identity, rights, provenance and versions are traceable;
-   city and dataset availability are independently represented;
-   reruns are idempotent and full reloads explicit;
-   Bronze, Silver and Gold responsibilities are distinct;
-   analytical grains, metric definitions and caveats are documented;
-   document sources, extracted text, chunks and vector IDs are
    traceable;
-   structured tools validate arguments and limit results;
-   RAG responses cite evidence and abstain when evidence is
    insufficient;
-   evaluation datasets and measured outcomes are reproducible;
-   tests distinguish local fixtures, test-catalog runtime and canonical
    development runtime;
-   free-tier resource limits and known product limitations are
    documented;
-   no feature claims completion based only on code presence or
    documentation.

## 15. Explicitly out of scope

Unless a future product decision justifies a new version: - Airbnb
booking, payment, reservation or live inventory; - guaranteed future
rates or actual occupancy claims from calendar observations; - live
weather, live transit, transit arrivals or routing optimization; -
restaurant opening status and real-time business discovery; - a general
event aggregation platform; - Overture Places and GTFS as separate
structured source families; - embedding all structured Airbnb rows into
Chroma; - arbitrary LLM-generated SQL; - mandatory paid APIs, dbt Cloud,
Chroma Cloud or paid hosting; - Kubernetes, microservices, multiple
agent frameworks, model fine-tuning or training a foundation model
without a demonstrated need.

## 16. Source references and change control

Verify current documentation, source availability, terms, schema
compatibility and free-tier limits before implementation. Links are
reference points, not guarantees of permanent availability.

-   Inside Airbnb data: https://insideairbnb.com/get-the-data/
-   Inside Airbnb policies: https://insideairbnb.com/data-policies/
-   Databricks Free Edition:
    https://docs.databricks.com/aws/en/getting-started/free-edition
-   Databricks Free Edition limitations:
    https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
-   dbt MetricFlow commands:
    https://docs.getdbt.com/docs/build/metricflow-commands
-   dbt MetricFlow overview:
    https://docs.getdbt.com/docs/build/about-metricflow
-   dbt Semantic Layer FAQ:
    https://docs.getdbt.com/docs/use-dbt-semantic-layer/sl-faqs
-   Chroma documentation: https://docs.trychroma.com/
-   Sentence Transformers: https://www.sbert.net/
-   Ollama: https://ollama.com/
-   Streamlit: https://docs.streamlit.io/
-   MCP specification: https://modelcontextprotocol.io/

### Change control

-   Project Plan owns product purpose, scope, architecture, source
    strategy, technology decisions and feature outcomes.
-   Unified Build Guide owns feature/subfeature/task decomposition,
    dependencies, implementation standards, prompts and acceptance
    criteria.
-   `docs/progress.md` records actual implementation state and verified
    evidence; it is not duplicated in these blueprint documents.
-   Repository code, tests and runtime evidence determine what is
    implemented.
-   Any change to feature IDs, scope, technology dependencies or
    acceptance criteria must be reflected in both v32 documents and
    reviewed before implementation.
