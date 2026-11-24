"""Validate TripPilot's populated YAML configuration and contract files.

These checks run in CI and locally without Spark, Databricks, or any
credentials. They go beyond YAML parsing: each populated file must have
the expected structure and essential keys, so a broken configuration is
caught before the pipeline runs. Empty placeholder YAML files are
intentionally excluded - only populated files are validated.
"""

from pathlib import Path
from typing import Any

import yaml

from src.quality.contract_loader import get_table_rules, load_contract

# The populated files this validation covers, mapped to their validators.
# The former empty placeholder files (config/alerts.yml, config/jobs.yml,
# config/model.yml, config/slos.yml and the empty operational contracts
# exclusion.yml, pipeline_runs.yml and quality_results.yml) were removed
# in the pre-F06 repository cleanup; a future feature that needs one of
# them should create it populated, and list it here.
CONFIG_FILES: dict[str, str] = {
    "config/project.yml": "project",
    "config/city_registry.yml": "city_registry",
    "contracts/airbnb/bronze_listings.yml": "bronze_contract",
    "contracts/airbnb/bronze_calendar.yml": "bronze_contract",
    "contracts/airbnb/bronze_reviews.yml": "bronze_contract",
    "contracts/airbnb/bronze_listings_summary.yml": "bronze_contract",
    "contracts/airbnb/bronze_reviews_summary.yml": "bronze_contract",
    "contracts/airbnb/bronze_neighbourhoods.yml": "bronze_contract",
    "contracts/airbnb/bronze_neighbourhood_geometry.yml": "bronze_contract",
    "contracts/ops/source_file_manifest.yml": "source_manifest_contract",
}

# Each Bronze contract file carries exactly one top-level rules key named
# after its table (bronze_listings, bronze_calendar, bronze_reviews); the
# shared validator needs to know which key to read (F06.1).
BRONZE_CONTRACT_RULES_KEYS: dict[str, str] = {
    "contracts/airbnb/bronze_listings.yml": "bronze_listings",
    "contracts/airbnb/bronze_calendar.yml": "bronze_calendar",
    "contracts/airbnb/bronze_reviews.yml": "bronze_reviews",
    "contracts/airbnb/bronze_listings_summary.yml": "bronze_listings_summary",
    "contracts/airbnb/bronze_reviews_summary.yml": "bronze_reviews_summary",
    "contracts/airbnb/bronze_neighbourhoods.yml": "bronze_neighbourhoods",
    "contracts/airbnb/bronze_neighbourhood_geometry.yml": (
        "bronze_neighbourhood_geometry"
    ),
}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(_is_nonempty_string(item) for item in value)
    )


def validate_project_config(
    content: dict[str, Any],
    label: str = "config/project.yml",
) -> list[str]:
    """Check the expected sections and essential keys of project.yml."""
    errors: list[str] = []

    project = content.get("project")
    if not isinstance(project, dict):
        errors.append(f"{label}: 'project' section is missing or is not a mapping")
    elif not _is_nonempty_string(project.get("name")):
        errors.append(f"{label}: 'project.name' must be a non-empty string")

    databricks = content.get("databricks")
    if not isinstance(databricks, dict):
        errors.append(f"{label}: 'databricks' section is missing or is not a mapping")
    else:
        if not _is_nonempty_string(databricks.get("catalog")):
            errors.append(f"{label}: 'databricks.catalog' must be a non-empty string")
        schemas = databricks.get("schemas")
        if not isinstance(schemas, dict) or len(schemas) == 0:
            errors.append(f"{label}: 'databricks.schemas' must be a non-empty mapping")

    sources = content.get("sources")
    if not isinstance(sources, dict) or len(sources) == 0:
        errors.append(f"{label}: 'sources' must be a non-empty mapping")

    return errors


