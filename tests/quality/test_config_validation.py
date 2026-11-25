"""Tests for populated YAML configuration and contract validation.

These tests use small hardcoded inputs on purpose. They check the exact
structure rules without needing Spark, Databricks, a Volume, or real tables.
"""

import copy
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
import yaml

from src.quality.config_validation import (
    SILVER_COLUMN_FROM_VALUES,
    SILVER_COLUMN_PARSE_VALUES,
    is_supported_column_type,
    validate_bronze_contract,
    validate_city_registry,
    validate_config_files,
    validate_project_config,
    validate_silver_contract,
    validate_source_city_registration,
    validate_source_manifest_contract,
)

PROJECT_CONFIG = {
    "project": {"name": "trippilot", "owner": "Henry"},
    "databricks": {
        "catalog": "trippilot_dev",
        "schemas": {"bronze": "bronze", "gold": "gold"},
    },
    "sources": {
        "airbnb": {
            "provider": "insideairbnb",
            "source_url": "https://insideairbnb.com/get-the-data/",
            "cities": {
                "toronto": {
                    "datasets": {
                        "listings": {
                            "file": "listings.csv.gz",
                            "file_type": "csv.gz",
                            "required_identifier": "id",
                        }
                    }
                }
            },
        }
    },
}

CITY_REGISTRY = {
    "version": 1,
    "cities": [
        {
            "city_id": "toronto",
            "slug": "toronto",
            "display_name": "Toronto",
            "country_code": "CA",
            "region": "Ontario",
            "timezone": "America/Toronto",
            "currency": "CAD",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "enabled": True,
        }
    ],
}

BRONZE_CONTRACT = {
    "bronze_listings": {
        "table": "trippilot_dev.bronze.airbnb_listings_bronze",
        "source": "insideairbnb",
        "required_columns": ["id", "name", "price"],
        "source_types": "string",
        "write_policy": "replace_city_snapshot",
    }
}

CALENDAR_CONTRACT = {
    "bronze_calendar": {
        "table": "trippilot_dev.bronze.airbnb_calendar_bronze",
        "source": "insideairbnb",
        "required_columns": ["listing_id", "date", "available"],
        "source_types": "string",
        "write_policy": "replace_city_snapshot",
    }
}

REVIEWS_CONTRACT = {
    "bronze_reviews": {
        "table": "trippilot_dev.bronze.airbnb_reviews_bronze",
        "source": "insideairbnb",
        "required_columns": ["listing_id", "id", "date"],
        "source_types": "string",
        "write_policy": "replace_city_snapshot",
    }
}

