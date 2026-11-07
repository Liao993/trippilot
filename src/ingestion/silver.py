"""
Reusable Silver-layer helpers for Airbnb listings.

Silver turns raw Bronze strings into typed, validated, deduplicated records.
These functions are intentionally small and testable without Spark.
"""

from typing import Any

from src.contracts.validators import validate_listing


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

    cleaned = (
        value
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    if cleaned == "":
        return None

    try:
        return float(cleaned)
    except ValueError:
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

    return identifier is not None and str(identifier).strip() != ""


def is_rejected_listing(listing_id: str | None) -> bool:
    """
    Determine whether a listing should be rejected from Silver.

    A listing is rejected only when it has no usable identifier.
    Missing prices or coordinates are quality issues, not rejection reasons.

    Args:
        listing_id: Raw or cleaned listing identifier.

    Returns:
        True when the listing cannot be reliably identified.
    """
    return listing_id is None or str(listing_id).strip() == ""


def get_rejection_reason(
    listing: dict[str, Any],
    rules: dict[str, Any],
) -> str | None:
    """
    Return a short reason why a listing cannot enter Silver.

    Returns None when the listing passes all checks.
    """
    errors = validate_listing(listing, rules)

    if not errors:
        return None

    return "; ".join(errors)


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
        required_identifier: Field used to identify a unique listing ID.

    Returns:
        A list containing one record per unique listing ID.
    """
    seen_ids: set[str] = set()
    unique_listings: list[dict[str, Any]] = []

    for listing in listings:
        identifier = listing.get(required_identifier)

        if identifier is None or str(identifier).strip() == "":
            continue

        identifier_key = str(identifier).strip()

        if identifier_key in seen_ids:
            continue

        seen_ids.add(identifier_key)
        unique_listings.append(listing)

    return unique_listings


def separate_listings(
    listings: list[dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Split listings into accepted and rejected groups.

    Accepted listings can move to the Silver table.
    Rejected listings should be saved in quarantine with a reason.

    Args:
        listings: Bronze records represented as dictionaries.
        rules: Silver data rules loaded from the YAML contract.

    Returns:
        A tuple of (accepted listings, rejected listings).
    """
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for listing in listings:
        reason = get_rejection_reason(listing, rules)

        if reason is None:
            accepted.append(listing)
        else:
            rejected.append({**listing, "rejection_reason": reason})

    return accepted, rejected
