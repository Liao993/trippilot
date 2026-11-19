# TripPilot — Project Plan

**Version:** 31.0  
**Revised:** November 19, 2026  
**Supersedes:** v28 as the active plan; retain earlier versions as historical references  
**Companion:** `trippilot-unified-build-guide-v31.md`  
**Overall platform horizon:** 8–12 months  
**Delivery principle:** follow the complete roadmap in order, reuse verified work, and build one integrated travel data and AI platform.  
**Status:** Project blueprint. Planned features are not evidence of implementation or runtime verification.

---

## 1. Project vision

Build **TripPilot**, a travel discovery and planning application powered by a reusable lakehouse and a grounded conversational AI assistant.

The complete project includes all of the following capabilities:

- **Accommodation:** Airbnb listing discovery using Inside Airbnb datasets.
- **Places:** hotel/lodging, restaurant, cafe and attraction discovery from one shared place dataset.
- **Transportation:** selected public-transit schedule information from official GTFS feeds.
- **Weather:** date- and location-aware weather lookup through a provider-backed service.
- **Destination knowledge:** official visitor guides, tourism brochures, attraction information and event documents.
- **AI interaction:** natural-language questions, structured tool calling, RAG, a vector database, MCP integration and multi-source trip-planning workflows.
- **Quality and operations:** data quality, AI evaluation, CI/CD, monitoring, tracing, source freshness, operational runbooks and reproducible releases.

The project is not an Airbnb-only application with AI postponed until the end. **Airbnb is the first complete vertical slice of the final integrated platform.** Its data services and conversational assistant establish the patterns that later sources will extend.

### Primary portfolio message

> Built a multi-source travel lakehouse and grounded AI application, starting with reusable multi-city accommodation pipelines and extending the same service, retrieval, MCP, evaluation and monitoring architecture to places, transit, weather and official destination knowledge.

The project should show that you understand how to combine data engineering, lakehouse design and AI application engineering—not simply how to connect an LLM to a collection of APIs.

## 2. Product definition and user experience

### 2.1 What a traveller should be able to do

The intended user experience grows from a useful Airbnb discovery experience into a multi-source travel assistant.

| Travel question | Data/service responsible | AI interaction |
|---|---|---|
| Find accommodation in a city and compare listing options | Inside Airbnb Gold + accommodation query service | Structured tool calling |
| Discover hotels/lodging, restaurants, cafes and attractions nearby | Overture Places Gold + geospatial places service | Structured tool calling; optional semantic discovery for place descriptions |
| Find nearby transit stops, routes and scheduled service | Selected GTFS Gold + transit query service | Structured tool calling |
| Check weather for a destination and date | Weather provider adapter + cache | Structured tool calling |
| Ask about visitor guidance, attraction rules, events and local information | Curated official document corpus + retrieval service | RAG with source attribution and validity checks |
| Build a day-by-day or multi-day trip outline | Accommodation, places, transit, weather and document services | Multi-tool orchestration through the travel assistant |

The assistant should disclose missing coverage, stale information, unsupported dates and unavailable services. It must not invent booking availability, hotel rates, opening hours, live transit arrivals or event status.

### 2.2 Product surfaces

1. **Streamlit application:** the first user-facing interface. Build it initially around Airbnb, then add tabs/pages for places, transit, weather and destination knowledge.
2. **Python service layer:** tested deterministic functions used by Streamlit and AI tools. Service logic must not live only in UI callbacks or prompts.
3. **Conversational AI layer:** interprets a traveller's request, asks for missing information, calls approved tools and composes a grounded answer.
4. **RAG/retrieval layer:** retrieves official documents and other suitable text content. It complements structured queries; it does not replace them.
5. **MCP integration:** exposes stable services to compatible AI hosts through typed tool contracts.

### 2.3 Airbnb-first does not mean AI-later

The first AI assistant is built while Airbnb is the only fully integrated source family. It uses structured LLM tool calling over the same Python functions used by Streamlit. It does not wait for Overture, GTFS or the document corpus.

When new source families are added, the existing assistant gains tools and context. The RAG corpus and vector index are extended when suitable text sources—such as official visitor guides and event documents—become available. The multi-source assistant is therefore an evolution of the original Airbnb assistant, not a separate AI product.

### 2.4 Scope boundaries

TripPilot is a **discovery and planning assistant**, not a booking or transaction platform. It does not book accommodation, collect payment, reserve restaurant tables, guarantee hotel availability, or operate as a live transit navigation service.

Inside Airbnb observations are not official booking inventory. Overture Places records are place discovery records, not guaranteed hotel inventory or live operating hours. GTFS Schedule is static schedule data unless a separate official real-time feed is integrated.

## 3. Delivery strategy and build sequence

TripPilot is built from the first roadmap feature through the final feature in the order defined in the Build Guide. Do not skip ahead to a later feature because it appears more interesting or because a later milestone is attractive.

The roadmap begins at **F01**. There is no separate F00 feature in this version. Within each feature, complete its subfeatures in ascending ID order, then move to the next feature. The only exception is a dependency discovered during implementation: pause, document the blocker, and complete the smallest prerequisite work needed before returning to the planned sequence. Do not silently reorder the roadmap.

### 3.1 Working pace and three-month aspiration

A pace of approximately **three subfeatures per week** is a planning estimate, not a quota or deadline. Some subfeatures will take less time; others will need several sessions because they involve unfamiliar tools, external data availability, Databricks limits or runtime debugging.

