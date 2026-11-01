# TripPilot progress

## Current status

| ID | Feature | Status | Notes |
|---|---|---|---|
| 1.1 | Inspect one city source | Merged | Toronto source inspected |
| 1.2 | One-city Bronze ingestion | Merged | Toronto Bronze table created with provenance |
| 1.3 | Make ingestion safe to rerun | Merged | Ingestion control and scoped replacement verified |
| 1.4 | Build one-city Silver | Merged | Cleans, validates, and deduplicates Toronto Bronze |

## Pipeline capability

- Airbnb one-city Bronze ingestion: working
- Rerun protection: working
- Airbnb one-city Silver cleaning: in progress
- Multi-city reuse: not started

## Coverage

| City | Snapshot | Bronze | Silver |
|---|---|---|---|
| Toronto | 2026-09-16 | Loaded | In progress |