"""
Unit tests for the contract-driven row-quality policy (F06.2-T03).

The pure contract-extraction logic is tested against synthetic
contracts and the two REAL calendar/review contract files. The Spark
annotation itself only assembles native expressions (no Python row
logic) and is exercised by the F06.2 test-mode Databricks run.
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

import pytest

from src.airbnb.row_quality import extract_row_validation_policy
from src.quality.contract_loader import load_contract


def _contract(policy=None, rules_key="bronze_x"):
    rules = {"table": "a.b.c", "required_columns": ["a"]}
    if policy is not None:
        rules["row_validation"] = policy
    return {rules_key: rules}


def test_extracts_policy_from_real_calendar_contract():
    contract = load_contract(ROOT / "contracts/airbnb/bronze_calendar.yml")
    required, date_fields = extract_row_validation_policy(contract, "bronze_calendar")
    assert required == ["listing_id", "date"]
    assert date_fields == ["date"]


def test_extracts_policy_from_real_reviews_contract():
    contract = load_contract(ROOT / "contracts/airbnb/bronze_reviews.yml")
    required, date_fields = extract_row_validation_policy(contract, "bronze_reviews")
    assert required == ["listing_id", "id", "date"]
    assert date_fields == ["date"]


def test_missing_row_validation_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy(_contract(), "bronze_x")


def test_row_validation_not_a_mapping_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy(_contract(["listing_id"]), "bronze_x")


def test_missing_rules_key_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy({"bronze_x": {}}, "bronze_other")


def test_empty_required_fields_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy(
            _contract({"required_fields": [], "date_fields": []}), "bronze_x"
        )


def test_blank_required_field_name_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy(
            _contract({"required_fields": ["  "], "date_fields": []}), "bronze_x"
        )


def test_bad_date_fields_type_raises():
    with pytest.raises(TypeError):
        extract_row_validation_policy(
            _contract({"required_fields": ["listing_id"], "date_fields": "date"}),
            "bronze_x",
        )


def test_date_fields_must_be_subset_of_required():
    with pytest.raises(TypeError):
        extract_row_validation_policy(
            _contract({"required_fields": ["listing_id"], "date_fields": ["date"]}),
            "bronze_x",
        )


def test_empty_date_fields_are_allowed():
    required, date_fields = extract_row_validation_policy(
        _contract({"required_fields": ["listing_id"], "date_fields": []}), "bronze_x"
    )
    assert required == ["listing_id"]
    assert date_fields == []
