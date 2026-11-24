"""Stable city registry lookups (F08.1).

Pure Python: the registry is a parsed YAML mapping; tests pass small
hardcoded inputs. Each registered city has one immutable city_id -
the canonical lowercase slug form used as source_entity_id by the
source-file manifest and as _city by Bronze provenance - plus
human-facing display metadata (display name, country, region,
timezone, currency, coordinates). city_id never changes once
assigned; only the entry's enabled flag may be toggled.

City-level enablement lives ONLY here. config/project.yml owns
dataset/provider configuration per registered city, never
enablement.
"""

import re
from typing import Any

REQUIRED_CITY_FIELDS = (
    "city_id",
    "slug",
    "display_name",
    "country_code",
    "region",
    "timezone",
    "enabled",
)
OPTIONAL_CITY_FIELDS = ("currency", "latitude", "longitude", "boundary_reference")

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z0-9_+\-]+(/[A-Za-z0-9_+\-]+)+$")


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def get_city(registry: Any, city_id: str) -> dict[str, Any] | None:
    """Return the registry entry for one immutable city_id, or None.

    Lookup is by exact city_id match; it never falls back to a display
    name, slug or case-insensitive match, so a renamed or unregistered
    city resolves to None and callers must not guess.
    """
    if not isinstance(registry, dict):
        raise TypeError("city registry must be a mapping")
    if not _is_nonempty_string(city_id):
        raise ValueError("city_id is required for a registry lookup")
    for entry in registry.get("cities") or []:
        if isinstance(entry, dict) and entry.get("city_id") == city_id:
            return dict(entry)
    return None


def get_enabled_cities(registry: Any) -> list[str]:
    """Return the city_id list of every enabled registered city.

    An entry whose enabled flag is not exactly True is treated as
    disabled: an incompletely registered city is never silently
    ingested.
    """
    if not isinstance(registry, dict):
        raise TypeError("city registry must be a mapping")
    enabled: list[str] = []
    for entry in registry.get("cities") or []:
        if (
            isinstance(entry, dict)
            and entry.get("enabled") is True
            and _is_nonempty_string(entry.get("city_id"))
        ):
            enabled.append(str(entry["city_id"]))
    return enabled


def find_registry_problems(registry: Any) -> list[str]:
    """Return every structural problem of a parsed city registry.

    One shared definition of a well-formed entry is enforced here and
    reused by src.quality.config_validation, so a malformed city can
    never reach the ingestion control plane.
    """
    if not isinstance(registry, dict):
        return ["registry must be a mapping"]

    problems: list[str] = []
    version = registry.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        problems.append("version must be a positive integer")

    cities = registry.get("cities")
    if not isinstance(cities, list) or len(cities) == 0:
        problems.append("'cities' must be a non-empty list")
        return problems

    seen_city_ids: dict[str, int] = {}
    seen_slugs: dict[str, int] = {}
    for index, entry in enumerate(cities):
        label = f"cities[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{label} must be a mapping")
            continue

        if not _is_nonempty_string(entry.get("city_id")):
            problems.append(f"{label} 'city_id' must be a non-empty string")
        elif not _SLUG_PATTERN.fullmatch(str(entry["city_id"])):
            problems.append(
                f"{label} 'city_id' must be the lowercase slug form "
                f"(letters, digits, hyphens), got {entry['city_id']!r}"
            )

        slug = entry.get("slug")
        if not _is_nonempty_string(slug):
            problems.append(f"{label} 'slug' must be a non-empty string")
        else:
            if not _SLUG_PATTERN.fullmatch(str(slug)):
                problems.append(
                    f"{label} 'slug' must be the lowercase slug form "
                    f"(letters, digits, hyphens), got {slug!r}"
                )
            elif _is_nonempty_string(entry.get("city_id")) and str(slug) != str(
                entry["city_id"]
            ):
                problems.append(
                    f"{label} 'slug' must equal the immutable city_id "
                    f"(got {slug!r} vs {entry['city_id']!r})"
                )

        for field in ("display_name", "region"):
            if not _is_nonempty_string(entry.get(field)):
                problems.append(f"{label} {field!r} must be a non-empty string")

        country = entry.get("country_code")
        if not _is_nonempty_string(country) or not _COUNTRY_PATTERN.fullmatch(
            str(country)
        ):
            problems.append(
                f"{label} 'country_code' must be a 2-letter ISO 3166-1 "
                f"alpha-2 code, got {country!r}"
            )

        timezone = entry.get("timezone")
        if not _is_nonempty_string(timezone) or not _TIMEZONE_PATTERN.fullmatch(
            str(timezone)
        ):
            problems.append(
                f"{label} 'timezone' must be an IANA timezone name "
                f"(for example America/Toronto), got {timezone!r}"
            )

        if not isinstance(entry.get("enabled"), bool):
            problems.append(f"{label} 'enabled' must be a boolean")

        currency = entry.get("currency")
        if currency is not None and (
            not _is_nonempty_string(currency)
            or not _CURRENCY_PATTERN.fullmatch(str(currency))
        ):
            problems.append(
                f"{label} 'currency' must be a 3-letter ISO 4217 code, got {currency!r}"
            )

        latitude = entry.get("latitude")
        if latitude is not None and (
            not _is_number(latitude) or not -90 <= latitude <= 90
        ):
            problems.append(f"{label} 'latitude' must be a number between -90 and 90")

        longitude = entry.get("longitude")
        if longitude is not None and (
            not _is_number(longitude) or not -180 <= longitude <= 180
        ):
            problems.append(
                f"{label} 'longitude' must be a number between -180 and 180"
            )

        boundary = entry.get("boundary_reference")
        if boundary is not None and not _is_nonempty_string(boundary):
            problems.append(f"{label} 'boundary_reference' must be a non-empty string")

        city_id = entry.get("city_id")
        if _is_nonempty_string(city_id):
            if str(city_id) in seen_city_ids:
                problems.append(
                    f"{label} duplicate city_id {city_id!r} (already registered "
                    f"at cities[{seen_city_ids[str(city_id)]}]"
                )
            else:
                seen_city_ids[str(city_id)] = index
        if _is_nonempty_string(slug):
            if str(slug) in seen_slugs:
                problems.append(
                    f"{label} duplicate slug {slug!r} (already registered "
                    f"at cities[{seen_slugs[str(slug)]}]"
                )
            else:
                seen_slugs[str(slug)] = index

    return problems
