import re
from datetime import date


def write_snapshot(df, table, city, snapshot_date, city_col, snapshot_col):
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
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", predicate)
        .saveAsTable(table)
    )
