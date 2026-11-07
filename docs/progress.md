# TripPilot progress

## Current subfeature

Feature 1.5.2 — Silver data rules, rejection tracking, and quality checks

## Actual working environment and source paths

- Databricks catalog: `trippilot_dev`
- Bronze schema: `trippilot_dev.bronze`
- Silver schema: `trippilot_dev.silver`
- Source Volume: `/Volumes/trippilot_dev/bronze/source_files`
- Airbnb source: Inside Airbnb
- Current city: Toronto
- Snapshot date: `2026-09-16`
- Source file: `/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz`

## Verified setup

- The repository contains reusable Silver helpers in `src/ingestion/silver.py`.
- The current code cleans Airbnb price strings, checks for a listing ID, and removes duplicate listing IDs.
- The project configuration identifies Toronto as the first enabled city.

## Subfeature status

| ID | Status | Branch/PR | Tested revision | Evidence | Next task |
|---|---|---|---|---|---|
| 1.1 | In progress |  |  | Source configuration exists in `config/project.yml` | Confirm source fields and quality risks |
| 1.2 | In progress | `feature/1.5.2-silver-governance` |  | Silver rules and validation helpers added | Add Bronze and Gold rules later |
| 1.3 | In progress |  |  | Bronze ingestion helpers exist | Verify Bronze write in Databricks |
| 1.4 | In progress |  |  | Run-control helper exists | Verify rerun behaviour in Databricks |
| 1.5 | In progress | `feature/1.5.2-silver-governance` |  | Silver rules, rejection reasons, and separation logic added | Verify quarantine and quality results in Databricks |

## Pipeline capability

- Silver can identify listings that are missing required fields.
- Silver can identify invalid numeric values, such as an impossible price or coordinate.
- Silver can separate accepted listings from rejected listings.
- Rejected listings will include a readable rejection reason.
- Duplicate listing IDs are removed by keeping the first occurrence.

## City coverage (actual validated count)

- Toronto: configured, not yet fully verified in Databricks.

## Deferred work and reason

- Gold metrics and reconciliation are deferred until the Silver quality checks are verified.
- Databricks Job scheduling, alerting, and runbooks are deferred until the one-city pipeline is stable.

## Blockers

- None identified in the repository review.