def validate_city_registry(
    content: dict[str, Any],
    label: str = "config/city_registry.yml",
) -> list[str]:
    """Check the cities list of city_registry.yml."""
    errors: list[str] = []

    cities = content.get("cities")
    if not isinstance(cities, list) or len(cities) == 0:
        errors.append(f"{label}: 'cities' must be a non-empty list")
        return errors

    for index, entry in enumerate(cities):
        entry_label = f"{label}: cities[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_label} must be a mapping")
            continue
        if not _is_nonempty_string(entry.get("city")):
            errors.append(f"{entry_label}: 'city' must be a non-empty string")
        if not isinstance(entry.get("enabled"), bool):
            errors.append(f"{entry_label}: 'enabled' must be a boolean")

    return errors


def validate_bronze_contract(
    content: dict[str, Any],
    label: str = "contracts/airbnb/bronze_listings.yml",
    rules_key: str = "bronze_listings",
) -> list[str]:
    """Check the table, source and column information of a Bronze contract.

    rules_key is the contract's single top-level key (bronze_listings,
    bronze_calendar, bronze_reviews); each file is validated against its
    own key so the error messages name the table that failed.
    """
    try:
        rules = get_table_rules(content, rules_key)
    except TypeError as exc:
        return [f"{label}: {exc}"]

    errors: list[str] = []
    if not _is_nonempty_string(rules.get("table")):
        errors.append(f"{label}: '{rules_key}.table' must be a non-empty string")
    if not _is_nonempty_string(rules.get("source")):
        errors.append(f"{label}: '{rules_key}.source' must be a non-empty string")
    if not _is_nonempty_string_list(rules.get("required_columns")):
        errors.append(
            f"{label}: '{rules_key}.required_columns' must be a non-empty "
            "list of column names"
        )
    provenance = rules.get("provenance_columns")
    if provenance is not None and not _is_nonempty_string_list(provenance):
        errors.append(
            f"{label}: '{rules_key}.provenance_columns' must be a non-empty "
            "list of column names"
        )
    policy = rules.get("corrected_file_policy")
    if policy is not None and not _is_nonempty_string(policy):
        errors.append(
            f"{label}: '{rules_key}.corrected_file_policy' must be a non-empty string"
        )

    # Optional row-level quality policy (F06.2-T03): when a Bronze
    # contract declares one, its shape is enforced here so the
    # ingestion notebooks can consume it without hard-coded fields.
    row_validation = rules.get("row_validation")
    if row_validation is not None:
        if not isinstance(row_validation, dict):
            errors.append(f"{label}: '{rules_key}.row_validation' must be a mapping")
        else:
            if not _is_nonempty_string_list(row_validation.get("required_fields")):
                errors.append(
                    f"{label}: '{rules_key}.row_validation.required_fields' "
                    "must be a non-empty list of column names"
                )
            date_fields = row_validation.get("date_fields")
            if date_fields is not None and not _is_nonempty_string_list(date_fields):
                errors.append(
                    f"{label}: '{rules_key}.row_validation.date_fields' must "
                    "be a non-empty list of column names"
                )
            required_fields = row_validation.get("required_fields")
            if (
                _is_nonempty_string_list(required_fields)
                and _is_nonempty_string_list(date_fields)
                and any(field not in required_fields for field in date_fields)
            ):
                errors.append(
                    f"{label}: '{rules_key}.row_validation.date_fields' must "
                    "be a subset of required_fields"
                )
    return errors


MANIFEST_REQUIRED_FIELDS = (
    "source_file_id",
    "source_family",
    "source_entity_id",
    "source_version",
    "file_type",
    "source_url",
    "retrieved_at_utc",
    "file_hash_sha256",
    "byte_size",
    "schema_version",
    "license",
    "attribution",
    "source_path",
    "run_id",
    "processing_state",
)
MANIFEST_OPTIONAL_FIELDS = ("landing_path", "error_message")
MANIFEST_CONTROLLED_STATES = ("registered", "validated", "landed", "failed")


