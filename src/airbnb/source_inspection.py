"""Inspect the header of a gzip-compressed Airbnb source CSV (F05.1).

The exact observed header — ordered column names, column count,
duplicate/missing names and a content-addressed fingerprint — is
registration evidence: the manifest's schema_version must describe the
file actually being registered, never a schema assumed from another
city or snapshot.
"""

import csv
import gzip
import hashlib
from collections import Counter
from pathlib import Path

GZIP_MAGIC_BYTES = b"\x1f\x8b"


def read_csv_gz_header_line(path) -> str:
    """Return the first decompressed line of the gzip CSV at path.

    Raises a clear ValueError when the file is missing, not a regular
    file, empty, not gzip-compressed, or contains no header line.
    """
    file = Path(path)
    if not file.exists():
        raise ValueError(f"{file}: source file not found")
    if not file.is_file():
        raise ValueError(f"{file}: source is not a regular file")
    if file.stat().st_size == 0:
        raise ValueError(f"{file}: source file is empty")
    with file.open("rb") as probe:
        if probe.read(2) != GZIP_MAGIC_BYTES:
            raise ValueError(f"{file}: file signature is not gzip")
    with gzip.open(file, "rt", encoding="utf-8", newline="") as stream:
        line = stream.readline()
    if not line.strip():
        raise ValueError(f"{file}: gzip stream contains no header line")
    return line.rstrip("\r\n")


def verify_gzip_integrity(path) -> int:
    """Fully decompress the gzip file; return the decompressed byte count.

    A gzip file can carry a valid magic signature and hash yet be
    truncated or corrupted mid-stream. Reading only the header line
    proves nothing about the body, so Bronze requires the whole stream
    to decompress cleanly BEFORE Spark parses it. Raises a clear
    ValueError when the stream cannot be read end-to-end or decompresses
    to nothing.
    """
    file = Path(path)
    if not file.exists():
        raise ValueError(f"{file}: source file not found")
    if not file.is_file():
        raise ValueError(f"{file}: source is not a regular file")
    if file.stat().st_size == 0:
        raise ValueError(f"{file}: source file is empty")
    decompressed = 0
    try:
        with gzip.open(file, "rb") as stream:
            while chunk := stream.read(1 << 20):
                decompressed += len(chunk)
    except (OSError, EOFError) as error:
        raise ValueError(
            f"{file}: gzip stream is not readable end-to-end ({error})"
        ) from error
    if decompressed == 0:
        raise ValueError(f"{file}: gzip stream decompresses to nothing")
    return decompressed


def check_required_columns(
    columns: list[str],
    required_columns: list[str],
) -> list[str]:
    """Return the required columns missing from the observed header.

    An empty result means the observed header satisfies the Bronze
    source contract. Missing REQUIRED columns are a hard failure before
    any write; additional unexpected columns are reported by the caller
    as schema drift for review, not silently ignored.
    """
    observed = set(columns)
    return [column for column in required_columns if column not in observed]


def inspect_csv_gz_header(path, schema_label: str = "detailed-listings") -> dict:
    """Inspect the gzip CSV header at path; return registration evidence.

    schema_label names the source dataset in the derived schema_version
    ("detailed-listings" for the listings file; F06.1 passes "calendar"
    and "detailed-reviews" for the calendar and review files), so a
    manifest never describes a calendar or review file as a listings
    schema.

    Returns a mapping with:
    - header_line: the observed first line without the trailing newline
    - columns: the ordered column names (CSV-quoting aware)
    - column_count: number of columns
    - duplicate_columns: names appearing more than once (empty when none)
    - missing_columns: positions of empty/blank names (empty when none)
    - schema_fingerprint: "sha256:<64 hex>" over the exact header line
    - schema_version: manifest schema_version derived from the fingerprint
    - byte_size: compressed file size in bytes
    """
    if not isinstance(schema_label, str) or not schema_label.strip():
        raise ValueError("schema_label must be a non-empty string")
    header_line = read_csv_gz_header_line(path)
    columns = next(csv.reader([header_line]))
    counts = Counter(columns)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    missing = [index for index, name in enumerate(columns) if not name.strip()]
    fingerprint = hashlib.sha256(header_line.encode("utf-8")).hexdigest()
    return {
        "header_line": header_line,
        "columns": columns,
        "column_count": len(columns),
        "duplicate_columns": duplicates,
        "missing_columns": missing,
        "schema_fingerprint": f"sha256:{fingerprint}",
        "schema_version": f"{schema_label}-sha256:{fingerprint[:16]}",
        "byte_size": Path(path).stat().st_size,
    }