MANIFEST_CONTRACT = {
    "states": ["registered", "validated", "landed", "failed"],
    "valid_transitions": {
        "registered": ["validated", "failed"],
        "validated": ["landed", "failed"],
        "landed": [],
        "failed": [],
    },
    "supported_file_types": ["csv", "csv.gz", "parquet"],
    "max_byte_size": 2147483648,
    "fields": {
        "source_file_id": {"type": "string", "required": True},
        "source_family": {"type": "string", "required": True},
        "source_entity_id": {"type": "string", "required": True},
        "source_version": {"type": "string", "required": True},
        "file_type": {"type": "string", "required": True},
        "dataset": {"type": "string", "required": False},
        "source_url": {"type": "string", "required": True},
        "retrieved_at_utc": {"type": "string", "required": True},
        "file_hash_sha256": {"type": "string", "required": True},
        "byte_size": {"type": "integer", "required": True},
        "schema_version": {"type": "string", "required": True},
        "license": {"type": "string", "required": True},
        "attribution": {"type": "string", "required": True},
        "source_path": {"type": "string", "required": True},
        "landing_path": {"type": "string", "required": False},
        "run_id": {"type": "string", "required": True},
        "processing_state": {"type": "string", "required": True},
        "error_message": {"type": "string", "required": False},
        "error_type": {"type": "string", "required": False},
    },
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


def test_project_city_enabled_flag_is_rejected():
    toronto = {**PROJECT_CONFIG["sources"]["airbnb"]["cities"]["toronto"]}
    toronto["enabled"] = True
    broken = {
        **PROJECT_CONFIG,
        "sources": {
            "airbnb": {
                **PROJECT_CONFIG["sources"]["airbnb"],
                "cities": {"toronto": toronto},
            }
        },
    }

    errors = validate_project_config(broken)

    assert any(
        "city enablement lives ONLY in config/city_registry.yml" in error
        for error in errors
    )


def test_project_missing_source_url_is_reported():
    family = {
        key: value
        for key, value in PROJECT_CONFIG["sources"]["airbnb"].items()
        if key != "source_url"
    }
    broken = {**PROJECT_CONFIG, "sources": {"airbnb": family}}

    errors = validate_project_config(broken)

    assert any("source_url" in error for error in errors)


def test_project_empty_datasets_is_reported():
    toronto = {"datasets": {}}
    broken = {
        **PROJECT_CONFIG,
        "sources": {
            "airbnb": {
                **PROJECT_CONFIG["sources"]["airbnb"],
                "cities": {"toronto": toronto},
            }
        },
    }

    errors = validate_project_config(broken)

    assert any("datasets" in error for error in errors)


def test_project_dataset_bad_file_type_is_reported():
    datasets = {**PROJECT_CONFIG["sources"]["airbnb"]["cities"]["toronto"]["datasets"]}
    datasets["listings"] = {**datasets["listings"], "file_type": "gzip"}
    broken = {
        **PROJECT_CONFIG,
        "sources": {
            "airbnb": {
                **PROJECT_CONFIG["sources"]["airbnb"],
                "cities": {
                    "toronto": {
                        "datasets": datasets,
                    }
                },
            }
        },
    }

    errors = validate_project_config(broken)

    assert any("file_type" in error for error in errors)


def test_project_dataset_file_name_type_mismatch_is_reported():
    datasets = {**PROJECT_CONFIG["sources"]["airbnb"]["cities"]["toronto"]["datasets"]}
    datasets["listings"] = {**datasets["listings"], "file": "listings.csv"}
    broken = {
        **PROJECT_CONFIG,
        "sources": {
            "airbnb": {
                **PROJECT_CONFIG["sources"]["airbnb"],
                "cities": {
                    "toronto": {
                        "datasets": datasets,
                    }
                },
            }
        },
    }

    errors = validate_project_config(broken)

    assert any("does not end with the declared file_type" in error for error in errors)


def test_source_city_registration_passes_for_registered_city():
    assert validate_source_city_registration(PROJECT_CONFIG, CITY_REGISTRY) == []


def test_source_city_registration_reports_unregistered_city():
    project = {
        "sources": {
            "airbnb": {
                "provider": "insideairbnb",
                "cities": {"yyz": {"datasets": {}}},
            }
        }
    }

    errors = validate_source_city_registration(project, CITY_REGISTRY)

    assert any(
        "not a city_id registered in config/city_registry.yml" in error
        for error in errors
    )


def test_empty_databricks_schemas_is_reported():
    broken = {
        **PROJECT_CONFIG,
        "databricks": {"catalog": "trippilot_dev", "schemas": {}},
    }
    errors = validate_project_config(broken)
    assert any("databricks.schemas" in error for error in errors)


def test_valid_city_registry_passes():
    assert validate_city_registry(CITY_REGISTRY) == []


def test_city_registry_missing_version_is_reported():
    errors = validate_city_registry({"cities": CITY_REGISTRY["cities"]})

    assert any("version" in error for error in errors)


def test_city_registry_bad_version_is_reported():
    errors = validate_city_registry({**CITY_REGISTRY, "version": 0})

    assert any("version" in error for error in errors)


def test_empty_cities_list_is_reported():
    errors = validate_city_registry({"version": 1, "cities": []})
    assert len(errors) == 1
    assert "'cities'" in errors[0]


def test_city_entry_missing_enabled_is_reported():
    broken_entry = {
        key: value
        for key, value in CITY_REGISTRY["cities"][0].items()
        if key != "enabled"
    }
    errors = validate_city_registry({**CITY_REGISTRY, "cities": [broken_entry]})
    assert len(errors) == 1
    assert "cities[0]" in errors[0]
    assert "enabled" in errors[0]


def test_city_entry_with_blank_id_is_reported():
    broken = {
        **CITY_REGISTRY,
        "cities": [{**CITY_REGISTRY["cities"][0], "city_id": "   "}],
    }
    errors = validate_city_registry(broken)

    assert any("'city_id'" in error for error in errors)


def test_city_entry_slug_mismatch_is_reported():
    broken = {
        **CITY_REGISTRY,
        "cities": [{**CITY_REGISTRY["cities"][0], "slug": "yyz"}],
    }
    errors = validate_city_registry(broken)

    assert any("must equal the immutable city_id" in error for error in errors)


def test_city_entry_bad_country_code_is_reported():
    broken = {
        **CITY_REGISTRY,
        "cities": [{**CITY_REGISTRY["cities"][0], "country_code": "CAN"}],
    }
    errors = validate_city_registry(broken)

    assert any("ISO 3166-1" in error for error in errors)


def test_city_entry_bad_timezone_is_reported():
    broken = {
        **CITY_REGISTRY,
        "cities": [{**CITY_REGISTRY["cities"][0], "timezone": "EST"}],
    }
    errors = validate_city_registry(broken)

    assert any("IANA timezone" in error for error in errors)


def test_city_duplicate_ids_are_reported():
    broken = {
        **CITY_REGISTRY,
        "cities": [*CITY_REGISTRY["cities"], *CITY_REGISTRY["cities"]],
    }
    errors = validate_city_registry(broken)

    assert any("duplicate city_id" in error for error in errors)


def test_valid_bronze_contract_passes():
    assert validate_bronze_contract(BRONZE_CONTRACT) == []


def test_bronze_missing_required_columns_is_reported():
    broken = {"bronze_listings": {"table": "a.b.c", "source": "insideairbnb"}}
    errors = validate_bronze_contract(broken)
    assert len(errors) == 1
    assert "bronze_listings.required_columns" in errors[0]


def test_bronze_valid_provenance_columns_pass():
    contract = {
        "bronze_listings": {
            **BRONZE_CONTRACT["bronze_listings"],
            "provenance_columns": ["_source", "_city", "_source_file_id"],
        }
    }

    assert validate_bronze_contract(contract) == []


def test_bronze_empty_provenance_column_names_are_reported():
    contract = {
        "bronze_listings": {
            **BRONZE_CONTRACT["bronze_listings"],
            "provenance_columns": ["_source", ""],
        }
    }

    errors = validate_bronze_contract(contract)
    assert len(errors) == 1
    assert "bronze_listings.provenance_columns" in errors[0]


def test_bronze_valid_corrected_file_policy_passes():
    contract = {
        "bronze_listings": {
            **BRONZE_CONTRACT["bronze_listings"],
            "corrected_file_policy": "explicit_reprocess_replace_slice",
        }
    }

    assert validate_bronze_contract(contract) == []


def test_bronze_empty_corrected_file_policy_is_reported():
    contract = {
        "bronze_listings": {
            **BRONZE_CONTRACT["bronze_listings"],
            "corrected_file_policy": "",
        }
    }

    errors = validate_bronze_contract(contract)
    assert len(errors) == 1
    assert "bronze_listings.corrected_file_policy" in errors[0]


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


def test_valid_calendar_contract_passes():
    assert (
        validate_bronze_contract(
            CALENDAR_CONTRACT,
            label="contracts/airbnb/bronze_calendar.yml",
            rules_key="bronze_calendar",
        )
        == []
    )


def test_valid_reviews_contract_passes():
    assert (
        validate_bronze_contract(
            REVIEWS_CONTRACT,
            label="contracts/airbnb/bronze_reviews.yml",
            rules_key="bronze_reviews",
        )
        == []
    )


def test_calendar_missing_required_columns_is_reported():
    broken = {"bronze_calendar": {"table": "a.b.c", "source": "insideairbnb"}}
    errors = validate_bronze_contract(
        broken,
        label="contracts/airbnb/bronze_calendar.yml",
        rules_key="bronze_calendar",
    )
    assert len(errors) == 1
    assert "bronze_calendar.required_columns" in errors[0]


def test_reviews_missing_table_is_reported():
    broken = {
        "bronze_reviews": {
            **REVIEWS_CONTRACT["bronze_reviews"],
            "table": "",
        }
    }
    errors = validate_bronze_contract(
        broken,
        label="contracts/airbnb/bronze_reviews.yml",
        rules_key="bronze_reviews",
    )
    assert len(errors) == 1
    assert "bronze_reviews.table" in errors[0]


def test_bronze_contract_reports_wrong_rules_key():
    errors = validate_bronze_contract(
        BRONZE_CONTRACT,
        label="contracts/airbnb/bronze_calendar.yml",
        rules_key="bronze_calendar",
    )
    assert len(errors) == 1
    assert "Missing rules for table: bronze_calendar" in errors[0]


def test_calendar_valid_row_validation_passes():
    contract = {
        "bronze_calendar": {
            **CALENDAR_CONTRACT["bronze_calendar"],
            "row_validation": {
                "required_fields": ["listing_id", "date"],
                "date_fields": ["date"],
            },
        }
    }

    assert (
        validate_bronze_contract(
            contract,
            label="contracts/airbnb/bronze_calendar.yml",
            rules_key="bronze_calendar",
        )
        == []
    )


def test_reviews_row_validation_not_a_mapping_is_reported():
    contract = {
        "bronze_reviews": {
            **REVIEWS_CONTRACT["bronze_reviews"],
            "row_validation": ["listing_id"],
        }
    }

    errors = validate_bronze_contract(
        contract,
        label="contracts/airbnb/bronze_reviews.yml",
        rules_key="bronze_reviews",
    )
    assert len(errors) == 1
    assert "bronze_reviews.row_validation" in errors[0]
    assert "must be a mapping" in errors[0]


def test_row_validation_empty_required_fields_is_reported():
    contract = {
        "bronze_calendar": {
            **CALENDAR_CONTRACT["bronze_calendar"],
            "row_validation": {"required_fields": [], "date_fields": ["date"]},
        }
    }

    errors = validate_bronze_contract(
        contract,
        label="contracts/airbnb/bronze_calendar.yml",
        rules_key="bronze_calendar",
    )
    assert len(errors) == 1
    assert "row_validation.required_fields" in errors[0]


def test_row_validation_bad_date_fields_type_is_reported():
    contract = {
        "bronze_reviews": {
            **REVIEWS_CONTRACT["bronze_reviews"],
            "row_validation": {
                "required_fields": ["listing_id", "id", "date"],
                "date_fields": "date",
            },
        }
    }

    errors = validate_bronze_contract(
        contract,
        label="contracts/airbnb/bronze_reviews.yml",
        rules_key="bronze_reviews",
    )
    assert len(errors) == 1
    assert "row_validation.date_fields" in errors[0]


def test_row_validation_date_fields_must_be_subset_is_reported():
    contract = {
        "bronze_calendar": {
            **CALENDAR_CONTRACT["bronze_calendar"],
            "row_validation": {
                "required_fields": ["listing_id"],
                "date_fields": ["date"],
            },
        }
    }

    errors = validate_bronze_contract(
        contract,
        label="contracts/airbnb/bronze_calendar.yml",
        rules_key="bronze_calendar",
    )
    assert len(errors) == 1
    assert "subset of required_fields" in errors[0]


def test_valid_manifest_contract_passes():
    assert validate_source_manifest_contract(MANIFEST_CONTRACT) == []


def test_manifest_contract_missing_field_is_reported():
    fields = {k: v for k, v in MANIFEST_CONTRACT["fields"].items() if k != "license"}
    broken = {**MANIFEST_CONTRACT, "fields": fields}

    errors = validate_source_manifest_contract(broken)

    assert any("fields.license" in error for error in errors)


def test_manifest_contract_required_field_must_be_required():
    fields = dict(MANIFEST_CONTRACT["fields"])
    fields["license"] = {"type": "string", "required": False}
    broken = {**MANIFEST_CONTRACT, "fields": fields}

    errors = validate_source_manifest_contract(broken)

    assert any("fields.license.required" in error for error in errors)


def test_manifest_contract_optional_field_must_not_be_required():
    fields = dict(MANIFEST_CONTRACT["fields"])
    fields["error_message"] = {"type": "string", "required": True}
    broken = {**MANIFEST_CONTRACT, "fields": fields}

    errors = validate_source_manifest_contract(broken)

    assert any("fields.error_message.required" in error for error in errors)


def test_manifest_contract_missing_controlled_state_is_reported():
    broken = {**MANIFEST_CONTRACT, "states": ["registered", "validated", "landed"]}

    errors = validate_source_manifest_contract(broken)

    assert any("'states'" in error for error in errors)


def test_manifest_contract_unknown_transition_state_is_reported():
    transitions = dict(MANIFEST_CONTRACT["valid_transitions"])
    transitions["registered"] = ["validated", "unknown"]
    broken = {**MANIFEST_CONTRACT, "valid_transitions": transitions}

    errors = validate_source_manifest_contract(broken)

    assert any("unknown state" in error for error in errors)


def test_manifest_contract_empty_file_types_is_reported():
    broken = {**MANIFEST_CONTRACT, "supported_file_types": []}

    errors = validate_source_manifest_contract(broken)

    assert any("supported_file_types" in error for error in errors)


def test_manifest_contract_bad_max_byte_size_is_reported():
    broken = {**MANIFEST_CONTRACT, "max_byte_size": 0}

    errors = validate_source_manifest_contract(broken)

    assert any("max_byte_size" in error for error in errors)


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
        "    source_url: https://insideairbnb.com/get-the-data/\n"
        "    cities:\n"
        "      toronto:\n"
        "        datasets:\n"
        "          listings:\n"
        "            file: listings.csv.gz\n"
        "            file_type: csv.gz\n"
        "            required_identifier: id\n"
    )
    valid_bronze_yml = (
        "bronze_listings:\n"
        "  table: a.b.c\n"
        "  source: insideairbnb\n"
        "  required_columns:\n"
        "    - id\n"
    )
    valid_calendar_yml = (
        "bronze_calendar:\n"
        "  table: a.b.c\n"
        "  source: insideairbnb\n"
        "  required_columns:\n"
        "    - listing_id\n"
    )
    valid_reviews_yml = (
        "bronze_reviews:\n"
        "  table: a.b.c\n"
        "  source: insideairbnb\n"
        "  required_columns:\n"
        "    - listing_id\n"
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "contracts").mkdir()
    (tmp_path / "config/project.yml").write_text(valid_project_yml, encoding="utf-8")
    (tmp_path / "config/city_registry.yml").write_text(
        "cities: [unclosed", encoding="utf-8"
    )
    for rel in [
        "contracts/airbnb/bronze_listings.yml",
        "contracts/airbnb/bronze_calendar.yml",
        "contracts/airbnb/bronze_reviews.yml",
    ]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "contracts/airbnb/bronze_listings.yml").write_text(
        valid_bronze_yml, encoding="utf-8"
    )
    (tmp_path / "contracts/airbnb/bronze_calendar.yml").write_text(
        valid_calendar_yml, encoding="utf-8"
    )
    (tmp_path / "contracts/airbnb/bronze_reviews.yml").write_text(
        valid_reviews_yml, encoding="utf-8"
    )
    (tmp_path / "contracts/ops").mkdir(parents=True, exist_ok=True)
    (tmp_path / "contracts/ops/source_file_manifest.yml").write_text(
        yaml.safe_dump(MANIFEST_CONTRACT), encoding="utf-8"
    )

    with pytest.raises(ValueError) as excinfo:
        validate_config_files(tmp_path)
    assert "invalid YAML" in str(excinfo.value)
    assert "config/city_registry.yml" in str(excinfo.value)


