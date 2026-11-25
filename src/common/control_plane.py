"""Ingestion control plane for the multi-city registry (F08.4).

Pure-Python, registry-driven selection that binds the three
configuration layers together - config/city_registry.yml (which
cities exist and which are enabled), config/project.yml (which
datasets each city registers, with which file and key field) and
ops.source_file_manifest (which exact bytes have landed for a
city/dataset slice) - into bounded, explicit decisions:

- list_city_datasets: the bounded grid of enabled city/dataset slices
  a run may touch, straight from the two validated config files.
- select_landed_source_file: the exact landed manifest record for one
  city/dataset slice, resolved from manifest state, never from a path.

Nothing here guesses: an unregistered city, an unregistered dataset
tag, a disabled city or an ambiguous landed slice is an error naming
the exact remedy. City enablement lives only in the registry; dataset
registration only in project.yml; landed identity only in the
manifest.
"""

from pathlib import Path
from typing import Any

import yaml

from src.common.city_registry import (
    find_registry_problems,
    get_city,
    get_enabled_cities,
)
from src.common.ingestion_manifest import INGESTION_DATASETS


def load_city_registry(repo_root: Path | str = ".") -> dict[str, Any]:
    """Parse config/city_registry.yml and refuse a malformed registry.

    The same structural rules as src.quality.config_validation apply,
    so a malformed registry can never reach selection decisions.
    """
    path = Path(repo_root) / "config" / "city_registry.yml"
    with path.open() as file:
        registry = yaml.safe_load(file)
    problems = find_registry_problems(registry)
    if problems:
        raise ValueError(f"{path}: invalid city registry:\n- " + "\n- ".join(problems))
    return registry


def load_project_config(repo_root: Path | str = ".") -> dict[str, Any]:
    """Parse config/project.yml (structure is enforced by the config gates)."""
    path = Path(repo_root) / "config" / "project.yml"
    with path.open() as file:
        return yaml.safe_load(file)


def _airbnb_cities(project_config: Any) -> dict[str, Any]:
    if not isinstance(project_config, dict):
        raise TypeError("project_config must be a mapping")
    sources = project_config.get("sources")
    if not isinstance(sources, dict) or not isinstance(sources.get("airbnb"), dict):
        raise TypeError(
            "project_config must map sources.airbnb to the city/dataset "
            "registry; a city cannot be selected without its dataset "
            "registration"
        )
    cities = sources["airbnb"].get("cities")
    if not isinstance(cities, dict) or not cities:
        raise ValueError(
            "sources.airbnb.cities must be a non-empty mapping of registered cities"
        )
    return cities


def list_city_datasets(project_config: Any, registry: Any) -> list[dict[str, Any]]:
    """Return the bounded grid of enabled city/dataset slices.

    One row per enabled, registered city x registered dataset, carrying
    the dataset's file, file type and key field from project.yml. A
    configured-but-unregistered city, an unknown dataset tag or a
    malformed registration is refused with an error naming the exact
    problem; a disabled city is excluded by design (enablement is a
    registry property, never an error).
    """
    cities = _airbnb_cities(project_config)
    enabled = set(get_enabled_cities(registry))
    rows: list[dict[str, Any]] = []
    for city_id, city_config in cities.items():
        if get_city(registry, str(city_id)) is None:
            raise ValueError(
                f"city {city_id!r} is configured in project.yml but not "
                "registered in the city registry; register it first or remove "
                "its configuration"
            )
        if city_id not in enabled:
            continue
        datasets = city_config.get("datasets")
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError(
                f"city {city_id!r}: 'datasets' must be a non-empty mapping of "
                "controlled dataset tags"
            )
        for dataset, dataset_config in datasets.items():
            if dataset not in INGESTION_DATASETS:
                raise ValueError(
                    f"city {city_id!r}: unknown dataset tag {dataset!r}; "
                    "expected one of: " + ", ".join(INGESTION_DATASETS)
                )
            if not isinstance(dataset_config, dict):
                raise TypeError(
                    f"city {city_id!r}/{dataset}: dataset configuration must "
                    "be a mapping"
                )
            rows.append(
                {
                    "city_id": str(city_id),
                    "dataset": str(dataset),
                    "file": str(dataset_config.get("file", "")),
                    "file_type": str(dataset_config.get("file_type", "")),
                    "required_identifier": str(
                        dataset_config.get("required_identifier", "")
                    ),
                }
            )
    return rows


