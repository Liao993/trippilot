import re
from datetime import date


def write_snapshot(
    df,
    table,
    city,
    snapshot_date,
    city_col,
    snapshot_col,
    *,
    merge_schema=False,
):
    """Atomically replace one city/snapshot slice of a Delta table.

    A single overwrite with replaceWhere replaces the slice in one
    atomic operation - no window where the data is deleted but not yet
    re-written. merge_schema=True additionally allows the incoming
    frame to carry new columns (e.g. manifest-backed provenance added
    in F05.2); the table schema then evolves to include them.
    """
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", city):
        raise ValueError("Unsafe city value")
    date.fromisoformat(snapshot_date)
    if (
        any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in table.split("."))
        or len(table.split(".")) != 3
    ):
        raise ValueError("Expected catalog.schema.table")
    for column in (city_col, snapshot_col):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
            raise ValueError("Unsafe column name")
    predicate = f"{city_col} = '{city}' AND {snapshot_col} = '{snapshot_date}'"
    writer = (
        df.write.format("delta").mode("overwrite").option("replaceWhere", predicate)
    )
    if merge_schema:
        writer = writer.option("mergeSchema", "true")
    writer.saveAsTable(table)