def validate_source_manifest_contract(
    content: dict[str, Any],
    label: str = "contracts/ops/source_file_manifest.yml",
) -> list[str]:
    """Check the states, transitions, file types and fields of the manifest contract."""
    errors: list[str] = []

    states = content.get("states")
    if not _is_nonempty_string_list(states):
        errors.append(f"{label}: 'states' must be a non-empty list of strings")
        states = []
    else:
        for state in MANIFEST_CONTROLLED_STATES:
            if state not in states:
                errors.append(
                    f"{label}: 'states' must contain the controlled state {state!r}"
                )

    transitions = content.get("valid_transitions")
    if not isinstance(transitions, dict) or len(transitions) == 0:
        errors.append(f"{label}: 'valid_transitions' must be a non-empty mapping")
    else:
        for from_state, to_states in transitions.items():
            if from_state not in states:
                errors.append(
                    f"{label}: 'valid_transitions' key {from_state!r} is not a known state"
                )
            if not isinstance(to_states, list):
                errors.append(
                    f"{label}: 'valid_transitions.{from_state}' must be a list of states"
                )
                continue
            for to_state in to_states:
                if to_state not in states:
                    errors.append(
                        f"{label}: 'valid_transitions.{from_state}' names unknown "
                        f"state {to_state!r}"
                    )

    if not _is_nonempty_string_list(content.get("supported_file_types")):
        errors.append(
            f"{label}: 'supported_file_types' must be a non-empty list of strings"
        )

    max_byte_size = content.get("max_byte_size")
    if (
        isinstance(max_byte_size, bool)
        or not isinstance(max_byte_size, int)
        or max_byte_size <= 0
    ):
        errors.append(f"{label}: 'max_byte_size' must be a positive integer")

    fields = content.get("fields")
    if not isinstance(fields, dict) or len(fields) == 0:
        errors.append(f"{label}: 'fields' must be a non-empty mapping")
        return errors

    for field in MANIFEST_REQUIRED_FIELDS:
        entry = fields.get(field)
        if not isinstance(entry, dict):
            errors.append(f"{label}: 'fields.{field}' must be a mapping")
            continue
        if entry.get("required") is not True:
            errors.append(f"{label}: 'fields.{field}.required' must be true")
        if not _is_nonempty_string(entry.get("type")):
            errors.append(f"{label}: 'fields.{field}.type' must be a non-empty string")

    for field in MANIFEST_OPTIONAL_FIELDS:
        entry = fields.get(field)
        if not isinstance(entry, dict):
            errors.append(f"{label}: 'fields.{field}' must be a mapping")
            continue
        if entry.get("required") is not False:
            errors.append(f"{label}: 'fields.{field}.required' must be false")
        if not _is_nonempty_string(entry.get("type")):
            errors.append(f"{label}: 'fields.{field}.type' must be a non-empty string")

    return errors


VALIDATORS = {
    "project": validate_project_config,
    "city_registry": validate_city_registry,
    "bronze_contract": validate_bronze_contract,
    "source_manifest_contract": validate_source_manifest_contract,
}


def validate_config_files(repo_root: str | Path | None = None) -> None:
    """Validate every populated configuration and contract file.

    Raises ValueError listing every problem found, with each message naming
    the file and the missing or invalid key. Runs without Spark, Databricks,
    production tables or credentials.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    errors: list[str] = []

    for rel_path, kind in CONFIG_FILES.items():
        label = rel_path
        path = root / rel_path

        try:
            content = load_contract(path)
        except FileNotFoundError:
            errors.append(f"{label}: required file is missing")
            continue
        except yaml.YAMLError as exc:
            errors.append(f"{label}: invalid YAML: {exc}")
            continue
        except TypeError as exc:
            errors.append(f"{label}: {exc}")
            continue

        if not content:
            errors.append(f"{label}: file is empty; a populated mapping is required")
            continue

        if kind == "bronze_contract":
            errors.extend(
                validate_bronze_contract(
                    content, label, rules_key=BRONZE_CONTRACT_RULES_KEYS[rel_path]
                )
            )
        else:
            errors.extend(VALIDATORS[kind](content, label))

    if errors:
        raise ValueError(
            "YAML configuration/contract validation failed:\n- " + "\n- ".join(errors)
        )


def main() -> None:
    """Validate every populated file from the repository root."""
    validate_config_files()
    print("All populated YAML configuration and contract files are valid.")


if __name__ == "__main__":
    main()