# F09.1: a structurally valid Silver contract, one representative
# column per declared shape (string, typed cast, money, percent,
# boolean, date, timestamp, provenance, quality, registry-derived,
# normalization-derived).
SILVER_CONTRACT = {
    "silver_listings": {
        "version": 1,
        "table": "trippilot_dev.silver.airbnb_listings_silver",
        "input": "bronze_listings",
        "grain": "one source listing observation per (city_id, snapshot_date, listing_id)",
        "primary_key": ["city_id", "snapshot_date", "listing_id"],
        "write_policy": "replace_city_snapshot",
        "currency_source": "city_registry",
        "columns": [
            {"name": "listing_id", "source": "id", "type": "string", "nullable": False},
            {
                "name": "price",
                "source": "price",
                "type": "decimal(10,2)",
                "parse": "money",
                "nullable": True,
            },
            {
                "name": "host_response_rate",
                "source": "host_response_rate",
                "type": "int",
                "parse": "percent",
                "nullable": True,
            },
            {
                "name": "instant_bookable",
                "source": "instant_bookable",
                "type": "boolean",
                "nullable": True,
            },
            {
                "name": "last_review",
                "source": "last_review",
                "type": "date",
                "nullable": True,
            },
            {
                "name": "source_ingested_at_utc",
                "source": "_ingested_at_utc",
                "type": "timestamp",
                "nullable": False,
            },
            {"name": "city_id", "source": "_city", "type": "string", "nullable": False},
            {
                "name": "snapshot_date",
                "source": "_snapshot_date",
                "type": "string",
                "nullable": False,
            },
            {
                "name": "bronze_quality_status",
                "source": "_quality_status",
                "type": "string",
                "nullable": False,
            },
            {
                "name": "currency",
                "from": "city_registry",
                "type": "string",
                "nullable": False,
            },
            {
                "name": "normalization_issues",
                "from": "normalization",
                "type": "array<string>",
                "nullable": False,
            },
        ],
        "lineage": {
            "bronze_provenance_map": {
                "_city": "city_id",
                "_ingested_at_utc": "source_ingested_at_utc",
            },
            "bronze_quality_map": {"_quality_status": "bronze_quality_status"},
        },
        "exclusions": [{"column": "bathrooms", "reason": "deprecated by the source"}],
        "normalization": {
            "blank_policy": "blank_to_null",
            "boolean_values": {"t": True, "f": False},
            "issues_column": "normalization_issues",
        },
    }
}