def select_landed_source_file(
    manifest_store: Any,
    project_config: Any,
    registry: Any,
    city_id: str,
    dataset: str,
    source_version: str | None = None,
) -> dict[str, Any]:
    """Return the exact landed manifest record for one city/dataset slice.

    The selection is bounded by both config layers before it touches
    the manifest: the city must be registered and enabled, and the
    dataset must be registered for that city in project.yml. The
    landed identity then comes solely from the source manifest - this
    never reads a path from configuration.
    """
    if not isinstance(city_id, str) or not city_id.strip():
        raise ValueError("city_id is required to select a source file")
    if not isinstance(dataset, str) or not dataset.strip():
        raise ValueError("dataset is required to select a source file")

    entry = get_city(registry, city_id)
    if entry is None:
        raise ValueError(f"city {city_id!r} is not registered in the city registry")
    if entry.get("enabled") is not True:
        raise ValueError(
            f"city {city_id!r} is registered but disabled; enable it in "
            "config/city_registry.yml before ingesting"
        )

    city_config = _airbnb_cities(project_config).get(city_id)
    if not isinstance(city_config, dict):
        raise TypeError(
            f"city {city_id!r} has no dataset registration mapping in project.yml"
        )
    datasets = city_config.get("datasets")
    if not isinstance(datasets, dict) or dataset not in datasets:
        available = ", ".join(sorted(datasets)) if isinstance(datasets, dict) else ""
        raise ValueError(
            f"dataset {dataset!r} is not registered for city {city_id!r} in "
            f"project.yml (registered: {available or 'none'})"
        )

    return manifest_store.read_landed_by_dataset(city_id, dataset, source_version)


def _latest_value(
    rows: list[dict[str, Any]],
    timestamp_fields: tuple[str, ...],
    value_field: str,
) -> str | None:
    """Return the latest row's value, ordered by its effective timestamp.

    The effective timestamp is the first non-empty field of
    timestamp_fields (completed before started, for example), so a
    still-running row is never shadowed by an older completed one.
    """
    if not rows:
        return None

    def effective_timestamp(row: dict[str, Any]) -> str:
        for field in timestamp_fields:
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    latest = max(rows, key=effective_timestamp)
    value = latest.get(value_field)
    return value if isinstance(value, str) and value.strip() else None


def build_city_dataset_coverage(
    project_config: Any,
    registry: Any,
    availability_store: Any,
    ingestion_store: Any,
) -> list[dict[str, Any]]:
    """Return the coverage grid: one row per configured city/dataset slice.

    F08.6 coverage reporting over the bounded registry grid. Each row
    carries:

    - availability_state: `disabled` (registry-owned), `unknown` (no
      ledger row for the slice yet) or the latest evidence-backed
      state from ops.source_file_availability (available /
      not_published / invalid).
    - load_status: `disabled`, `pending` (DERIVED: no
      ops.ingestion_manifest row means the load never started) or the
      latest stored status (running / success / failed).

    The grid is read-only and bounded by the same registration rules
    as list_city_datasets: an unregistered city or an uncontrolled
    dataset tag is refused, never silently skipped.
    """
    cities = _airbnb_cities(project_config)
    rows: list[dict[str, Any]] = []
    for city_id, city_config in cities.items():
        entry = get_city(registry, str(city_id))
        if entry is None:
            raise ValueError(
                f"city {city_id!r} is configured in project.yml but not "
                "registered in the city registry; register it first or remove "
                "its configuration"
            )
        enabled = entry.get("enabled") is True
        datasets = city_config.get("datasets")
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError(
                f"city {city_id!r}: 'datasets' must be a non-empty mapping of "
                "controlled dataset tags"
            )
        for dataset in datasets:
            if dataset not in INGESTION_DATASETS:
                raise ValueError(
                    f"city {city_id!r}: unknown dataset tag {dataset!r}; "
                    "expected one of: " + ", ".join(INGESTION_DATASETS)
                )
            slice_row: dict[str, Any] = {
                "city_id": str(city_id),
                "dataset": str(dataset),
            }
            if not enabled:
                slice_row["availability_state"] = "disabled"
                slice_row["load_status"] = "disabled"
                rows.append(slice_row)
                continue
            availability_rows = availability_store.list_by_city_dataset(
                str(city_id), str(dataset)
            )
            slice_row["availability_state"] = (
                _latest_value(
                    availability_rows, ("checked_at_utc",), "availability_state"
                )
                or "unknown"
            )
            load_rows = ingestion_store.list_for_city_dataset(
                str(city_id), str(dataset)
            )
            slice_row["load_status"] = (
                _latest_value(
                    load_rows, ("completed_at_utc", "started_at_utc"), "status"
                )
                or "pending"
            )
            rows.append(slice_row)
    return rows
