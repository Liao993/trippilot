"""Tests for the Airbnb source inspection helpers (F05.1 / F07.1).

These tests prove the helpers read the exact observed schema — ordered
columns, duplicates, missing names, content-addressed fingerprints —
from real gzip/plain CSV files and GeoJSON FeatureCollections, so the
manifest's schema_version describes the registered bytes instead of
an assumed schema.
"""

import gzip
import json

import pytest

from src.airbnb.geojson_reader import parse_geojson_features
from src.airbnb.source_inspection import (
    check_required_columns,
    inspect_csv_gz_header,
    inspect_csv_header,
    inspect_geojson,
    read_csv_gz_header_line,
    read_csv_header_line,
    verify_gzip_integrity,
)


def _write_gzip_csv(path, header, rows=("1,alpha\n",)):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as file:
        file.write(header + "\n")
        for row in rows:
            file.write(row)
    return path


def test_inspection_returns_ordered_columns_and_count(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv.gz", "id,name,price")

    result = inspect_csv_gz_header(source)

    assert result["columns"] == ["id", "name", "price"]
    assert result["column_count"] == 3
    assert result["header_line"] == "id,name,price"
    assert result["byte_size"] == source.stat().st_size


def test_inspection_detects_duplicate_and_missing_names(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv.gz", "id,name,id,price,")

    result = inspect_csv_gz_header(source)

    assert result["duplicate_columns"] == ["id"]
    assert result["missing_columns"] == [4]  # trailing comma -> empty name
    assert result["column_count"] == 5


def test_inspection_handles_quoted_header_names(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv.gz", 'id,"name, quoted",price')

    result = inspect_csv_gz_header(source)

    assert result["columns"] == ["id", "name, quoted", "price"]


def test_fingerprint_is_deterministic_and_header_sensitive(tmp_path):
    first = _write_gzip_csv(tmp_path / "a.csv.gz", "id,name")
    second = _write_gzip_csv(tmp_path / "b.csv.gz", "id,name,price")
    twin = _write_gzip_csv(tmp_path / "c.csv.gz", "id,name")

    a = inspect_csv_gz_header(first)
    b = inspect_csv_gz_header(second)
    c = inspect_csv_gz_header(twin)

    assert a["schema_fingerprint"] == c["schema_fingerprint"]
    assert a["schema_fingerprint"] != b["schema_fingerprint"]
    assert a["schema_fingerprint"].startswith("sha256:")
    assert len(a["schema_fingerprint"]) == len("sha256:") + 64
    assert a["schema_version"] == (
        "detailed-listings-sha256:" + a["schema_fingerprint"][7:23]
    )


def test_clean_header_produces_no_problem_reports(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv.gz", "id,name")

    result = inspect_csv_gz_header(source)

    assert result["duplicate_columns"] == []
    assert result["missing_columns"] == []


# --- F06.1: schema_version labels the source dataset ------------------


def test_schema_version_uses_the_requested_schema_label(tmp_path):
    source = _write_gzip_csv(tmp_path / "calendar.csv.gz", "listing_id,date,available")

    result = inspect_csv_gz_header(source, schema_label="calendar")

    assert result["schema_version"] == (
        "calendar-sha256:" + result["schema_fingerprint"][7:23]
    )


def test_schema_version_accepts_the_detailed_reviews_label(tmp_path):
    source = _write_gzip_csv(tmp_path / "reviews.csv.gz", "listing_id,id,date")

    result = inspect_csv_gz_header(source, schema_label="detailed-reviews")

    assert result["schema_version"] == (
        "detailed-reviews-sha256:" + result["schema_fingerprint"][7:23]
    )


def test_schema_label_rejects_blank_labels(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv.gz", "id,name")

    with pytest.raises(ValueError, match="schema_label"):
        inspect_csv_gz_header(source, schema_label="   ")


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "empty",
        "not_gzip",
        "no_header",
    ],
)
def test_rejects_broken_sources(tmp_path, case):
    path = tmp_path / f"{case}.csv.gz"
    if case == "missing":
        path = tmp_path / "does_not_exist.csv.gz"
    elif case == "empty":
        path.write_bytes(b"")
    elif case == "not_gzip":
        path.write_bytes(b"plain text, not gzip")
    elif case == "no_header":
        with gzip.open(path, "wt", encoding="utf-8") as file:
            file.write("")

    with pytest.raises(ValueError):
        read_csv_gz_header_line(path)


def test_header_line_strips_crlf(tmp_path):
    path = tmp_path / "crlf.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as file:
        file.write("id,name\r\n1,alpha\r\n")

    assert read_csv_gz_header_line(path) == "id,name"


# --- F05.3: full-stream integrity and contract column checks ----------


def test_gzip_integrity_returns_decompressed_size(tmp_path):
    source = _write_gzip_csv(
        tmp_path / "listings.csv.gz", "id,name", rows=("1,alpha\n", "2,beta\n")
    )

    decompressed = verify_gzip_integrity(source)

    assert decompressed == len(b"id,name\n1,alpha\n2,beta\n")


def test_gzip_integrity_rejects_corrupt_stream(tmp_path):
    source = _write_gzip_csv(
        tmp_path / "listings.csv.gz", "id,name", rows=("1,alpha\n",)
    )
    compressed = bytearray(source.read_bytes())
    compressed[-6] ^= 0xFF  # corrupt the gzip trailer
    corrupted = tmp_path / "corrupt.csv.gz"
    corrupted.write_bytes(bytes(compressed))

    with pytest.raises(ValueError, match="not readable end-to-end"):
        verify_gzip_integrity(corrupted)


def test_gzip_integrity_rejects_truncated_stream(tmp_path):
    source = _write_gzip_csv(
        tmp_path / "listings.csv.gz", "id,name", rows=("1,alpha\n",)
    )
    truncated = tmp_path / "truncated.csv.gz"
    truncated.write_bytes(source.read_bytes()[:-10])

    with pytest.raises(ValueError):
        verify_gzip_integrity(truncated)


@pytest.mark.parametrize("case", ["missing", "empty", "not_gzip", "decompresses_empty"])
def test_gzip_integrity_rejects_unusable_sources(tmp_path, case):
    path = tmp_path / "bad.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    if case == "missing":
        path = tmp_path / "does_not_exist.csv.gz"
    elif case == "empty":
        path.write_bytes(b"")
    elif case == "not_gzip":
        path.write_bytes(b"plain text, not gzip")
    elif case == "decompresses_empty":
        with gzip.open(path, "wt", encoding="utf-8") as file:
            file.write("")

    with pytest.raises(ValueError):
        verify_gzip_integrity(path)


def test_required_columns_pass_when_present():
    assert check_required_columns(["id", "name", "price"], ["id", "price"]) == []


def test_required_columns_check_reports_missing_in_order():
    missing = check_required_columns(["id", "name"], ["price", "id", "latitude"])

    assert missing == ["price", "latitude"]


# --- F07.1 D4: plain (uncompressed) CSV header inspection --------------


def _write_plain_csv(path, header, rows=("1,alpha\n",)):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wt", encoding="utf-8", newline="") as file:
        file.write(header + "\n")
        for row in rows:
            file.write(row)
    return path


def test_plain_csv_inspection_matches_gzip_facts(tmp_path):
    plain = _write_plain_csv(tmp_path / "listings.csv", "id,name,price")
    gz = _write_gzip_csv(tmp_path / "listings.csv.gz", "id,name,price")

    plain_result = inspect_csv_header(plain, schema_label="summary-listings")
    gz_result = inspect_csv_gz_header(gz, schema_label="summary-listings")

    assert plain_result["schema_fingerprint"] == gz_result["schema_fingerprint"]
    assert plain_result["schema_version"] == gz_result["schema_version"]
    assert plain_result["columns"] == ["id", "name", "price"]
    assert plain_result["column_count"] == 3
    assert plain_result["duplicate_columns"] == []
    assert plain_result["missing_columns"] == []
    assert plain_result["byte_size"] == plain.stat().st_size


def test_plain_csv_inspection_uses_the_requested_schema_label(tmp_path):
    source = _write_plain_csv(
        tmp_path / "neighbourhoods.csv", "neighbourhood_group,neighbourhood"
    )

    result = inspect_csv_header(source, schema_label="neighbourhoods")

    assert result["schema_version"] == (
        "neighbourhoods-sha256:" + result["schema_fingerprint"][7:23]
    )


def test_plain_csv_inspection_rejects_gzip_content(tmp_path):
    source = _write_gzip_csv(tmp_path / "listings.csv", "id,name")

    with pytest.raises(ValueError, match="gzip-compressed"):
        inspect_csv_header(source)


def test_plain_csv_inspection_rejects_headerless_files(tmp_path):
    path = tmp_path / "headerless.csv"
    path.write_text("\n1,alpha\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no header line"):
        read_csv_header_line(path)


def test_plain_csv_inspection_rejects_blank_schema_labels(tmp_path):
    source = _write_plain_csv(tmp_path / "listings.csv", "id,name")

    with pytest.raises(ValueError, match="schema_label"):
        inspect_csv_header(source, schema_label="   ")


# --- F07.1 D4 / F07.2-T03: GeoJSON FeatureCollection inspection ---------


def _write_geojson(path, features):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )
    return path


def _feature(name, group="", geometry_type="MultiPolygon"):
    return {
        "type": "Feature",
        "properties": {"neighbourhood": name, "neighbourhood_group": group},
        "geometry": {"type": geometry_type, "coordinates": [[[[0.0, 0.0]]]]},
    }


def test_geojson_inspection_reports_structure_and_counts(tmp_path):
    source = _write_geojson(tmp_path / "n.geojson", [_feature("A"), _feature("B")])

    result = inspect_geojson(source, schema_label="neighbourhood-geojson")

    assert result["geojson_type"] == "FeatureCollection"
    assert result["feature_count"] == 2
    assert result["columns"] == ["neighbourhood", "neighbourhood_group"]
    assert result["geometry_types"] == ["MultiPolygon"]
    assert result["byte_size"] == source.stat().st_size


def test_geojson_fingerprint_is_deterministic_and_sensitive(tmp_path):
    a = _write_geojson(tmp_path / "a.geojson", [_feature("A"), _feature("B")])
    b = _write_geojson(
        tmp_path / "b.geojson", [_feature("A", geometry_type="Polygon"), _feature("B")]
    )
    twin = _write_geojson(tmp_path / "c.geojson", [_feature("A"), _feature("B")])

    ra = inspect_geojson(a, schema_label="neighbourhood-geojson")
    rb = inspect_geojson(b, schema_label="neighbourhood-geojson")
    rc = inspect_geojson(twin, schema_label="neighbourhood-geojson")

    assert ra["schema_fingerprint"] == rc["schema_fingerprint"]
    assert ra["schema_fingerprint"] != rb["schema_fingerprint"]
    assert ra["schema_version"] == (
        "neighbourhood-geojson-sha256:" + ra["schema_fingerprint"][7:23]
    )


@pytest.mark.parametrize(
    "case",
    [
        "invalid_json",
        "wrong_type",
        "features_not_list",
        "empty",
    ],
)
def test_geojson_inspection_rejects_broken_sources(tmp_path, case):
    path = tmp_path / "bad.geojson"
    if case == "invalid_json":
        path.write_text("{not json", encoding="utf-8")
    elif case == "wrong_type":
        path.write_text('{"type": "Polygon", "coordinates": []}', encoding="utf-8")
    elif case == "features_not_list":
        path.write_text(
            '{"type": "FeatureCollection", "features": {}}', encoding="utf-8"
        )
    elif case == "empty":
        path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        inspect_geojson(path)


def test_geojson_inspection_rejects_blank_schema_labels(tmp_path):
    source = _write_geojson(tmp_path / "n.geojson", [_feature("A")])

    with pytest.raises(ValueError, match="schema_label"):
        inspect_geojson(source, schema_label="   ")


def test_geojson_rerun_and_parser_agree_on_rows_and_counts(tmp_path):
    # F07.3-T02: repeating the same geometry source must be idempotent
    # at every step - the parser yields identical rows, the inspector
    # reports identical counts and fingerprint - so a rerun (or a
    # force-reload replacement of the same snapshot) can never drift
    # from the first attempt.
    source = _write_geojson(
        tmp_path / "n.geojson", [_feature("A"), _feature("B"), _feature("C")]
    )

    first_rows = parse_geojson_features(source)
    second_rows = parse_geojson_features(source)
    first = inspect_geojson(source, schema_label="neighbourhood-geojson")
    second = inspect_geojson(source, schema_label="neighbourhood-geojson")

    assert first_rows == second_rows
    assert first["feature_count"] == second["feature_count"] == len(first_rows)
    assert first["schema_fingerprint"] == second["schema_fingerprint"]
    assert (
        first["columns"]
        == second["columns"]
        == [
            "neighbourhood",
            "neighbourhood_group",
        ]
    )
    # Every parsed row keeps its geometry verbatim: the same number of
    # geometry objects flows into Bronze on every rerun.
    assert all(row["geometry_json"] is not None for row in first_rows)
