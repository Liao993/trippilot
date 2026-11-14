"""Tests for the Airbnb source-header inspection helper (F05.1-T01).

These tests prove the helper reads the exact observed header — ordered
columns, duplicates, missing names, content-addressed fingerprint —
from a real gzip file, so the manifest's schema_version describes the
registered bytes instead of an assumed schema.
"""

import gzip

import pytest

from src.airbnb.source_inspection import (
    check_required_columns,
    inspect_csv_gz_header,
    read_csv_gz_header_line,
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