The near-term aspiration is that, after roughly three months of steady work, the project may be approaching or may have reached an integrated Airbnb conversational assistant and meaningful multi-city coverage, with a target of 50 eligible cities. This is an outcome to work toward, not a fixed delivery promise. The actual position depends on the starting state, verified work that can be reused, implementation complexity and source availability.

### 3.2 One continuous roadmap

The full roadmap remains active:
- F01–F04 establish the shared foundation and engineering controls.
- F05–F12 build and validate the Airbnb data platform.
- F13–F16 deliver the Python services, Streamlit experience, conversational assistant and AI evaluation.
- F17 expands the Airbnb pipeline across cities, targeting 50 eligible cities and preparing for 100.
- F18–F20 add Overture Places.
- F21–F23 add selected GTFS transit data.
- F24 adds weather.
- F25–F27 add official documents, embeddings, vector search and evaluated RAG.
- F28–F30 add MCP and multi-source trip planning.
- F31 completes unified operational readiness and portfolio release evidence.

The three-month aspiration does not remove, defer or reorder these features. It is simply a rough progress expectation while following the same roadmap from beginning to end.

### 3.3 How to handle existing work

Existing code is an asset, not a reason to skip roadmap features. When reaching a subfeature, inspect the repository and its evidence. If the implementation already meets the acceptance criteria, verify it and record the evidence rather than rebuilding it. If it is incomplete, repair it within that subfeature. A feature can be marked complete only when its required subfeatures and feature-level acceptance criteria are verified.

### 3.4 Shared build, test and promotion policy

Every feature follows the same approved build lifecycle, defined in the Unified Build Guide v31: inspect and plan; implement; run `pytest`; run isolated testing-data validation; automatically execute the approved live/canonical workflow when all validation and governance gates pass; then verify, review and record evidence. The process is tool-independent and may be carried out by the user with guidance or an AI coding agent.

Testing has three purposes and should not be confused: small synthetic fixtures for fast unit tests; real-source testing in an isolated test destination, processing all relevant records when practical; and live/canonical acceptance after gates pass. When a dataset is too large for a routine full test, bounded or representative sampling may be used for development, but its selection and size must be documented and any required full-source/scale acceptance remains outstanding. The relevant data is the feature's intended source scope, not automatically the provider's entire global dataset.

Live execution is automatic after the approved workflow's test gates pass, but it is never unconditional. Source rights/attribution, source identity, schema, quality thresholds, reconciliation, idempotency, permissions, destination safety and feature-specific constraints must pass. A failed gate blocks promotion and is reported.

### 3.5 Multi-city acceptance principle

The 50-city target belongs to F17 and is reached only after F01–F16 have been completed in sequence. A city counts only when its selected detailed-listings snapshot is available and valid, Bronze ingestion succeeds with provenance and run metadata, core Silver succeeds, quality and reconciliation checks pass, and runtime evidence is recorded. Calendar, reviews, summary and neighbourhood files have independent availability and completion states.

Use a candidate pool larger than 50, because not every city will have a suitable source snapshot. Process cities in bounded batches and increase batch size only after observing actual Databricks runtime, resource usage and failure rates. Do not claim 50-city coverage from registry entries alone.

## 4. Data-source strategy

### 4.1 Accommodation — Inside Airbnb

**Role:** primary accommodation lakehouse source and first full data engineering vertical slice.

Inside Airbnb provides public quarterly datasets for cities/regions, generally covering approximately the most recent 12 months. Public datasets are currently published under CC BY 4.0, with attribution requirements. Availability and file dates vary by city; the pipeline must discover and verify the actual file inventory rather than assuming all cities publish every file.

Source files to account for when available:

| File | Source grain / meaning | TripPilot use |
|---|---|---|
| `listings.csv.gz` | Detailed listing observation for a snapshot | Main accommodation search and comparison |
| `calendar.csv.gz` | Listing/date observations within the calendar snapshot | Calendar observations and price/availability indicators with strong caveats |
| `reviews.csv.gz` | Individual review records | Review history and listing-level review metrics |
| `listings.csv` | Summary listing information and metrics | Reconciliation/reference input; not a second detailed listing fact |
| `reviews.csv` | Summary review data associated with listing IDs | Reconciliation/time analytics where definitions align |
| `neighbourhoods.csv` | Neighbourhood names/list | Neighbourhood dimension/reference |
| `neighbourhoods.geojson` | Neighbourhood boundaries | Spatial layer and map enrichment |

**Interpretation requirements:**

- A listing row is an observed source snapshot, not a booking or live inventory record.
- Calendar observations are not confirmed bookings, actual occupancy or guaranteed future availability.
- Preserve snapshot date, city, currency and price basis for every price field.
- Do not compare different currencies without a declared FX provider and conversion timestamp.
- Use source IDs as keys only after validating their stability and uniqueness.
- Keep detailed records and source summary files separate; use summary files for comparison/reconciliation instead of blindly unioning them.
- Treat differences between quarterly snapshots as snapshot change analysis, not CDC.
- Preserve source URL, retrieval date, file hash, file size, source schema/version, licence and attribution metadata.

**City target:** build the city registry to support 50 cities and a future expansion to 100. Actual onboarding is based on current Inside Airbnb file availability, valid schemas and successful processing. Coverage is reported separately by city, snapshot and file type.

Official references:  
https://insideairbnb.com/get-the-data/  
https://insideairbnb.com/data-policies/

### 4.2 Shared hotel, restaurant and attraction discovery — Overture Maps Places

**Role:** one shared global POI/places pipeline for hotel/lodging, restaurant, cafe, attraction and other supported place categories.

