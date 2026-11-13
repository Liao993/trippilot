"""Tests for populated YAML configuration and contract validation.

These tests use small hardcoded inputs on purpose. They check the exact
structure rules without needing Spark, Databricks, a Volume, or real tables.
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

from src.quality.config_validation import (
    validate_bronze_contract,
    validate_city_registry,
    validate_config_files,
    validate_project_config,
    validate_silver_contract,
)

PROJECT_CONFIG = {
    "project": {"name": "trippilot", "owner": "Henry"},
    "databricks": {
        "catalog": "trippilot_dev",
        "schemas": {"bronze": "bronze", "silver": "silver", "gold": "gold"},
    },
    "sources": {
        "airbnb": {
            "provider": "insideairbnb",
            "cities": {
                "toronto": {
                    "enabled": True,
                    "raw_path": "/Volumes/trippilot_dev/bronze/source_files/x.csv.gz",
                    "required_identifier": "id",
                }
            },
        }
    },
}

CITY_REGISTRY = {"cities": [{"city": "toronto", "enabled": True}]}

BRONZE_CONTRACT = {
    "bronze_listings": {
        "table": "trippilot_dev.bronze.airbnb_listings_bronze",
        "source": "insideairbnb",
        "required_columns": ["id", "name", "price"],
        "source_types": "string",
        "write_policy": "replace_city_snapshot",
    }
}

SILVER_CONTRACT = {
    "silver_listings": {
        "table": "trippilot_dev.silver.airbnb_listings_silver",
        "business_key": ["listing_id", "city", "snapshot_date"],
        "required_columns": ["listing_id", "city", "snapshot_date"],
        "rules": {
            "id": {"required": True, "type": "string", "allow_empty": False},
            "price": {"required": False, "type": "decimal", "minimum": 0},
        },
    }
}


def test_valid_project_config_passes():
    assert validate_project_config(PROJECT_CONFIG) == []


def test_missing_project_name_is_reported():
    broken = {**PROJECT_CONFIG, "project": {"owner": "Henry"}}
    errors = validate_project_config(broken)
    assert len(errors) == 1
    assert "config/project.yml" in errors[0]
    assert "project.name" in errors[0]


def test_missing_databricks_sections_are_reported():
    errors = validate_project_config({"project": {"name": "trippilot"}})
    assert any("'databricks'" in error for error in errors)
    assert any("'sources'" in error for error in errors)


def test_empty_databricks_schemas_is_reported():
    broken = {
        **PROJECT_CONFIG,
        "databricks": {"catalog": "trippilot_dev", "schemas": {}},
    }
    errors = validate_project_config(broken)
    assert any("databricks.schemas" in error for error in errors)


def test_valid_city_registry_passes():
    assert validate_city_registry(CITY_REGISTRY) == []


def test_empty_cities_list_is_reported():
    errors = validate_city_registry({"cities": []})
    assert len(errors) == 1
    assert "'cities'" in errors[0]


def test_city_entry_missing_enabled_is_reported():
    broken = {"cities": [{"city": "toronto"}]}
    errors = validate_city_registry(broken)
    assert len(errors) == 1
    assert "cities[0]" in errors[0]
    assert "enabled" in errors[0]


def test_city_entry_with_blank_name_is_reported():
    broken = {"cities": [{"city": "   ", "enabled": True}]}
    errors = validate_city_registry(broken)
    assert any("'city'" in error for error in errors)


def test_valid_bronze_contract_passes():
    assert validate_bronze_contract(BRONZE_CONTRACT) == []


def test_bronze_missing_required_columns_is_reported():
    broken = {"bronze_listings": {"table": "a.b.c", "source": "insideairbnb"}}
    errors = validate_bronze_contract(broken)
    assert len(errors) == 1
    assert "bronze_listings.required_columns" in errors[0]


def test_bronze_missing_table_section_is_reported():
    errors = validate_bronze_contract({})
    assert len(errors) == 1
    assert "bronze_listings.yml" in errors[0]


def test_bronze_empty_column_list_is_reported():
    broken = {
        "bronze_listings": {
            **BRONZE_CONTRACT["bronze_listings"],
            "required_columns": [],
        }
    }
    errors = validate_bronze_contract(broken)
    assert any("required_columns" in error for error in errors)


def test_valid_silver_contract_passes():
    assert validate_silver_contract(SILVER_CONTRACT) == []


def test_silver_empty_business_key_is_reported():
    broken = {
        "silver_listings": {**SILVER_CONTRACT["silver_listings"], "business_key": []}
    }
    errors = validate_silver_contract(broken)
    assert any("business_key" in error for error in errors)


def test_silver_missing_rules_is_reported():
    broken = {"silver_listings": {**SILVER_CONTRACT["silver_listings"], "rules": {}}}
    errors = validate_silver_contract(broken)
    assert any("silver_listings.rules" in error for error in errors)


def test_silver_non_mapping_rule_is_reported():
    broken = {
        "silver_listings": {
            **SILVER_CONTRACT["silver_listings"],
            "rules": {"id": "required"},
        }
    }
    errors = validate_silver_contract(broken)
    assert len(errors) == 1
    assert "silver_listings.rules.id" in errors[0]


def test_validate_config_files_passes_on_real_repo_files():
    validate_config_files(ROOT)


def test_validate_config_files_reports_invalid_yaml(tmp_path):
    valid_project_yml = (
        "project:\n"
        "  name: trippilot\n"
        "databricks:\n"
        "  catalog: trippilot_dev\n"
        "  schemas:\n"
        "    bronze: bronze\n"
        "sources:\n"
        "  airbnb:\n"
        "    provider: insideairbnb\n"
        "    cities:\n"
        "      toronto:\n"
        "        enabled: true\n"
    )
    valid_bronze_yml = (
        "bronze_listings:\n"
        "  table: a.b.c\n"
        "  source: insideairbnb\n"
        "  required_columns:\n"
        "    - id\n"
    )
    valid_silver_yml = (
        "silver_listings:\n"
        "  table: a.b.c\n"
        "  business_key:\n"
        "    - listing_id\n"
        "  required_columns:\n"
        "    - listing_id\n"
        "  rules:\n"
        "    id:\n"
        "      required: true\n"
        "      type: string\n"
    )

    (tmp_path / "config").mkdir()
    (tmp_path / "contracts").mkdir()
    (tmp_path / "config/project.yml").write_text(valid_project_yml, encoding="utf-8")
    (tmp_path / "config/city_registry.yml").write_text(
        "cities: [unclosed", encoding="utf-8"
    )
    for rel in [
        "contracts/airbnb/bronze_listings.yml",
        "contracts/airbnb/silver_listings.yml",
    ]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "contracts/airbnb/bronze_listings.yml").write_text(
        valid_bronze_yml, encoding="utf-8"
    )
    (tmp_path / "contracts/airbnb/silver_listings.yml").write_text(
        valid_silver_yml, encoding="utf-8"
    )

    with pytest.raises(ValueError) as excinfo:
        validate_config_files(tmp_path)
    assert "invalid YAML" in str(excinfo.value)
    assert "config/city_registry.yml" in str(excinfo.value)


def test_validate_config_files_reports_missing_file(tmp_path):
    with pytest.raises(ValueError) as excinfo:
        validate_config_files(tmp_path)
    message = str(excinfo.value)
    for rel in [
        "config/project.yml",
        "config/city_registry.yml",
        "contracts/airbnb/bronze_listings.yml",
        "contracts/airbnb/silver_listings.yml",
    ]:
        assert rel in message
    assert "required file is missing" in message
