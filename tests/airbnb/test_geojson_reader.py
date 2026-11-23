"""Tests for the GeoJSON Bronze row parser (F07.2-T02).

Pure-Python tests on synthetic FeatureCollections under pytest's
tmp_path: no Spark, no Volume. They prove the one-row-per-feature
grain, verbatim geometry preservation, NULL handling for missing
properties/geometries, and rejection of non-FeatureCollection inputs.
"""

import json
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

from src.airbnb.geojson_reader import parse_geojson_features


def _write_geojson(path, features):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )
    return path


def _feature(name, group="", geometry=None):
    return {
        "type": "Feature",
        "properties": {"neighbourhood": name, "neighbourhood_group": group},
        "geometry": geometry
        or {"type": "MultiPolygon", "coordinates": [[[[0.0, 0.0]]]]},
    }


def test_one_row_per_feature_with_all_property_keys(tmp_path):
    source = _write_geojson(
        tmp_path / "n.geojson",
        [
            _feature("A", group=""),
            {**_feature("B"), "properties": {"neighbourhood": "B"}},
        ],
    )

    rows = parse_geojson_features(source)

    assert len(rows) == 2
    assert set(rows[0]) == {"neighbourhood", "neighbourhood_group", "geometry_json"}
    assert rows[0]["neighbourhood"] == "A"
    assert rows[0]["neighbourhood_group"] == ""
    # A feature missing a property key yields NULL for it - never dropped.
    assert rows[1]["neighbourhood_group"] is None


def test_geometry_object_is_preserved_verbatim(tmp_path):
    geometry = {"type": "MultiPolygon", "coordinates": [[[[1.5, 2.5], [3.5, 4.5]]]]}
    source = _write_geojson(
        tmp_path / "n.geojson", [{**_feature("A"), "geometry": geometry}]
    )

    rows = parse_geojson_features(source)

    assert json.loads(rows[0]["geometry_json"]) == geometry


def test_feature_without_geometry_yields_null_geometry_json(tmp_path):
    source = _write_geojson(
        tmp_path / "n.geojson", [{**_feature("A"), "geometry": None}]
    )

    rows = parse_geojson_features(source)

    assert rows[0]["neighbourhood"] == "A"
    assert rows[0]["geometry_json"] is None


def test_non_dict_feature_yields_an_all_null_row(tmp_path):
    source = _write_geojson(tmp_path / "n.geojson", ["garbage", _feature("B")])

    rows = parse_geojson_features(source)

    assert len(rows) == 2
    assert rows[0] == {
        "neighbourhood": None,
        "neighbourhood_group": None,
        "geometry_json": None,
    }
    assert rows[1]["neighbourhood"] == "B"


def test_non_string_property_values_are_stringified(tmp_path):
    feature = _feature("A")
    feature["properties"] = {"neighbourhood": "A", "population": 12345}
    source = _write_geojson(tmp_path / "n.geojson", [feature])

    rows = parse_geojson_features(source)

    assert rows[0]["population"] == "12345"


def test_explicit_property_keys_drive_the_columns(tmp_path):
    source = _write_geojson(tmp_path / "n.geojson", [_feature("A"), _feature("B")])

    rows = parse_geojson_features(source, property_keys=["neighbourhood"])

    assert set(rows[0]) == {"neighbourhood", "geometry_json"}


@pytest.mark.parametrize("text", ["{not json", '{"type": "Point", "coordinates": []}'])
def test_non_feature_collection_is_rejected(tmp_path, text):
    source = tmp_path / "bad.geojson"
    source.write_text(text, encoding="utf-8")

    # Invalid JSON raises "not readable as JSON"; valid JSON that is not
    # a FeatureCollection raises the structural message. Either way the
    # reader refuses to produce rows.
    with pytest.raises(ValueError, match="not readable as JSON|FeatureCollection"):
        parse_geojson_features(source)