Use Overture Places as the initial downloadable place catalogue rather than building separate hotel and restaurant pipelines. It is published as cloud-native Parquet/GeoParquet data, provides global coverage, stable IDs and source metadata, and has a hierarchical taxonomy suitable for category filtering.

Important schema/version note: the September 2026 Overture places schema v2 removed the old `categories` field. Use the current `taxonomy` and `basic_category` fields, pin the release/schema, and implement category mapping from versioned configuration. Do not copy examples using the retired `categories` field into new code.

Engineering and governance requirements:

- Pin release ID and schema version; record retrieval date and changelog.
- Filter to configured city areas and required columns before materializing large partitions.
- Preserve GERS/place IDs, geometry, names, addresses, taxonomy, `basic_category`, confidence, `sources[]` and release lineage.
- Build explicit category groups for lodging/hotels, food/drink and attractions. Maintain this mapping as versioned configuration.
- Treat confidence as one quality signal, not a duplicate-removal guarantee.
- Preserve upstream provider and licence information; do not assume every source-provider record has identical licence obligations.
- Deduplicate cautiously and retain ambiguous match candidates for audit.
- Do not claim that place records contain dependable room rates, bookings, reviews, opening hours or guaranteed current operating status.

The Places theme documentation describes its own published licences and lists the contributing source providers and associated licence information. Re-check the release-specific attribution/licensing guidance before distributing derived datasets.

Official references:  
https://docs.overturemaps.org/guides/places/  
https://docs.overturemaps.org/schema/reference/places/place/  
https://docs.overturemaps.org/guides/places/taxonomy/  
https://docs.overturemaps.org/guides/attribution-and-licensing/

### 4.3 Public transportation — GTFS Schedule

**Role:** selected, official static public-transit service data.

Use GTFS Schedule feeds from agencies that publish a current, downloadable feed with terms that permit the intended use. Start with nearby stops, routes serving stops, and scheduled departures for a requested service date/time. Maintain an agency/feed registry because availability, feed quality, terms and service dates vary by operator.

Core GTFS Schedule files commonly include `agency.txt`, `routes.txt`, `trips.txt`, `stops.txt`, `stop_times.txt`, `calendar.txt` and `calendar_dates.txt`. Some feeds may use conditional or optional files, so validate against the current specification rather than assuming every feed has exactly the same file set.

Requirements:

- Record agency, publisher, official URL, feed version/hash, licence, timezone, retrieval date and service validity.
- Validate required files, IDs, relationships, stop coordinates, time formats and service calendars.
- Apply `calendar_dates` exceptions and agency timezone correctly.
- Clearly label results as static schedule data. Do not describe them as live arrivals.
- Do not promise GTFS for every Airbnb city; maintain independent transit coverage.
- GTFS Realtime is optional and separate from the static Schedule implementation.

Official references:  
https://gtfs.org/documentation/overview/  
https://gtfs.org/documentation/schedule/reference/

### 4.4 Weather — provider-backed lookup and cache

**Role:** request-time weather context for destination/date questions.

Use Open-Meteo as the initial provider adapter for the non-commercial portfolio stage, subject to current terms and attribution. The free API is non-commercial and rate-limited. Do not assume the free terms are suitable for a future commercial product.

Weather should initially be a service with a cache, not a 50/100-city historical lakehouse batch. Cache keys include coordinates, forecast product, date range and units. Store retrieval time, provider/model information where supplied, issue time, valid time range, units and expiry. Distinguish forecast from historical/climate products and return an explicit unsupported-horizon response.

Keep the provider behind a replaceable interface so another provider can be adopted without changing the chatbot contract.

Official references:  
https://open-meteo.com/en/docs  
https://open-meteo.com/en/terms

### 4.5 Official visitor guides and event documents

**Role:** RAG knowledge for destination guidance that structured tables and APIs cannot reliably answer.

Start with a curated collection from official tourism boards, city/government websites, museums, parks, cultural institutions, visitor centres and transit agencies. Add event documents only when event dates and details are explicitly supported by the source.

Store source URL, publisher, city/coverage, language, document type, publication/update date, retrieval date, valid/event dates, licence/terms, content hash and review/expiry policy. Treat undated brochures and old PDFs as historical reference, not proof that an event is currently happening.

Prefer a smaller, auditable collection over an indiscriminate web crawl. Re-check rights and terms before storing full text, building embeddings or distributing content.

## 5. Lakehouse and AI architecture

```text
SOURCE / ACQUISITION LAYER
  Inside Airbnb snapshots (7 file classes)
  Overture Places monthly GeoParquet releases
  Official GTFS Schedule ZIP feeds
  Weather provider API
  Official visitor / event documents
          |
          v
SOURCE CONTROL AND SHARED PLATFORM
  source registry | city registry | agency registry | document manifest
  schema contracts | file hashes | terms/licence metadata | run IDs
  configuration | secrets management | environment settings
          |
          v
DATABRICKS LAKEHOUSE
  Bronze: source-faithful, versioned source records and raw metadata
  Silver: typed, normalized, quality-checked, deduplicated and enriched data
  Gold: accommodation, place and transit products for defined user queries
  Operational Delta tables: pipeline runs, quality results, coverage, freshness
  Document tables: extracted text, chunks, embeddings metadata and source links
          |
          +-----------------------------+
          |                             |
          v                             v
DETERMINISTIC SERVICE LAYER        RETRIEVAL / VECTOR LAYER
  accommodation service             document chunks in Delta
  places discovery service           embedding generation/config
  transit schedule service           Databricks AI Search index
  weather provider/cache             vector + keyword/hybrid retrieval
  document retrieval service         metadata filters and source IDs
          |                             |
          +--------------+--------------+
                         v
APPLICATION / AI LAYER
  Streamlit user interface
  LLM intent understanding and structured tool calling
  RAG-grounded destination answers
  MCP server -> MCP client / compatible host
  bounded multi-source trip planner
                         |
                         v
QUALITY, CI/CD AND OPERATIONS (CROSS-CUTTING)
  GitHub + pull requests + automated tests + deployment configuration
  Databricks Jobs/pipelines monitoring + data freshness/quality metrics
  app/tool/RAG/agent traces + AI evaluation datasets and reports
  alerts/runbooks + release evidence + rollback/recovery procedures
```

