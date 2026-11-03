# Feature 1.4 revision — Silver validation review

## What changed

- A usable `listing_id` is now the only hard Silver requirement.
- Listings with missing prices or coordinates remain in Silver.
- Added `has_valid_price` and `has_valid_coordinates` quality flags.
- Replaced `subtract()` with explicit valid/rejected filters.
- Made duplicate handling deterministic using the latest Bronze ingestion.
- Renamed `airbnb_listings_quarantine` to `airbnb_listings_rejected`.

## Verification

- Bronze filtered input: [count]
- Valid Silver candidates before deduplication: [count]
- Rejected rows: [count]
- Duplicate valid rows removed: [count]
- Final Silver rows: [count]
- Reconciliation passed: yes/no

## Data-quality observations

- Listings with missing price: [count]
- Listings with missing coordinates: [count]
- Listings missing both: [count]

## Decision

Listings with missing price or coordinates remain in Silver because they can still support non-price and non-map analyses. Future Gold metrics must respect the quality flags.