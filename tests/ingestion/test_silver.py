"""
Unit tests for Airbnb Silver transformation helpers.

These tests use small hardcoded inputs so failures are easy to understand.
They do not require Spark, Databricks, or the real Toronto file.
"""

from src.ingestion.silver import (
    clean_price,
    deduplicate_listings,
    is_valid_listing,
)


def test_clean_price_handles_currency_and_commas():
    assert clean_price("$1,234.00") == 1234.0


def test_clean_price_handles_plain_number():
    assert clean_price("150") == 150.0


def test_clean_price_returns_none_for_blank_value():
    assert clean_price("") is None


def test_clean_price_returns_none_for_invalid_value():
    assert clean_price("not-a-price") is None


def test_is_valid_listing_accepts_non_blank_id():
    listing = {"id": "123", "price": "$150.00"}

    assert is_valid_listing(listing) is True


def test_is_valid_listing_rejects_blank_id():
    listing = {"id": " ", "price": "$150.00"}

    assert is_valid_listing(listing) is False


def test_deduplicate_listings_keeps_first_record():
    listings = [
        {"id": "1", "price": "$100.00"},
        {"id": "1", "price": "$120.00"},
        {"id": "2", "price": "$150.00"},
    ]

    result = deduplicate_listings(listings)

    assert len(result) == 2
    assert result[0]["price"] == "$100.00"
    assert result[1]["id"] == "2"


def test_deduplicate_listings_skips_missing_ids():
    listings = [
        {"id": None, "price": "$100.00"},
        {"id": "1", "price": "$120.00"},
    ]

    result = deduplicate_listings(listings)

    assert len(result) == 1
    assert result[0]["id"] == "1"