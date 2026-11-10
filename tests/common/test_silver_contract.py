"""Tests for Airbnb Silver data rules and rejection handling."""
from pathlib import Path
import sys

start = Path.cwd().resolve()
ROOT = next(
    (p for p in [start, *start.parents]
     if (p / 'src').is_dir() and (p / 'config/project.yml').is_file()),
    None,
)
if ROOT is None:
    raise RuntimeError('Cannot locate repository root. Open this notebook inside the Databricks Git folder.')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print('Repository root:', ROOT)

from src.quality.contract_loader import get_table_rules, load_contract
from src.airbnb.transformations import (
    clean_price,
    deduplicate_listings,
    get_rejection_reason,
    separate_listings,
)


def test_clean_price_handles_common_formats():
    assert clean_price("$1,234.00") == 1234.0
    assert clean_price("$99") == 99.0
    assert clean_price("") is None
    assert clean_price(None) is None
    assert clean_price("not-a-price") is None


def test_missing_id_is_rejected():
    rules = load_contract("contracts/airbnb/silver_listings.yml")
    table_rules = get_table_rules(rules, "silver_listings")
    listing = {"id": "", "city": "toronto", "snapshot_date": "2026-09-16"}

    reason = get_rejection_reason(listing, table_rules)

    assert reason is not None
    assert "Missing required field: id" in reason


def test_valid_listing_is_accepted():
    rules = load_contract("contracts/airbnb/silver_listings.yml")
    table_rules = get_table_rules(rules, "silver_listings")
    listing = {
        "id": "123",
        "city": "toronto",
        "snapshot_date": "2026-09-16",
        "price": "$150.00",
        "currency": "CAD",
    }

    reason = get_rejection_reason(listing, table_rules)

    assert reason is None


def test_duplicate_ids_are_removed():
    listings = [
        {"id": "1", "city": "toronto"},
        {"id": "1", "city": "toronto"},
        {"id": "2", "city": "toronto"},
    ]

    unique_listings = deduplicate_listings(listings)

    assert len(unique_listings) == 2
    assert unique_listings[0]["id"] == "1"
    assert unique_listings[1]["id"] == "2"


def test_invalid_and_valid_listings_are_separated():
    rules = load_contract("contracts/airbnb/silver_listings.yml")
    table_rules = get_table_rules(rules, "silver_listings")
    listings = [
        {
            "id": "1",
            "city": "toronto",
            "snapshot_date": "2026-09-16",
        },
        {
            "id": "",
            "city": "toronto",
            "snapshot_date": "2026-09-16",
        },
    ]

    accepted, rejected = separate_listings(listings, table_rules)

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["rejection_reason"] == "Missing required field: id"
