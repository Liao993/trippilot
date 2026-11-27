"""Validate TripPilot's populated YAML configuration and contract files.

These checks run in CI and locally without Spark, Databricks, or any
credentials. They go beyond YAML parsing: each populated file must have
the expected structure and essential keys, so a broken configuration is
caught before the pipeline runs. Empty placeholder YAML files are
intentionally excluded - only populated files are validated.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from src.common.city_registry import find_registry_problems
from src.common.source_manifest import SUPPORTED_FILE_TYPES
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
    # F09.1: the normalized detailed-listings Silver contract.
    "contracts/airbnb/silver_listings.yml": "silver_contract",
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

# The Silver contract carries exactly one top-level rules key, like the
# Bronze contracts (F09.1).
SILVER_CONTRACT_RULES_KEYS: dict[str, str] = {
    "contracts/airbnb/silver_listings.yml": "silver_listings",
}

# Column types a Silver contract may declare. decimal(p, s) carries its
# precision/scale explicitly; identifiers stay strings and counts stay
# ints by design - the types are a contract, never an inference.
_SIMPLE_COLUMN_TYPES = frozenset(
    {"string", "boolean", "date", "timestamp", "int", "long", "array<string>"}
)
_DECIMAL_TYPE_PATTERN = re.compile(r"^decimal\(([0-9]+),([0-9]+)\)$")


def is_supported_column_type(column_type: Any) -> bool:
    """Return whether a Silver contract column type is supported."""
    if not isinstance(column_type, str):
        return False
    if column_type in _SIMPLE_COLUMN_TYPES:
        return True
    match = _DECIMAL_TYPE_PATTERN.match(column_type)
    return bool(match) and int(match.group(1)) > 0 and int(match.group(2)) >= 0


# Parse markers a Silver contract column may carry beyond its type
# (F09.1: money strips currency symbol and thousands separators,
# percent strips the '%' sign).
SILVER_COLUMN_PARSE_VALUES = frozenset({"money", "percent"})
# Derivation markers for columns with no Bronze source (registry
# currency, the normalization-issues outcome).
SILVER_COLUMN_FROM_VALUES = frozenset(
    {"city_registry", "normalization", "amenity_search"}
)

# Registry-derived Silver columns declare which city-registry field
# they take their value from.
SILVER_REGISTRY_KEY_VALUES = frozenset({"currency", "country_name"})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(_is_nonempty_string(item) for item in value)
    )


def _validate_sources_section(sources: dict[str, Any], label: str) -> list[str]:
    """Check the per-family city/dataset source registry (F08.2).

    City keys are immutable city_ids registered in
    config/city_registry.yml (cross-checked separately in
    validate_config_files, which sees both files). City enablement is
    owned by the registry, so an 'enabled' flag here is an error.
    """
    errors: list[str] = []
    for family_name, family in sources.items():
        family_label = f"{label}: sources.{family_name}"
        if not isinstance(family, dict):
            errors.append(f"{family_label} must be a mapping")
            continue
        if not _is_nonempty_string(family.get("provider")):
            errors.append(f"{family_label}.provider must be a non-empty string")
        source_url = family.get("source_url")
        if not _is_nonempty_string(source_url) or not str(source_url).startswith(
            ("https://", "http://")
        ):
            errors.append(
                f"{family_label}.source_url must be an official https:// or http:// URL"
            )
        cities = family.get("cities")
        if not isinstance(cities, dict) or len(cities) == 0:
            errors.append(
                f"{family_label}.cities must be a non-empty mapping keyed by "
                "registered city_id"
            )
            continue
        for city_id, city in cities.items():
            city_label = f"{family_label}.cities.{city_id}"
            if not isinstance(city, dict):
                errors.append(f"{city_label} must be a mapping")
                continue
            if "enabled" in city:
                errors.append(
                    f"{city_label}: city enablement lives ONLY in "
                    "config/city_registry.yml; remove the 'enabled' flag "
                    "from project.yml"
                )
            datasets = city.get("datasets")
            if not isinstance(datasets, dict) or len(datasets) == 0:
                errors.append(
                    f"{city_label}.datasets must be a non-empty mapping of "
                    "controlled dataset tags"
                )
                continue
            for dataset, spec in datasets.items():
                dataset_label = f"{city_label}.datasets.{dataset}"
                if not isinstance(spec, dict):
                    errors.append(f"{dataset_label} must be a mapping")
                    continue
                if not _is_nonempty_string(spec.get("file")):
                    errors.append(f"{dataset_label}.file must be a non-empty string")
                file_type = spec.get("file_type")
                if (
                    not _is_nonempty_string(file_type)
                    or str(file_type) not in SUPPORTED_FILE_TYPES
                ):
                    errors.append(
                        f"{dataset_label}.file_type must be one of the "
                        f"supported file types {SUPPORTED_FILE_TYPES}"
                    )
                if not _is_nonempty_string(spec.get("required_identifier")):
                    errors.append(
                        f"{dataset_label}.required_identifier must be a "
                        "non-empty string"
                    )
                if (
                    _is_nonempty_string(spec.get("file"))
                    and _is_nonempty_string(file_type)
                    and str(file_type) in SUPPORTED_FILE_TYPES
                    and not str(spec["file"]).endswith(f".{file_type}")
                ):
                    errors.append(
                        f"{dataset_label}.file {spec['file']!r} does not end "
                        f"with the declared file_type {file_type!r}"
                    )
    return errors


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
    else:
        errors.extend(_validate_sources_section(sources, label))

    return errors


def validate_source_city_registration(
    project_content: dict[str, Any],
    registry_content: dict[str, Any],
    label: str = "config/project.yml",
    registry_label: str = "config/city_registry.yml",
) -> list[str]:
    """Cross-check project.yml source cities against the registry (F08.2).

    Every sources.<family>.cities key must be an immutable city_id
    registered in config/city_registry.yml; a city that is only in
    project.yml can never be ingested, and its datasets would silently
    detach from the registry's enablement and metadata.
    """
    errors: list[str] = []
    cities = registry_content.get("cities")
    registered = {
        entry.get("city_id")
        for entry in (cities or [])
        if isinstance(entry, dict) and _is_nonempty_string(entry.get("city_id"))
    }
    sources = project_content.get("sources")
    if not isinstance(sources, dict):
        return errors
    for family_name, family in sources.items():
        if not isinstance(family, dict) or not isinstance(family.get("cities"), dict):
            continue
        for city_id in family["cities"]:
            if city_id not in registered:
                errors.append(
                    f"{label}: sources.{family_name}.cities.{city_id} is not a "
                    f"city_id registered in {registry_label}"
                )
    return errors


def validate_city_registry(
    content: dict[str, Any],
    label: str = "config/city_registry.yml",
) -> list[str]:
    """Check the stable city registry (F08.1) entry rules.

    The structural definition of a well-formed registry entry lives in
    src.common.city_registry.find_registry_problems so the runtime
    control plane and CI validation enforce one shared definition.
    """
    return [f"{label}: {problem}" for problem in find_registry_problems(content)]


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


def validate_silver_contract(
    content: dict[str, Any],
    label: str = "contracts/airbnb/silver_listings.yml",
    rules_key: str = "silver_listings",
) -> list[str]:
    """Check the structure of a normalized Silver contract (F09.1).

    rules_key is the contract's single top-level key. The checks mirror
    what the Silver transformation enforces at runtime: a version, the
    canonical table, an input, a grain and primary key drawn from the
    declared columns, unique column names with supported types and a
    single input each (Bronze `source` or `from` derivation), lineage
    maps whose targets are declared columns, exclusions that name a
    reason and are not also declared, and a normalization section that
    declares its issues column and the t/f boolean mapping.
    """
    try:
        rules = get_table_rules(content, rules_key)
    except TypeError as exc:
        return [f"{label}: {exc}"]

    errors: list[str] = []

    version = rules.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        errors.append(f"{label}: '{rules_key}.version' must be a positive integer")

    for key in ("table", "input", "grain", "currency_source"):
        if not _is_nonempty_string(rules.get(key)):
            errors.append(f"{label}: '{rules_key}.{key}' must be a non-empty string")

    columns = rules.get("columns")
    declared: set[str] = set()
    if not isinstance(columns, list) or not columns:
        errors.append(f"{label}: '{rules_key}.columns' must be a non-empty list")
        columns = []
    for entry in columns:
        if not isinstance(entry, dict):
            errors.append(f"{label}: '{rules_key}.columns' entries must be mappings")
            continue
        name = entry.get("name")
        if not _is_nonempty_string(name):
            errors.append(f"{label}: column entry needs a non-empty 'name'")
            continue
        if name in declared:
            errors.append(f"{label}: column {name!r} is declared twice")
            continue
        declared.add(name)
        column_label = f"{label}: column {name!r}"

        has_source = _is_nonempty_string(entry.get("source"))
        has_from = _is_nonempty_string(entry.get("from"))
        if has_source == has_from:
            errors.append(
                f"{column_label}: must declare exactly one of 'source' "
                "(Bronze column) or 'from' (derived input)"
            )
        elif has_from and entry["from"] not in SILVER_COLUMN_FROM_VALUES:
            errors.append(
                f"{column_label}: unknown 'from' value {entry['from']!r}; "
                f"expected one of {sorted(SILVER_COLUMN_FROM_VALUES)}"
            )
        elif (
            has_from
            and entry["from"] == "city_registry"
            and entry.get("registry_key") not in SILVER_REGISTRY_KEY_VALUES
        ):
            errors.append(
                f"{column_label}: city_registry columns must declare "
                f"'registry_key' one of {sorted(SILVER_REGISTRY_KEY_VALUES)}"
            )
        elif has_from and entry["from"] == "amenity_search":
            if entry.get("type") != "boolean":
                errors.append(f"{column_label}: amenity_search columns must be boolean")
            if not _is_nonempty_string_list(entry.get("patterns")):
                errors.append(
                    f"{column_label}: amenity_search columns need a non-empty "
                    "'patterns' list of non-blank strings"
                )
            remove_patterns = entry.get("remove_patterns", [])
            if not isinstance(remove_patterns, list) or any(
                not isinstance(pattern, str) or not pattern.strip()
                for pattern in remove_patterns
            ):
                errors.append(
                    f"{column_label}: 'remove_patterns' must be a list of "
                    "non-blank strings"
                )

        if not is_supported_column_type(entry.get("type")):
            errors.append(f"{column_label}: unsupported type {entry.get('type')!r}")

        parse = entry.get("parse")
        if parse is not None and (
            not _is_nonempty_string(parse) or parse not in SILVER_COLUMN_PARSE_VALUES
        ):
            errors.append(
                f"{column_label}: unknown parse marker {parse!r}; expected "
                f"one of {sorted(SILVER_COLUMN_PARSE_VALUES)}"
            )

        if not isinstance(entry.get("nullable"), bool):
            errors.append(f"{column_label}: 'nullable' must be boolean")

    primary_key = rules.get("primary_key")
    if not _is_nonempty_string_list(primary_key):
        errors.append(
            f"{label}: '{rules_key}.primary_key' must be a non-empty list of "
            "column names"
        )
    elif declared:
        missing = [name for name in primary_key if name not in declared]
        if missing:
            errors.append(
                f"{label}: '{rules_key}.primary_key' names undeclared "
                f"columns: {missing}"
            )

    lineage = rules.get("lineage")
    if not isinstance(lineage, dict):
        errors.append(f"{label}: '{rules_key}.lineage' must be a mapping")
    else:
        for map_key in ("bronze_provenance_map", "bronze_quality_map"):
            mapping = lineage.get(map_key)
            if not isinstance(mapping, dict) or not mapping:
                errors.append(
                    f"{label}: '{rules_key}.lineage.{map_key}' must be a "
                    "non-empty mapping"
                )
                continue
            for bronze_column, silver_column in mapping.items():
                if not _is_nonempty_string(bronze_column) or not _is_nonempty_string(
                    silver_column
                ):
                    errors.append(
                        f"{label}: '{rules_key}.lineage.{map_key}' entries must "
                        "be non-empty strings"
                    )
                elif declared and silver_column not in declared:
                    errors.append(
                        f"{label}: lineage target {silver_column!r} is not a "
                        "declared column"
                    )

    exclusions = rules.get("exclusions")
    if exclusions is not None:
        if not isinstance(exclusions, list) or not exclusions:
            errors.append(
                f"{label}: '{rules_key}.exclusions' must be a non-empty list "
                "when present"
            )
        else:
            for entry in exclusions:
                if (
                    not isinstance(entry, dict)
                    or not _is_nonempty_string(entry.get("column"))
                    or not _is_nonempty_string(entry.get("reason"))
                ):
                    errors.append(
                        f"{label}: '{rules_key}.exclusions' entries need "
                        "'column' and 'reason'"
                    )
                    continue
                if declared and entry["column"] in declared:
                    errors.append(
                        f"{label}: excluded column {entry['column']!r} is also "
                        "declared as a column"
                    )

    normalization = rules.get("normalization")
    if not isinstance(normalization, dict) or not normalization:
        errors.append(
            f"{label}: '{rules_key}.normalization' must be a non-empty mapping"
        )
    else:
        issues_column = normalization.get("issues_column")
        if not _is_nonempty_string(issues_column):
            errors.append(
                f"{label}: '{rules_key}.normalization.issues_column' must be "
                "a non-empty string"
            )
        elif declared and issues_column not in declared:
            errors.append(
                f"{label}: '{rules_key}.normalization.issues_column' must be "
                "a declared column"
            )
        if normalization.get("boolean_values") != {"t": True, "f": False}:
            errors.append(
                f"{label}: '{rules_key}.normalization.boolean_values' must "
                "map t -> true and f -> false"
            )
        if not _is_nonempty_string(normalization.get("blank_policy")):
            errors.append(
                f"{label}: '{rules_key}.normalization.blank_policy' must be "
                "a non-empty string"
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
# Optional manifest fields, cross-checked against the contract: the
# dataset tag (F08.4) and the classified failure reason (F07.3-T01)
# join the optional operational fields; all must stay required: false.
MANIFEST_OPTIONAL_FIELDS = (
    "dataset",
    "landing_path",
    "error_message",
    "error_type",
)
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
    "silver_contract": validate_silver_contract,
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
    parsed_by_kind: dict[str, dict[str, Any]] = {}

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

        if kind in ("project", "city_registry"):
            parsed_by_kind[kind] = content

        if kind == "bronze_contract":
            errors.extend(
                validate_bronze_contract(
                    content, label, rules_key=BRONZE_CONTRACT_RULES_KEYS[rel_path]
                )
            )
        elif kind == "silver_contract":
            errors.extend(
                validate_silver_contract(
                    content, label, rules_key=SILVER_CONTRACT_RULES_KEYS[rel_path]
                )
            )
        else:
            errors.extend(VALIDATORS[kind](content, label))

    if "project" in parsed_by_kind and "city_registry" in parsed_by_kind:
        errors.extend(
            validate_source_city_registration(
                parsed_by_kind["project"], parsed_by_kind["city_registry"]
            )
        )

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