### 5.1 Responsibility boundaries

- **Databricks/PySpark/Delta:** ingestion, transformation, quality, lakehouse storage, history, governance and query-ready Gold products.
- **Python service layer:** deterministic query and business logic, validated parameters, result limits and clear error contracts.
- **Streamlit:** user interaction and rendering; it must call services rather than contain SQL/business logic.
- **LLM:** understand user intent, ask for missing information, choose approved tools, and compose an answer using tool results.
- **Vector database / AI Search:** semantic retrieval over suitable text content, primarily official documents and extracted visitor/event content.
- **MCP:** a protocol boundary that exposes tested Python services to a compatible AI client/host.
- **CI/CD:** verify and package changes, then deploy only to environments the project can actually access.
- **Monitoring/evaluation:** measure pipeline health, data quality, query/app reliability, retrieval quality, tool correctness and agent outcomes.

### 5.2 Do not put every data source into the vector database

The vector index is **not** a second copy of the lakehouse and is not the default query engine for all travel data.

Use structured tools/SQL for:
- Airbnb filters, listing metrics, calendars and reviews.
- Place category, proximity and spatial filtering.
- GTFS routes, stop times and service calendars.
- Weather values and forecast ranges.

Use embeddings/vector retrieval for:
- Official visitor guide passages.
- Attraction policies and descriptions where a text question benefits from semantic retrieval.
- Event and cultural documents with city, validity date, publisher and source metadata.
- Other curated, rights-cleared unstructured content.

A selected place description may later be indexed for semantic discovery, but the canonical place record remains in Delta Gold. Do not embed every listing, stop-time row or weather observation merely to claim vector database experience.

### 5.3 Vector database strategy

The preferred Databricks-aligned starting point is **Databricks AI Search** (formerly Databricks Vector Search), using a Delta Sync index over a Delta table of curated document chunks and metadata. It keeps the lakehouse table as the system of record and the index as a retrieval structure. Start with triggered synchronization to control refreshes and resource use.

Free Edition documentation currently lists one AI Search endpoint with one search unit and does not support Direct Vector Access. The design should therefore use the supported Delta Sync approach if it is available in the actual workspace. Verify endpoint/index creation, model/embedding access, quotas and permissions in the workspace before committing to it. Keep a small retrieval adapter so the vector index provider can be substituted if the Free Edition capability is unavailable or too restrictive; do not build two production retrieval systems in parallel.

### 5.4 Data model layers

**Bronze:** raw files or faithful parsed records, source metadata, source-version identifiers, retrieval timestamps, hashes and ingestion run metadata.

**Silver:** normalized types, keys, categories, coordinates, dates/time zones, schema validation, deduplication, relationship validation and auditable exclusions.

**Gold:** consumer-oriented products with documented grain, measures, currency handling, source freshness and lineage.

**Document retrieval products:** document manifest, extracted text, versioned chunks, embedding configuration and vector index metadata. These retain their relationship to original source documents and publication/validity dates.

**Operational products:** pipeline runs, quality results, city/file/agency coverage, source freshness, app requests, tool invocations, RAG retrieval events and evaluation results.

## 6. Logical data products

### 6.1 Airbnb

- `bronze_airbnb_listings_detail`
- `bronze_airbnb_calendar`
- `bronze_airbnb_reviews_detail`
- `bronze_airbnb_listings_summary_source`
- `bronze_airbnb_reviews_summary_source`
- `bronze_airbnb_neighbourhoods_source`
- `bronze_airbnb_neighbourhood_geometry_source`
- `silver_airbnb_listings`, `silver_airbnb_calendar`, `silver_airbnb_reviews`
- `silver_airbnb_listings_summary`, `silver_airbnb_reviews_summary`
- `silver_airbnb_neighbourhoods`, `silver_airbnb_neighbourhood_geometry`
- `bridge_airbnb_listing_neighbourhood`
- `gold_airbnb_listing_snapshot`, `gold_airbnb_calendar_observation`, `gold_airbnb_review`
- `gold_airbnb_listing_review_metrics`, `gold_airbnb_neighbourhood_profile`, `gold_airbnb_city_profile`
- `gold_airbnb_snapshot_changes`, `gold_airbnb_data_quality_summary`

### 6.2 Places

- `bronze_overture_places_source`
- `silver_overture_places`
- `gold_places`
- category views/products: `gold_lodging_places`, `gold_restaurants`, `gold_attractions`
- `gold_places_quality_summary`

Preserve Overture release, schema, stable ID, taxonomy, confidence and upstream source/licence metadata.

### 6.3 GTFS

- `bronze_gtfs_feed_files`
- `silver_gtfs_agency`, `silver_gtfs_routes`, `silver_gtfs_trips`, `silver_gtfs_stops`, `silver_gtfs_stop_times`, `silver_gtfs_calendar`, `silver_gtfs_calendar_dates`
- `gold_transit_stops`, `gold_transit_routes`, `gold_transit_schedule`
- feed coverage and validation products