def _silver_content():
    return copy.deepcopy(SILVER_CONTRACT)


def test_validate_config_files_reports_missing_file(tmp_path):
    with pytest.raises(ValueError) as excinfo:
        validate_config_files(tmp_path)
    message = str(excinfo.value)
    for rel in [
        "config/project.yml",
        "config/city_registry.yml",
        "contracts/airbnb/bronze_listings.yml",
        "contracts/airbnb/bronze_calendar.yml",
        "contracts/airbnb/bronze_reviews.yml",
        "contracts/airbnb/silver_listings.yml",
        "contracts/ops/source_file_manifest.yml",
    ]:
        assert rel in message
    assert "required file is missing" in message


# ---------------------------------------------------------------------
# Silver contract validation (F09.1)
# ---------------------------------------------------------------------


def test_valid_silver_contract_passes():
    assert validate_silver_contract(_silver_content()) == []


def test_silver_contract_reports_wrong_rules_key():
    content = {"silver_calendar": _silver_content()["silver_listings"]}
    errors = validate_silver_contract(content)
    assert any("Missing rules for table" in error for error in errors)


def test_silver_missing_version_is_reported():
    content = _silver_content()
    del content["silver_listings"]["version"]
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "version" in errors[0]


def test_silver_bad_version_is_reported():
    content = _silver_content()
    content["silver_listings"]["version"] = "1"
    errors = validate_silver_contract(content)
    assert any("version" in error for error in errors)


