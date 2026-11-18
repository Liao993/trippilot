"""
Contract-driven row-quality annotation for the Airbnb Bronze paths (F06.2).

F06.2-T03 validates the required identifier/date fields declared by
the observed source contracts - WITHOUT dropping, casting or
quarantining anything. Invalid rows stay in Bronze, marked with an
explicit reason, so Silver (F08/F09) and quality reporting can act on
them later.
"""

from typing import Any

# Dates in the observed calendar/review files are ISO YYYY-MM-DD. The
# check runs on the RAW string: a non-conforming value is flagged,
# never coerced (that is Silver's job).
_ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def extract_row_validation_policy(
    contract: dict[str, Any],
    rules_key: str,
) -> tuple[list[str], list[str]]:
    """
    Return (required_fields, date_fields) from a Bronze contract.

    The policy comes from the contract file, never from hard-coded
    column names, so a drifting or corrected source schema is caught
    by the contract gates instead of silently passing here.

    Raises:
        TypeError: When the contract lacks a well-formed row_validation
            block for this rules key.
    """
    rules = contract.get(rules_key)
    if not isinstance(rules, dict):
        raise TypeError(
            f"contract rules key {rules_key!r} is missing or is not a mapping"
        )

    policy = rules.get("row_validation")
    if not isinstance(policy, dict):
        raise TypeError(f"{rules_key}.row_validation is missing or is not a mapping")

    required = policy.get("required_fields")
    if not isinstance(required, list) or not required:
        raise TypeError(
            f"{rules_key}.row_validation.required_fields must be a non-empty "
            "list of column names"
        )
    if not all(isinstance(field, str) and field.strip() for field in required):
        raise TypeError(
            f"{rules_key}.row_validation.required_fields must contain only "
            "non-empty column names"
        )

    date_fields = policy.get("date_fields", [])
    if not isinstance(date_fields, list) or not all(
        isinstance(field, str) and field.strip() for field in date_fields
    ):
        raise TypeError(
            f"{rules_key}.row_validation.date_fields must be a list of column names"
        )
    if any(field not in required for field in date_fields):
        raise TypeError(
            f"{rules_key}.row_validation.date_fields must be a subset of "
            "required_fields"
        )

    return list(required), list(date_fields)


def annotate_row_quality(df, required_fields: list[str], date_fields: list[str]):
    """
    Add ``_quality_status`` and ``_quality_reason`` columns to a raw DataFrame.

    A field listed in required_fields is flagged ``missing <field>``
    when null or blank; a field also listed in date_fields is flagged
    ``invalid <field> format`` when present but not ISO YYYY-MM-DD. Rows
    are never dropped or modified - only the two metadata columns are
    added. Multiple problems on one row are joined with '; '. The
    annotation is pure metadata: values keep their raw string form.

    The pyspark import stays inside the function so CI (which has no
    Spark) can import this module for the contract-policy tests.
    """
    from pyspark.sql import functions as F

    reason_columns = []
    for field in required_fields:
        value = F.col(field)
        is_missing = value.isNull() | (F.trim(value) == "")
        reason_columns.append(F.when(is_missing, F.lit(f"missing {field}")))
        if field in date_fields:
            is_present = value.isNotNull() & (F.trim(value) != "")
            bad_format = is_present & ~value.rlike(_ISO_DATE_PATTERN)
            reason_columns.append(F.when(bad_format, F.lit(f"invalid {field} format")))

    reason = F.concat_ws("; ", *reason_columns)
    return df.withColumn("_quality_reason", reason).withColumn(
        "_quality_status",
        F.when(F.length(reason) == 0, F.lit("valid")).otherwise(F.lit("invalid")),
    )
