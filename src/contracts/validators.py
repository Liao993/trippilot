"""Check Airbnb Silver records against simple, readable data rules."""

from typing import Any


def check_required_field(record: dict[str, Any], field: str) -> str | None:
    """Return an error message when a required field is missing or blank."""
    value = record.get(field)

    if value is None or str(value).strip() == "":
        return f"Missing required field: {field}"

    return None


def check_numeric_field(
    record: dict[str, Any],
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> str | None:
    """Return an error message when an optional numeric field is invalid."""
    value = record.get(field)

    if value is None or str(value).strip() == "":
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"Invalid numeric value for {field}: {value}"

    if minimum is not None and number < minimum:
        return f"{field} is below the minimum allowed value: {number}"

    if maximum is not None and number > maximum:
        return f"{field} is above the maximum allowed value: {number}"

    return None


def check_allowed_values(
    record: dict[str, Any],
    field: str,
    allowed_values: list[str],
) -> str | None:
    """Return an error message when a value is not on the allowed list."""
    value = record.get(field)

    if value is None or str(value).strip() == "":
        return None

    if str(value) not in allowed_values:
        return f"Invalid value for {field}: {value}"

    return None


def validate_listing(
    listing: dict[str, Any],
    rules: dict[str, Any],
) -> list[str]:
    """Return all validation errors for one Airbnb listing."""
    errors: list[str] = []
    column_rules = rules.get("rules", {})

    for field, field_rules in column_rules.items():
        if field_rules.get("required"):
            error = check_required_field(listing, field)
            if error:
                errors.append(error)

        if "allowed_values" in field_rules:
            error = check_allowed_values(
                listing,
                field,
                field_rules["allowed_values"],
            )
            if error:
                errors.append(error)

        if field_rules.get("type") in {"decimal", "double", "float"}:
            error = check_numeric_field(
                listing,
                field,
                field_rules.get("minimum"),
                field_rules.get("maximum"),
            )
            if error:
                errors.append(error)

    return errors
