"""Unit tests for the registry-driven control plane (F08.4).

Pure Python: registry/project fixtures and a stub manifest store. The
bounded-selection rules (unregistered city, disabled city, unregistered
dataset, malformed config) are exercised with exact error matches, so
selection can never silently fall back to a guess.
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

from src.common.city_registry import find_registry_problems
from src.common.control_plane import (
    build_city_dataset_coverage,
    list_city_datasets,
    select_landed_source_file,
)

REGISTRY = {
    "version": 1,
    "cities": [
        {
            "city_id": "toronto",
            "slug": "toronto",
            "display_name": "Toronto",
            "country_code": "CA",
            "region": "Ontario",
            "timezone": "America/Toronto",
            "enabled": True,
        },
        {
            "city_id": "hamburg",
            "slug": "hamburg",
            "display_name": "Hamburg",
            "country_code": "DE",
            "region": "Hamburg",
            "timezone": "Europe/Berlin",
            "enabled": False,
        },
    ],
}

LANDED_RECORD = {
    "source_file_id": "a" * 64,
    "source_family": "insideairbnb",
    "source_entity_id": "toronto",
    "source_version": "2026-09-16",
    "file_type": "csv.gz",
    "dataset": "listings",
    "processing_state": "landed",
    "landing_path": "/Volumes/trippilot_dev/bronze/source_files/insideairbnb/toronto/listings.csv.gz",
}


def _project(**overrides):
    config = {
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
                            },
                            "calendar": {
                                "file": "calendar.csv.gz",
                                "file_type": "csv.gz",
                                "required_identifier": "listing_id",
                            },
                        }
                    },
                    "hamburg": {
                        "datasets": {
                            "listings": {
                                "file": "listings.csv.gz",
                                "file_type": "csv.gz",
                                "required_identifier": "id",
                            },
                        }
                    },
                },
            }
        }
    }
    config.update(overrides)
    return config


class StubManifestStore:
    def __init__(self, record=None):
        self.record = record
        self.calls = []

    def read_landed_by_dataset(self, city_id, dataset, source_version=None):
        self.calls.append((city_id, dataset, source_version))
        if self.record is None:
            raise ValueError("toronto/listings: no landed manifest record found")
        return self.record


def test_registry_fixture_is_structurally_valid():
    # Guards the fixture itself against registry-rule drift.
    assert find_registry_problems(REGISTRY) == []


def test_list_city_datasets_returns_enabled_slices_in_config_order():
    rows = list_city_datasets(_project(), REGISTRY)

    # hamburg is registered but disabled: excluded by design.
    assert [(row["city_id"], row["dataset"]) for row in rows] == [
        ("toronto", "listings"),
        ("toronto", "calendar"),
    ]
    listings = rows[0]
    assert listings["file"] == "listings.csv.gz"
    assert listings["file_type"] == "csv.gz"
    assert listings["required_identifier"] == "id"


def test_list_city_datasets_refuses_an_unregistered_city():
    project = _project()
    project["sources"]["airbnb"]["cities"]["atlantis"] = {
        "datasets": {"listings": {"file": "listings.csv.gz"}}
    }

    with pytest.raises(ValueError, match="not registered"):
        list_city_datasets(project, REGISTRY)


def test_list_city_datasets_refuses_unknown_dataset_tags():
    project = _project()
    project["sources"]["airbnb"]["cities"]["toronto"]["datasets"]["misc"] = {
        "file": "misc.csv",
        "file_type": "csv",
        "required_identifier": "id",
    }

    with pytest.raises(ValueError, match="unknown dataset tag"):
        list_city_datasets(project, REGISTRY)


def test_list_city_datasets_refuses_an_empty_dataset_registration():
    project = _project()
    project["sources"]["airbnb"]["cities"]["toronto"]["datasets"] = {}

    with pytest.raises(ValueError, match="non-empty mapping"):
        list_city_datasets(project, REGISTRY)


def test_select_returns_the_landed_record_for_a_registered_slice():
    store = StubManifestStore(record=LANDED_RECORD)

    record = select_landed_source_file(
        store, _project(), REGISTRY, "toronto", "listings"
    )

    assert record is LANDED_RECORD
    assert store.calls == [("toronto", "listings", None)]


def test_select_forwards_the_source_version():
    store = StubManifestStore(record=LANDED_RECORD)

    select_landed_source_file(
        store, _project(), REGISTRY, "toronto", "listings", "2026-09-16"
    )

    assert store.calls == [("toronto", "listings", "2026-09-16")]


def test_select_refuses_an_unregistered_city():
    store = StubManifestStore(record=LANDED_RECORD)

    with pytest.raises(ValueError, match="not registered"):
        select_landed_source_file(store, _project(), REGISTRY, "atlantis", "listings")

    assert store.calls == []


def test_select_refuses_a_disabled_city():
    store = StubManifestStore(record=LANDED_RECORD)

    with pytest.raises(ValueError, match="disabled"):
        select_landed_source_file(store, _project(), REGISTRY, "hamburg", "listings")

    assert store.calls == []


def test_select_refuses_an_unregistered_dataset():
    store = StubManifestStore(record=LANDED_RECORD)

    with pytest.raises(ValueError, match="not registered for city"):
        select_landed_source_file(store, _project(), REGISTRY, "toronto", "reviews")

    assert store.calls == []


class StubAvailabilityStore:
    def __init__(self, rows):
        # rows: {(city_id, dataset): [ledger rows, newest last]}
        self.rows = rows

    def list_by_city_dataset(self, city_id, dataset):
        return self.rows.get((city_id, dataset), [])


class StubIngestionStore:
    def __init__(self, rows):
        # rows: {(city_id, dataset): [manifest rows]}
        self.rows = rows

    def list_for_city_dataset(self, city_id, dataset):
        return self.rows.get((city_id, dataset), [])


def _availability(state, checked_at, **overrides):
    row = {
        "availability_state": state,
        "checked_at_utc": checked_at,
    }
    row.update(overrides)
    return row


def _load(status, completed_at=None, started_at=None):
    return {
        "status": status,
        "completed_at_utc": completed_at,
        "started_at_utc": started_at,
    }


def test_coverage_grid_covers_every_configured_slice():
    coverage = build_city_dataset_coverage(
        _project(),
        REGISTRY,
        StubAvailabilityStore(
            {
                ("toronto", "listings"): [
                    _availability("available", "2026-11-01T10:00:00+00:00")
                ]
            }
        ),
        StubIngestionStore(
            {
                ("toronto", "listings"): [
                    _load("success", "2026-11-02T10:00:00+00:00")
                ],
                ("toronto", "calendar"): [
                    _load("running", started_at="2026-11-03T10:00:00+00:00")
                ],
            }
        ),
    )

    assert coverage == [
        {
            "city_id": "toronto",
            "dataset": "listings",
            "availability_state": "available",
            "load_status": "success",
        },
        {
            "city_id": "toronto",
            "dataset": "calendar",
            "availability_state": "unknown",
            "load_status": "running",
        },
        {
            "city_id": "hamburg",
            "dataset": "listings",
            "availability_state": "disabled",
            "load_status": "disabled",
        },
    ]


def test_coverage_derives_pending_and_unknown_from_missing_rows():
    coverage = build_city_dataset_coverage(
        _project(),
        REGISTRY,
        StubAvailabilityStore({}),
        StubIngestionStore({}),
    )

    toronto_listings = next(
        row
        for row in coverage
        if row["city_id"] == "toronto" and row["dataset"] == "listings"
    )
    assert toronto_listings["availability_state"] == "unknown"
    assert toronto_listings["load_status"] == "pending"


def test_coverage_uses_the_latest_ledger_and_manifest_rows():
    coverage = build_city_dataset_coverage(
        _project(),
        REGISTRY,
        StubAvailabilityStore(
            {
                ("toronto", "listings"): [
                    _availability("available", "2026-10-01T10:00:00+00:00"),
                    _availability("not_published", "2026-11-01T10:00:00+00:00"),
                ]
            }
        ),
        StubIngestionStore(
            {
                ("toronto", "listings"): [
                    _load("success", "2026-10-01T10:00:00+00:00"),
                    _load("failed", "2026-11-01T11:00:00+00:00"),
                ]
            }
        ),
    )

    toronto_listings = next(
        row
        for row in coverage
        if row["city_id"] == "toronto" and row["dataset"] == "listings"
    )
    assert toronto_listings["availability_state"] == "not_published"
    assert toronto_listings["load_status"] == "failed"


def test_coverage_refuses_an_unregistered_city():
    project = _project()
    project["sources"]["airbnb"]["cities"]["atlantis"] = {
        "datasets": {"listings": {"file": "listings.csv.gz"}}
    }

    with pytest.raises(ValueError, match="not registered"):
        build_city_dataset_coverage(
            project, REGISTRY, StubAvailabilityStore({}), StubIngestionStore({})
        )


def test_coverage_refuses_unknown_dataset_tags():
    project = _project()
    project["sources"]["airbnb"]["cities"]["toronto"]["datasets"]["misc"] = {
        "file": "misc.csv",
        "file_type": "csv",
        "required_identifier": "id",
    }

    with pytest.raises(ValueError, match="unknown dataset tag"):
        build_city_dataset_coverage(
            project, REGISTRY, StubAvailabilityStore({}), StubIngestionStore({})
        )


def test_select_requires_city_and_dataset_arguments():
    store = StubManifestStore(record=LANDED_RECORD)

    with pytest.raises(ValueError, match="city_id is required"):
        select_landed_source_file(store, _project(), REGISTRY, " ", "listings")

    with pytest.raises(ValueError, match="dataset is required"):
        select_landed_source_file(store, _project(), REGISTRY, "toronto", "")
