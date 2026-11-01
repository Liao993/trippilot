# TripPilot progress

## Current subfeature

Feature 1.1 — Inspect one city source

## Actual working environment

- Catalog: `trippilot_dev`
- Source Volume path: `/Volumes/trippilot_dev/bronze/source_files`
- Source: Inside Airbnb
- City inspected: Toronto
- Raw file: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz`

## Feature 1.1 status

| ID | Status | Branch/PR | Tested revision | Evidence | Next task |
|---|---|---|---|---|---|
| 1.1 | In progress | feature/1-1-inspect-airbnb-source |  | Databricks inspection notebook run | Document schema, identifiers, and quality findings |

## Findings

- File format: compressed CSV (`.csv.gz`)
- Listing identifier: `id`
- Row count:22050
- Distinct listing IDs:22050
- Null or blank IDs: 0
- Snapshot/source date: "2026-09-17"
- Key quality observations: No

## Feature 1.2 status

| ID | Status | Branch/PR | Tested revision | Evidence | Next task |
|---|---|---|---|---|---|
| 1.2 | In progress | feature/1-2-airbnb-bronze |  | Databricks test and Bronze table verification | Record final row count and merge PR |

## Bronze ingestion evidence

- Source: Inside Airbnb
- City: Toronto
- Snapshot date: 2026-09-16
- Raw path: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz`
- Bronze table: `trippilot_dev.bronze.airbnb_listings_bronze`
- Raw input rows: 22050
- Bronze output rows: 22050
- Run ID: af3fd5312cf44516b98ce7955449438d
- Verification: Raw and Bronze row counts match; provenance columns populated.