def test_silver_missing_descriptors_are_reported():
    content = _silver_content()
    rules = content["silver_listings"]
    del rules["table"]
    del rules["input"]
    del rules["grain"]
    del rules["currency_source"]
    errors = validate_silver_contract(content)
    assert len(errors) == 4
    for key in ("table", "input", "grain", "currency_source"):
        assert any(key in error for error in errors)


def test_silver_bad_column_type_is_reported():
    content = _silver_content()
    content["silver_listings"]["columns"][1]["type"] = "number"
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "price" in errors[0]


def test_silver_column_with_both_inputs_is_reported():
    content = _silver_content()
    column = content["silver_listings"]["columns"][1]
    column["from"] = "city_registry"
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "exactly one of 'source'" in errors[0]


def test_silver_column_with_neither_input_is_reported():
    content = _silver_content()
    del content["silver_listings"]["columns"][1]["source"]
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "exactly one of 'source'" in errors[0]


def test_silver_unknown_from_value_is_reported():
    content = _silver_content()
    content["silver_listings"]["columns"][8]["from"] = "magic"
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "'from'" in errors[0]


def test_silver_unknown_parse_marker_is_reported():
    content = _silver_content()
    content["silver_listings"]["columns"][2]["parse"] = "fraction"
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "parse marker" in errors[0]


