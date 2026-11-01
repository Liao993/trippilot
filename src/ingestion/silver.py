"""
Reusable Silver-layer helpers for Airbnb listings.

Silver turns raw Bronze strings into typed, validated, deduplicated records.
These functions are intentionally small and testable without Spark.
"""

from typing import Any


def clean_price(value: str | None) -> float | None:
    """
    Convert an Airbnb price string into a numeric float.

    Airbnb prices can look like "$1,234.00", "$1,234", or "".
    Bronze keeps the original string; Silver decides how to interpret it.

    Args:
        value: Raw price string from Bronze.

    Returns:
        A float price, or None when the value cannot be parsed.
    """
    if value is None:
        return None

    # Remove currency symbols, commas, and surrounding whitespace.
    cleaned = (
        value
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    # An empty string is not a valid price.
    if cleaned == "":
        return None

    try:
        return float(cleaned)
    except ValueError:
        # Do not guess. Return None so the record can be quarantined.
        return None


def is_valid_listing(
    listing: dict[str, Any],
    required_identifier: str = "id",
) -> bool:
    """
    Check whether a listing has the minimum fields needed for Silver.

    Args:
        listing: One Bronze record represented as a dictionary.
        required_identifier: Name of the unique listing identifier.

    Returns:
        True when the listing has a non-empty identifier.
    """
    identifier = listing.get(required_identifier)

    # A missing, null, or blank ID cannot be trusted as a unique listing.
    return identifier is not None and str(identifier).strip() != ""


def deduplicate_listings(
    listings: list[dict[str, Any]],
    required_identifier: str = "id",
) -> list[dict[str, Any]]:
    """
    Remove duplicate listings while keeping the first occurrence.

    The first occurrence is deterministic because Bronze rows are read
    in a stable order for this one-file, one-city ingestion pattern.

    Args:
        listings: Bronze records represented as dictionaries.
        required_identifier: Field used to identify a unique listing.

    Returns:
        A list containing one record per unique listing ID.
    """
    seen_ids: set[str] = set()
    unique_listings: list[dict[str, Any]] = []

    for listing in listings:
        identifier = listing.get(required_identifier)

        # Skip records without a usable identifier.
        if identifier is None or str(identifier).strip() == "":
            continue

        # Convert to string so numeric and string IDs compare consistently.
        identifier_key = str(identifier).strip()

        if identifier_key in seen_ids:
            continue

        seen_ids.add(identifier_key)
        unique_listings.append(listing)

    return unique_listings