"""Fixture-based tests for Airbnb Silver exclusion rules.

The fixtures are small synthetic listings in the repository's existing
inline-dict convention. The rules come from the real Silver contract
(contracts/airbnb/silver_listings.yml), so the tests exercise the actual
contract behaviour at its boundaries without production data, Spark, or
Databricks access.
"""

import sys
from pathlib import Path

start = Path.cwd().resolve()
ROOT = next(
    (
        p
        for p in [start, *start.parents]
        if (p / "src").is_dir() and (p / "config/project.yml").is_file()
    ),
    None,
)
if ROOT is None:
    raise RuntimeError(
        "Cannot locate repository root. Open this notebook inside the Databricks Git folder."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print("Repository root:", ROOT)

from src.quality.contract_loader import get_table_rules, load_contract
from src.quality.exclusion import get_exclusion_reason
from src.quality.record_validation import validate_listing


def _silver_rules():
    return get_table_rules(
        load_contract(ROOT / "contracts/airbnb/silver_listings.yml"),
        "silver_listings",
    )


def _valid_listing():
    return {
        "id": "123",
        "city": "toronto",
        "snapshot_date": "2026-09-16",
        "price": 150.0,
        "currency": "CAD",
        "latitude": 43.65,
        "longitude": -79.38,
    }


def test_valid_listing_passes_all_rules():
    assert get_exclusion_reason(_valid_listing(), _silver_rules()) is None


def test_listing_at_numeric_boundaries_passes():
    # Boundary values from the contract: price minimum 0, latitude
    # [-90, 90], longitude [-180, 180].
    listing = _valid_listing()
    listing.update({"price": 0, "latitude": -90, "longitude": 180})

    assert get_exclusion_reason(listing, _silver_rules()) is None


def test_missing_required_id_is_rejected():
    listing = _valid_listing()
    listing["id"] = ""

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Missing required field: id" in reason


def test_missing_required_snapshot_date_is_rejected():
    listing = _valid_listing()
    listing["snapshot_date"] = None

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Missing required field: snapshot_date" in reason


def test_unparseable_price_is_rejected():
    listing = _valid_listing()
    listing["price"] = "not-a-price"

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Invalid numeric value for price: not-a-price" in reason


def test_negative_price_is_rejected():
    listing = _valid_listing()
    listing["price"] = -5

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "price is below the minimum allowed value" in reason


def test_latitude_above_maximum_is_rejected():
    listing = _valid_listing()
    listing["latitude"] = 90.5

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "latitude is above the maximum allowed value" in reason


def test_longitude_below_minimum_is_rejected():
    listing = _valid_listing()
    listing["longitude"] = -180.5

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "longitude is below the minimum allowed value" in reason


def test_city_outside_allowed_values_is_rejected():
    listing = _valid_listing()
    listing["city"] = "vancouver"

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Invalid value for city: vancouver" in reason


def test_currency_outside_allowed_values_is_rejected():
    listing = _valid_listing()
    listing["currency"] = "USD"

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Invalid value for currency: USD" in reason


def test_multiple_errors_are_joined_in_one_reason():
    listing = _valid_listing()
    listing["id"] = ""
    listing["city"] = "vancouver"

    reason = get_exclusion_reason(listing, _silver_rules())

    assert reason is not None
    assert "Missing required field: id" in reason
    assert "Invalid value for city: vancouver" in reason
    assert "; " in reason


def test_validate_listing_returns_list_of_errors():
    listing = _valid_listing()
    listing["id"] = ""

    errors = validate_listing(listing, _silver_rules())

    assert isinstance(errors, list)
    assert len(errors) == 1
    assert errors[0] == "Missing required field: id"