def test_silver_duplicate_column_is_reported():
    content = _silver_content()
    rules = content["silver_listings"]
    rules["columns"].append(copy.deepcopy(rules["columns"][0]))
    errors = validate_silver_contract(content)
    assert any("declared twice" in error for error in errors)


def test_silver_missing_nullable_flag_is_reported():
    content = _silver_content()
    del content["silver_listings"]["columns"][0]["nullable"]
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "nullable" in errors[0]


def test_silver_primary_key_must_be_declared():
    content = _silver_content()
    content["silver_listings"]["primary_key"] = ["city_id", "not_a_column"]
    errors = validate_silver_contract(content)
    assert len(errors) == 1
    assert "undeclared columns" in errors[0]


def test_silver_excluded_column_cannot_be_declared():
    content = _silver_content()
    rules = content["silver_listings"]
    rules["columns"].append(
        {"name": "bathrooms", "source": "bathrooms", "type": "string", "nullable": True}
    )
    errors = validate_silver_contract(content)
    assert any("also declared" in error for error in errors)


def test_silver_exclusion_needs_a_reason():
    content = _silver_content()
    content["silver_listings"]["exclusions"] = [{"column": "bathrooms"}]
    errors = validate_silver_contract(content)
    assert any("'column' and 'reason'" in error for error in errors)