### 6.4 Weather

Weather is initially API-backed rather than a permanent 50-city lakehouse fact. Use a cache/store only where it improves response time and quota management. Retain provider, location, issue time, valid time, retrieved time, unit and expiry.

### 6.5 Documents and vector retrieval

- `bronze_travel_documents` (file/source manifest and immutable source reference)
- `silver_travel_document_text` (extracted/cleaned text with source sections)
- `gold_travel_document_chunks` (versioned chunk, text, source metadata, city, language, validity and hash)
- Databricks AI Search index sourced from the chunk Delta table (or approved substitute adapter)
- retrieval logs and versioned RAG evaluation results

## 7. Feature roadmap

The complete build is organized as small, verifiable features in the companion build guide. Airbnb is the first vertical slice, but all source families and AI capabilities below are part of the project scope.

| Workstream | Features | Outcome |
|---|---|---|
| Foundation and engineering controls | F01–F04 | Shared architecture, Databricks foundation, migration verification, automated tests and CI/CD baseline |
| Airbnb platform and multi-city rollout | F05–F17 | Reusable first-city Bronze/Silver path, multi-city expansion toward 50, Gold products and later application/AI capabilities |
| Places discovery | F18–F20 | Shared hotel/lodging, restaurant, cafe and attraction products |
| Public transportation | F21–F23 | Selected GTFS feed pipelines and schedule query service |
| Weather | F24 | Provider adapter, cache and assistant integration |
| Documents and RAG | F25–F27 | Official document corpus, vector database and evaluated retrieval |
| MCP and multi-source AI | F28–F30 | MCP interfaces and multi-source travel assistant |
| Unified operations | F31 | Monitoring, deployment, evaluation reporting, runbooks and portfolio release |

### 7.1 Feature and subfeature register (v29)

Every roadmap feature is decomposed into numbered subfeatures. The subfeature names below are the planning baseline; the Build Guide defines their task IDs, implementation steps and acceptance gates.

**Identifier hierarchy**
- `F12` — parent feature (for example, Airbnb Gold data products).
- `F12.1` — subfeature (for example, Gold product requirements and grain design).
- `F12.1-T01` — task within that subfeature.

Subfeature IDs are stable once implementation begins. If scope changes, update the existing subfeature specification and record the change; do not silently renumber completed work. Add a new subfeature with the next available decimal suffix when new scope is approved. Tasks are numbered within their subfeature and may be added without changing sibling IDs.

| Feature | Subfeatures |
|---|---|
| F01 | F01.1 Repository baseline and architecture; F01.2 Environment, city and source configuration; F01.3 Shared contracts and engineering conventions |
| F02 | F02.1 Migration preflight and workspace validation; F02.2 Isolated migration execution and recovery tests; F02.3 Reconciliation, evidence and migration sign-off |
| F03 | F03.1 CI baseline and developer checks; F03.2 Contract, fixture and notebook validation; F03.3 Merge protection and delivery readiness |
| F04 | F04.1 Source manifest and provenance contract; F04.2 Raw acquisition, validation and immutable landing; F04.3 Run controls, reprocessing and failure tests |
| F05 | F05.1 Detailed listing source inspection and registration; F05.2 Bronze ingestion and metadata preservation; F05.3 Idempotency, schema drift and reprocessing |
| F06 | F06.1 Calendar and review source contracts; F06.2 Separate Bronze ingestion paths; F06.3 File-level quality and rerun validation |
| F07 | F07.1 Summary source registration and Bronze; F07.2 Neighbourhood CSV and GeoJSON Bronze; F07.3 Geometry, availability and replacement validation |
| F08 | F08.1 Listing Silver contract and normalization; F08.2 Business validation, exclusions and deduplication; F08.3 Silver tests and reconciliation |
| F09 | F09.1 Calendar Silver model; F09.2 Review Silver model and privacy minimization; F09.3 Relationship, history and quality validation |
| F10 | F10.1 Summary reconciliation products; F10.2 Neighbourhood and geometry normalization; F10.3 Spatial linkage and audit validation |
| F11 | F11.1 Cross-file reconciliation and relationship quality; F11.2 Snapshot history, coverage and freshness; F11.3 Operational quality reporting and recovery |
| F12 | F12.1 Gold product requirements and grain design; F12.2 Core accommodation Gold tables; F12.3 Profiles, snapshot changes and Gold validation |
| F13 | F13.1 Service contracts and data access foundation; F13.2 Accommodation search and detail capabilities; F13.3 Context, errors and service-level tests |
| F14 | F14.1 Streamlit application shell and navigation; F14.2 Accommodation discovery and comparison experience; F14.3 Context, usability and integration validation |
| F15 | F15.1 Assistant scope, model and prompt foundation; F15.2 Typed tool calling and request clarification; F15.3 Grounded responses, failure handling and safety checks |
| F16 | F16.1 Evaluation dataset and expected tool behaviour; F16.2 Quality metrics and evaluation execution; F16.3 Tracing, privacy and regression reporting |
| F17 | F17.1 City eligibility and registry onboarding; F17.2 Candidate cohort and source-availability audit; F17.3 Multi-city batch execution and failure isolation; F17.4 Controlled multi-city Bronze rollout; F17.5 Multi-city Silver validation and reconciliation; F17.6 Backfill, coverage reporting and scale validation; F17.7 50-city acceptance and evidence; F17.8 100-city readiness review |
| F18 | F18.1 Overture release, schema and licence registration; F18.2 City-area acquisition and Bronze processing; F18.3 Provenance, schema drift and rerun validation |
| F19 | F19.1 Places normalization and taxonomy mapping; F19.2 Confidence, geometry and provenance controls; F19.3 Deduplication, schema evolution and Silver validation |
| F20 | F20.1 Places Gold model and category products; F20.2 Nearby/category discovery service; F20.3 Application/AI integration and query evaluation |
| F21 | F21.1 Agency discovery, terms and registry; F21.2 GTFS feed acquisition and Bronze landing; F21.3 Feed completeness, versioning and invalid-feed handling |
| F22 | F22.1 GTFS Silver contracts and normalization; F22.2 Relationships, calendars and time validation; F22.3 Feed acceptance and schema compatibility tests |
| F23 | F23.1 Transit Gold data products; F23.2 Schedule and nearby-stop service functions; F23.3 Assistant integration and schedule correctness tests |
| F24 | F24.1 Weather provider contract and terms review; F24.2 Provider adapter, validation and cache; F24.3 Resilience, UI/AI integration and provider tests |
| F25 | F25.1 Document source selection and rights review; F25.2 Document catalogue and versioned acquisition; F25.3 Text extraction, event metadata and expiry controls |
| F26 | F26.1 Chunking strategy and canonical chunk records; F26.2 Embedding generation and version management; F26.3 Vector index synchronization and retrieval metadata tests |
| F27 | F27.1 Retrieval service and metadata filtering; F27.2 Retrieval/answer evaluation and grounded generation; F27.3 Freshness, no-answer handling and assistant integration |
| F28 | F28.1 MCP tool selection and protocol contracts; F28.2 Thin server handlers and service integration; F28.3 Security limits, errors and parity tests |
| F29 | F29.1 MCP client and tool discovery; F29.2 Host integration and controlled tool execution; F29.3 Timeout, disconnect and partial-failure validation |
| F30 | F30.1 Travel intent and context design; F30.2 Multi-source tool routing and itinerary composition; F30.3 Grounding, partial failures and end-to-end evaluation |
| F31 | F31.1 Release/version and deployment controls; F31.2 Unified data, application and AI observability; F31.3 Runbooks, recovery and operational readiness; F31.4 Portfolio evidence and release sign-off |

