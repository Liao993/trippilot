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

from src.common.city_registry import (
    find_registry_problems,
    get_city,
    get_enabled_cities,
)


def _entry(**overrides):
    entry = {
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
    entry.update(overrides)
    return {key: value for key, value in entry.items() if value is not None}


def _registry(*entries):
    return {"version": 1, "cities": list(entries)}


VALID_REGISTRY = _registry(_entry())


def test_valid_registry_has_no_problems():
    assert find_registry_problems(VALID_REGISTRY) == []


def test_returns_only_enabled_city_ids():
    registry = _registry(
        _entry(city_id="toronto"),
        _entry(city_id="vancouver", display_name="Vancouver", enabled=False),
        _entry(city_id="montreal", display_name="Montreal"),
    )

    assert get_enabled_cities(registry) == ["toronto", "montreal"]


def test_missing_enabled_flag_means_disabled():
    assert get_enabled_cities(_registry(_entry(enabled=None))) == []


def test_empty_registry_returns_empty_list():
    assert get_enabled_cities({"version": 1, "cities": []}) == []


def test_get_city_returns_exact_immutable_id():
    city = get_city(VALID_REGISTRY, "toronto")

    assert city is not None
    assert city["city_id"] == "toronto"
    assert city["display_name"] == "Toronto"


def test_get_city_resolves_disabled_entries_without_guessing():
    registry = _registry(
        _entry(city_id="vancouver", display_name="Vancouver", enabled=False)
    )

    assert get_city(registry, "vancouver")["enabled"] is False


def test_get_city_returns_none_for_unknown_or_renamed_city():
    assert get_city(VALID_REGISTRY, "Toronto") is None
    assert get_city(VALID_REGISTRY, "yyz") is None


def test_get_city_rejects_blank_lookup():
    with pytest.raises(ValueError):
        get_city(VALID_REGISTRY, "   ")


def test_get_city_rejects_non_mapping_registry():
    with pytest.raises(TypeError):
        get_city(["cities"], "toronto")


@pytest.mark.parametrize(
    "overrides, expected_fragment",
    [
        ({"city_id": None}, "'city_id' must be a non-empty string"),
        ({"city_id": "Toronto"}, "lowercase slug form"),
        ({"slug": None}, "'slug' must be a non-empty string"),
        ({"slug": "YYZ"}, "lowercase slug form"),
        ({"slug": "yyz"}, "must equal the immutable city_id"),
        ({"display_name": None}, "'display_name' must be a non-empty string"),
        ({"country_code": "CAN"}, "2-letter ISO 3166-1 alpha-2"),
        ({"region": None}, "'region' must be a non-empty string"),
        ({"timezone": "EST"}, "IANA timezone"),
        ({"enabled": None}, "'enabled' must be a boolean"),
        ({"enabled": "true"}, "'enabled' must be a boolean"),
        ({"currency": "ca"}, "3-letter ISO 4217"),
        ({"latitude": 95.0}, "between -90 and 90"),
        ({"latitude": True}, "between -90 and 90"),
        ({"longitude": -200.0}, "between -180 and 180"),
    ],
)
def test_find_registry_problems_reports_bad_fields(overrides, expected_fragment):
    problems = find_registry_problems(_registry(_entry(**overrides)))

    assert any(expected_fragment in problem for problem in problems)


def test_registry_problems_reports_non_mapping():
    assert find_registry_problems(["not", "a", "mapping"]) == [
        "registry must be a mapping"
    ]


def test_registry_problems_reports_missing_version():
    problems = find_registry_problems({"cities": [_entry()]})

    assert any("version" in problem for problem in problems)


def test_registry_problems_reports_bad_version():
    problems = find_registry_problems({"version": 0, "cities": [_entry()]})

    assert any("version" in problem for problem in problems)


def test_registry_problems_reports_empty_cities():
    problems = find_registry_problems({"version": 1, "cities": []})

    assert any("'cities' must be a non-empty list" for problem in problems)


def test_registry_problems_reports_non_mapping_entry():
    problems = find_registry_problems({"version": 1, "cities": ["toronto"]})

    assert any("cities[0] must be a mapping" for problem in problems)


def test_registry_problems_reports_duplicate_city_ids():
    registry = _registry(_entry(), _entry())

    problems = find_registry_problems(registry)

    assert any("duplicate city_id" in problem for problem in problems)


def test_registry_problems_reports_duplicate_slugs():
    registry = _registry(
        _entry(),
        _entry(city_id="montreal", display_name="Montreal"),
    )

    problems = find_registry_problems(registry)

    assert any("duplicate slug" in problem for problem in problems)
