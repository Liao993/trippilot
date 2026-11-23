"""Inspect Airbnb source files: gzip/plain CSV headers and GeoJSON (F05.1/F07.1).

The exact observed schema — ordered column names, column count,
duplicate/missing names and a content-addressed fingerprint — is
registration evidence: the manifest's schema_version must describe the
file actually being registered, never a schema assumed from another
city or snapshot.

Since F07.1 the same evidence is produced for plain (uncompressed) CSV
files and GeoJSON FeatureCollections: the shared header-facts derivation
is reused for both CSV variants, and the GeoJSON inspection adds the
feature count, property keys and geometry types (F07.2-T03 evidence).
"""

import csv
import gzip
import hashlib
import json
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


def read_csv_header_line(path) -> str:
    """Return the first line of the plain (uncompressed) CSV at path.

    Raises a clear ValueError when the file is missing, not a regular
    file, empty, gzip-compressed despite a plain-csv registration, not
    readable as UTF-8 text, or contains no header line.
    """
    file = Path(path)
    if not file.exists():
        raise ValueError(f"{file}: source file not found")
    if not file.is_file():
        raise ValueError(f"{file}: source is not a regular file")
    if file.stat().st_size == 0:
        raise ValueError(f"{file}: source file is empty")
    with file.open("rb") as probe:
        if probe.read(2) == GZIP_MAGIC_BYTES:
            raise ValueError(
                f"{file}: content is gzip-compressed but was inspected as csv; "
                "use the gzip inspection path instead"
            )
    try:
        with file.open("rt", encoding="utf-8", newline="") as stream:
            line = stream.readline()
    except UnicodeDecodeError as error:
        raise ValueError(f"{file}: not readable as UTF-8 text ({error})") from error
    if not line.strip():
        raise ValueError(f"{file}: csv source contains no header line")
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


def _derive_header_facts(header_line: str, schema_label: str) -> dict:
    """Derive the shared CSV header facts from one observed header line.

    Used by both the gzip and plain-CSV inspections so the two variants
    can never drift apart (F07.1 D4).
    """
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
    }


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
    facts = _derive_header_facts(read_csv_gz_header_line(path), schema_label)
    facts["byte_size"] = Path(path).stat().st_size
    return facts


def inspect_csv_header(path, schema_label: str = "summary-listings") -> dict:
    """Inspect the plain (uncompressed) CSV header at path (F07.1 D4).

    Same facts and schema_version derivation as the gzip variant - the
    fingerprint is over the exact observed header line - for the
    summary listings/reviews and neighbourhoods files.
    """
    if not isinstance(schema_label, str) or not schema_label.strip():
        raise ValueError("schema_label must be a non-empty string")
    facts = _derive_header_facts(read_csv_header_line(path), schema_label)
    facts["byte_size"] = Path(path).stat().st_size
    return facts


def _is_geojson_feature_collection(document: object) -> bool:
    """Whether the parsed document is a FeatureCollection with a features array."""
    return (
        isinstance(document, dict)
        and document.get("type") == "FeatureCollection"
        and isinstance(document.get("features"), list)
    )


def inspect_geojson(path, schema_label: str = "neighbourhood-geojson") -> dict:
    """Inspect a GeoJSON FeatureCollection; return registration evidence (F07.1 D4).

    Validates the structure (type FeatureCollection with a features
    list), counts features, collects the union of property keys and
    geometry types, and derives a content-addressed fingerprint over
    the canonicalized [sorted property keys, sorted geometry types]
    signature - so the manifest schema_version describes the observed
    structure of this exact file.

    Returns a mapping with:
    - geojson_type: the top-level type ("FeatureCollection")
    - feature_count: number of features (F07.2-T03 evidence)
    - columns: sorted distinct property keys across features
    - geometry_types: sorted distinct geometry types across features
    - schema_fingerprint: "sha256:<64 hex>" over the canonical signature
    - schema_version: manifest schema_version derived from the fingerprint
    - byte_size: file size in bytes
    """
    if not isinstance(schema_label, str) or not schema_label.strip():
        raise ValueError("schema_label must be a non-empty string")
    file = Path(path)
    if not file.exists():
        raise ValueError(f"{file}: source file not found")
    if not file.is_file():
        raise ValueError(f"{file}: source is not a regular file")
    if file.stat().st_size == 0:
        raise ValueError(f"{file}: source file is empty")
    try:
        document = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{file}: not readable as JSON ({error})") from error
    if not _is_geojson_feature_collection(document):
        raise ValueError(
            f"{file}: expected a GeoJSON FeatureCollection with a features array"
        )
    features = document["features"]
    property_keys = sorted(
        {
            key
            for feature in features
            if isinstance(feature, dict)
            for key in (feature.get("properties") or {})
        }
    )
    geometry_types = sorted(
        {
            feature["geometry"]["type"]
            for feature in features
            if isinstance(feature, dict)
            and isinstance(feature.get("geometry"), dict)
            and "type" in feature["geometry"]
        }
    )
    signature = json.dumps([property_keys, geometry_types], sort_keys=True)
    fingerprint = hashlib.sha256(signature.encode("utf-8")).hexdigest()
    return {
        "geojson_type": "FeatureCollection",
        "feature_count": len(features),
        "columns": property_keys,
        "geometry_types": geometry_types,
        "schema_fingerprint": f"sha256:{fingerprint}",
        "schema_version": f"{schema_label}-sha256:{fingerprint[:16]}",
        "byte_size": file.stat().st_size,
    }