**Notion hierarchy:** create one parent page per feature and one child page per subfeature. Tasks remain checklists/sections inside the subfeature page unless a task itself becomes a separately managed deliverable. Do not create a Notion page for every small coding action.

**Feature learning/close-out:** after completing a feature, the user supplies the updated GitHub repository/feature reference and the Notion feature page reference. If either is missing, the AI must stop and request both before generating a consolidated feature page. The consolidated page is based on inspected code and verified evidence, and explains the feature’s purpose, architecture/data flow, important decisions, storage locations, implementation, tests, runtime results, limitations and lessons. The user reads it and creates a separate follow-up Q&A page; answers are written into that Q&A page unless the user explicitly requests chat answers. This is a learning/documentation workflow, not a substitute for implementation evidence in GitHub or `docs/progress.md`.

**Progress rule:** feature status is derived from its subfeatures. A feature is `Verified` only when every required subfeature is verified and the parent feature acceptance criteria pass. Deferred or optional subfeatures must be explicitly marked and justified; they cannot be silently treated as complete.

**Do not create city-specific copies of notebooks or services.** Source registries, reusable ingestion patterns, contracts and per-city manifests should carry the expansion.

## 8. City coverage strategy: 50-city target, 100-city-ready design

- **50-city target:** process eligible Inside Airbnb cities through detailed-listings Bronze and core Silver for a declared snapshot, with provenance, quality, reconciliation and runtime evidence. This target is reached when F17 is completed in roadmap order; it is not a calendar deadline.
- **Candidate pool:** inspect the live catalogue and select a buffer (for example, 60–70 candidates) because cities may lack a current snapshot or one or more source files.
- **100-city readiness:** keep city/source registries, contracts, run controls, table keys and batch execution configuration-driven. A 100-city target is a design/capacity review, not a claim of processed coverage.
- **No city-specific code:** do not create a notebook, transformation or service copy for each city. Use city IDs, source manifests, shared contracts and per-city run records.
- **Incremental execution:** pilot a small number of representative cities, then expand batch size only after measuring actual resource use and reliability.
- **Failure isolation:** track each city × source file × snapshot independently. Failed units can be retried without rewriting successful cities.
- **Source availability:** a configured city is not a loaded city. `not_published`, `not_available`, `schema_invalid`, `failed`, `loaded` and `validated` are different outcomes.

A city counts toward the 50-city core target only when detailed listings have a valid source snapshot, a successful Bronze output, a successful core Silver output and reconciliation evidence. Secondary file classes have independent statuses and must not be inferred from the detailed-listings status.

| Dimension | Example statuses |
|---|---|
| City eligibility | candidate, eligible, excluded, pending_review |
| Airbnb city/snapshot/listings | discovered, available, downloaded, bronze_loaded, silver_validated, partial, stale, failed, schema_invalid |
| Airbnb secondary file | available, loaded, not_published, not_available, partial, failed, schema_invalid |
| Overture city/release | not_checked, available, loaded, partial, failed, stale |
| Transit agency/feed | discovered, terms_reviewed, active, expired, invalid, unavailable |
| Weather location | supported, throttled, provider_error, stale_cache, unsupported_horizon |
| Documents | curated, indexed, stale, expired, terms_pending, unavailable |

A city may be Airbnb-supported but have no verified GTFS feed, or have places data but few curated documents. Report capabilities independently instead of showing one misleading `supported=true` flag.

