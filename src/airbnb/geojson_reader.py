"""Parse a GeoJSON FeatureCollection into Bronze rows (F07.2-T02).

One row per feature: the observed property keys as raw strings plus
the full geometry object preserved as a compact JSON string in
``geometry_json`` - spatial information is never flattened away. A
feature without a usable geometry yields a NULL ``geometry_json``
(flagged by the contract's row validation, never dropped), and a
feature missing a property key yields NULL for that key.

Pure Python (json + pathlib): no Spark, CI-safe, and deterministic for
identical bytes, so Bronze raw-row reconciliation is exact.
"""

import json
from pathlib import Path
from typing import Any


def _is_feature_collection(document: Any) -> bool:
    """Whether the parsed document is a FeatureCollection with a features array."""
    return (
        isinstance(document, dict)
        and document.get("type") == "FeatureCollection"
        and isinstance(document.get("features"), list)
    )


def parse_geojson_features(
    path: str | Path,
    property_keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return one row dict per feature in the FeatureCollection at path.

    property_keys (default: the sorted union across all features, the
    same canonical set inspect_geojson reports) selects the property
    columns; every row carries the same keys plus ``geometry_json``.
    Property values stay raw strings (non-string scalars are
    stringified, missing keys are NULL); ``geometry_json`` is the
    feature's full geometry object serialized as compact JSON, or NULL
    when the feature has no geometry object.

    Raises a clear ValueError when the file is not a FeatureCollection.
    """
    file = Path(path)
    try:
        document = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{file}: not readable as JSON ({error})") from error
    if not _is_feature_collection(document):
        raise ValueError(
            f"{file}: expected a GeoJSON FeatureCollection with a features array"
        )
    features = document["features"]

    if property_keys is None:
        property_keys = sorted(
            {
                key
                for feature in features
                if isinstance(feature, dict)
                for key in (feature.get("properties") or {})
            }
        )

    rows: list[dict[str, Any]] = []
    for feature in features:
        row: dict[str, Any] = {key: None for key in property_keys}
        geometry_json: str | None = None
        if isinstance(feature, dict):
            properties = feature.get("properties") or {}
            for key in property_keys:
                row[key] = _raw_string(properties.get(key))
            geometry = feature.get("geometry")
            if isinstance(geometry, dict):
                geometry_json = json.dumps(geometry, separators=(",", ":"))
        row["geometry_json"] = geometry_json
        rows.append(row)
    return rows


def _raw_string(value: Any) -> str | None:
    """Keep raw text as-is; stringify present non-string scalars, NULL otherwise."""
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)