def test_silver_issues_column_must_be_declared():
    content = _silver_content()
    rules = content["silver_listings"]
    rules["normalization"]["issues_column"] = "issues"
    errors = validate_silver_contract(content)
    assert any("issues_column" in error for error in errors)


def test_silver_lineage_target_must_be_declared():
    content = _silver_content()
    rules = content["silver_listings"]
    rules["lineage"]["bronze_quality_map"]["_quality_status"] = "quality_status"
    errors = validate_silver_contract(content)
    assert any("not a declared column" in error for error in errors)


def test_silver_boolean_values_must_map_t_and_f():
    content = _silver_content()
    rules = content["silver_listings"]
    rules["normalization"]["boolean_values"] = {"t": "true", "f": "false"}
    errors = validate_silver_contract(content)
    assert any("boolean_values" in error for error in errors)


def test_supported_column_type_matrix():
    supported = [
        "string",
        "boolean",
        "date",
        "timestamp",
        "int",
        "long",
        "array<string>",
        "decimal(10,2)",
        "decimal(9,6)",
        "decimal(1,0)",
    ]
    for column_type in supported:
        assert is_supported_column_type(column_type), column_type

    unsupported = [
        "number",
        "float",
        "double",
        "decimal",
        "decimal(10)",
        "decimal(10,2,3)",
        "decimal(0,2)",
        "decimal(10,-2)",
        "",
        None,
        42,
    ]
    for column_type in unsupported:
        assert not is_supported_column_type(column_type), column_type


def test_silver_marker_sets_are_closed():
    assert SILVER_COLUMN_FROM_VALUES == frozenset({"city_registry", "normalization"})
    assert SILVER_COLUMN_PARSE_VALUES == frozenset({"money", "percent"})