## 9. Production-oriented quality, CI/CD and monitoring

These capabilities are **part of the project from the foundation onward**. They are not a final feature to bolt on after the application works.

### 9.1 CI/CD and software quality

Start with GitHub as the source of truth and pull-request checks. Expand deployment automation as the workspace and permissions allow.

Minimum CI baseline:
- Ruff formatting/linting and pytest.
- Configuration/schema/contract validation.
- Unit tests using small fixtures; integration tests that can run without a production dataset.
- Notebook/source validation where relevant.
- Dependency and secret checks appropriate to the repository.
- Pull-request status checks before merge.

Databricks delivery path:
- Keep notebook and Python logic source-controlled.
- Use Databricks Declarative Automation Bundles (formerly Asset Bundles) when supported, to define Jobs/pipelines/app resources as code.
- Validate bundle configuration in CI.
- Deploy to a development target only when credentials and workspace capabilities are available.
- Keep production-like targets as configuration until a real permitted environment exists; do not claim a production deployment from a local or Free Edition demo.
- Prefer short-lived workload identity/OIDC when an eligible account/environment supports it; never commit tokens or secrets.

### 9.2 Data monitoring

Monitor at least:
- Pipeline/job success, failure, duration and retry outcomes.
- Source freshness and snapshot/feed/document age.
- Expected versus received files and city/source coverage.
- Input, accepted, excluded, duplicate and output row counts.
- Schema drift, nulls, invalid coordinates, invalid prices and broken relationships.
- Gold product freshness and row-count/metric anomalies.
- API cache hit, provider error, rate-limit and stale-response state.

Use Databricks job/pipeline event logs and built-in monitoring where available. Build lightweight Delta/SQL metrics and Streamlit/SQL reports as a portable baseline. Do not assume every enterprise monitoring feature is available in Free Edition.

### 9.3 Application and AI monitoring

Log safe, structured telemetry with request/correlation ID, timestamp, app version, model/provider ID, prompt/template version, selected tools, validated arguments (redacted as needed), tool status, latency, response status, token/usage values where provided, retrieval/index version and error class.

Monitor:
- UI/service latency and error rates.
- Tool selection, argument validation failures and tool execution errors.
- LLM timeout/provider errors and token/usage patterns where available.
- RAG retrieval latency, index freshness/sync failures, source diversity and no-answer rate.
- Agent loop count, tool-call count and partial-failure handling.

Do not log unnecessary personal data, secrets, full traveller profiles or raw documents. Keep evaluation datasets separate from production traces and redact user content before using it in tests.

### 9.4 AI evaluation

Keep separate test/evaluation layers:

1. **Service correctness:** does the underlying function return the correct structured result?
2. **Tool evaluation:** did the LLM select the appropriate tool and provide valid arguments?
3. **Answer evaluation:** is the natural-language response faithful to the tool result and clear about caveats?
4. **RAG retrieval evaluation:** did the index retrieve relevant, valid, city-specific source passages?
5. **RAG answer evaluation:** are claims supported and sources attributed?
6. **Agent evaluation:** can the assistant clarify missing details, coordinate multiple tools, handle partial failure and avoid unsupported claims?

Version test cases, expected outcomes, model/prompt/tool versions and evaluation configuration. Report measurable results only from recorded test runs.

### 9.5 Operational readiness

Include runbooks for source failure, schema change, failed batch, index sync failure, provider quota/rate limit, stale cache, tool failure, bad deployment and rollback. Every release should have a tested commit, CI evidence, data/source versions and known limitations.

## 10. Databricks Free Edition strategy

Use Databricks Free Edition for personal learning and portfolio development as long as its capabilities and quotas are sufficient. The project should remain portable: code and source files must not exist only inside the workspace.

Current official documentation (checked November 11, 2026) lists serverless-only compute, limited notebook usage, one 2X-Small SQL warehouse, up to five concurrent job tasks, one active pipeline per pipeline type, restricted outbound internet, up to three Apps that automatically stop after 24 hours, and one AI Search endpoint with one search unit. Direct Vector Access is not supported in Free Edition. Fair-use quota exhaustion can make compute unavailable temporarily, and the workspace has no SLA/support guarantee. Features/limits may change; verify at implementation time.

Practical design:
- Download restricted source files outside Databricks and upload them through a supported workspace/Volume path.
- Process cities in controlled batches; do not assume 50-city jobs can all run concurrently.
- Build the Streamlit application locally first; treat Databricks Apps as an optional demo deployment.
- Use a Databricks AI Search Delta Sync index if it is enabled and suitable; verify creation, embedding access and synchronization in the actual workspace. Use a retrieval adapter so an alternative local/development vector store can be substituted if needed.
- Keep GitHub code, raw source backups, manifests and reproducible setup outside the workspace.
- Use Free Edition only for non-commercial personal work. Revisit paid/commercial hosting only when there is a real need.

Official references:
- https://docs.databricks.com/aws/en/getting-started/free-edition
- https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- https://docs.databricks.com/aws/en/dev-tools/ci-cd
- https://docs.databricks.com/aws/en/dev-tools/bundles/
- https://docs.databricks.com/aws/en/ai-search/create-ai-search
- https://docs.databricks.com/aws/en/ldp/observability

## 11. Target repository layout

This is a target layout, not a mandate to rewrite the existing repository. Preserve working migration code and current conventions; add folders only when a feature needs them.

```text
trippilot/
  .github/workflows/                 # CI and optional deploy workflows
  config/
    project.yml
    environments/
    sources/
    cities/
    gtfs_agencies/
    place_taxonomy.yml
  contracts/
    airbnb/ places/ gtfs/ weather/ documents/ services/ operations/
  src/
    common/ quality/ observability/
    acquisition/
    airbnb/ places/ gtfs/ weather/ documents/
    services/
    ai/
      tools/ rag/ evaluation/ tracing/
    mcp/
  notebooks/
    ops/ bronze/ silver/ gold/
  sql/
    verification/ monitoring/ gold/
  app/
    streamlit/
      pages/
  tests/
    unit/ contract/ integration/ fixtures/ evaluation/
  evals/
    datasets/ retrieval/ tools/ agent/
  docs/
    architecture/ decisions/ sources/ verification/ progress.md
  runbooks/
  databricks.yml                     # Declarative Automation Bundle when adopted
```

## 12. Portfolio evidence and resume claims

The project should provide evidence in stages.

### First Airbnb release
- One representative city processed through the intended available Airbnb file classes.
- Reusable ingestion and Bronze/Silver/Gold code, contracts and reconciliation.
- A documented listing data product and supporting calendar/review/neighbourhood insights where available.
- Python service layer and Streamlit accommodation explorer.
- Working LLM chatbot using structured tool calling over tested functions.
- Initial tool/answer evaluation set and trace examples.
- GitHub Actions CI checks, architecture diagram, setup instructions and limitations.

### Full integrated platform
- Multi-city coverage report toward 50, then 100-ready configuration.
- Overture lodging/food/attraction data products with source and taxonomy lineage.
- Selected GTFS feeds and schedule service with correct calendars/time zones.
- Weather service/cache and freshness controls.
- Curated official document corpus, chunking, embeddings, vector index and RAG evaluation.
- MCP server/client and multi-source travel assistant.
- Data, app, retrieval and agent monitoring with operational runbooks.
- Repeatable tests, release evidence, rollback/recovery notes and measured evaluation outcomes.

Possible first-release resume framing (use only after verified):

> Built an Airbnb-focused Databricks lakehouse and conversational discovery application, implementing reusable Bronze/Silver/Gold pipelines, source-versioned ingestion, data quality and reconciliation, Python query services, Streamlit exploration and LLM tool calling with evaluation and CI checks.

Possible full-project resume framing (use only after verified):

> Developed a multi-source travel lakehouse and grounded AI assistant integrating accommodation, global place discovery, selected GTFS transit, weather and official destination documents, with vector retrieval, MCP tool integration, CI/CD, monitoring and layered AI evaluation.

Never claim 50 or 100 cities, complete source coverage, production deployment or quality scores unless supported by progress records and test evidence.

## 13. Explicitly out of scope unless justified

- Airbnb booking, reservation, payment or live inventory functionality.
- Hotel rates/booking availability without a licensed source designed for that purpose.
- Treating calendar observations as real occupancy or confirmed bookings.
- Treating static GTFS as live arrivals.
- Treating Overture place records as verified opening hours, endorsements, reviews or rates.
- A global event aggregation platform from day one.
- Embedding every structured row into the vector database.
- Arbitrary SQL generation by the LLM.
- Kubernetes, microservices, multi-agent architecture, model fine-tuning or training a custom foundation model without a demonstrated need.
- A second orchestration platform when Databricks Jobs/Lakeflow is sufficient.
- Building a new routing engine from scratch.

## 14. Source references and change control

Re-check source schemas, file availability, attribution, API terms and Databricks limits before implementation. The sources below are design references, not permanent guarantees.

- Inside Airbnb downloads: https://insideairbnb.com/get-the-data/
- Inside Airbnb policy: https://insideairbnb.com/data-policies/
- Overture Places guide: https://docs.overturemaps.org/guides/places/
- Overture Places schema: https://docs.overturemaps.org/schema/reference/places/place/
- Overture taxonomy: https://docs.overturemaps.org/guides/places/taxonomy/
- Overture licensing: https://docs.overturemaps.org/guides/attribution-and-licensing/
- GTFS overview: https://gtfs.org/documentation/overview/
- GTFS Schedule reference: https://gtfs.org/documentation/schedule/reference/
- Open-Meteo docs: https://open-meteo.com/en/docs
- Open-Meteo terms: https://open-meteo.com/en/terms
- Databricks Free Edition: https://docs.databricks.com/aws/en/getting-started/free-edition
- Databricks Free Edition limitations: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- Databricks CI/CD: https://docs.databricks.com/aws/en/dev-tools/ci-cd
- Declarative Automation Bundles: https://docs.databricks.com/aws/en/dev-tools/bundles/
- Databricks AI Search: https://docs.databricks.com/aws/en/ai-search/create-ai-search
- Databricks pipeline observability: https://docs.databricks.com/aws/en/ldp/observability




## 15. v30 feature decomposition and change control

v29 retains the feature → subfeature → task hierarchy and the complete 31-feature product scope carried forward from v28. Implementation follows F01 through F31 in order, with subfeatures completed in ascending order inside each feature. The detailed task breakdown and acceptance criteria are in `trippilot-build-guide-v29.md`.

- Project Plan owns product scope, architecture, source strategy and roadmap.
- Build Guide owns subfeature decomposition, implementation tasks, dependencies and acceptance criteria.
- `HOW_TO_USE.md` owns the working protocol for ChatGPT-assisted implementation.
- `docs/progress.md` in GitHub owns actual implementation status and verification evidence.

A Notion parent page represents a feature; each subfeature receives a child page. Keep implementation tasks within that child page unless a task has independent ownership, review or delivery requirements.
