"""DuckDB connection helpers for read_parquet queries."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import duckdb


def connect() -> duckdb.DuckDBPyConnection:
    """In-process DuckDB (no server). Caller should close or use ``session``."""
    return duckdb.connect(database=":memory:")


@contextmanager
def session() -> Iterator[duckdb.DuckDBPyConnection]:
    con = connect()
    try:
        yield con
    finally:
        con.close()


def read_parquet_sql(
    path: Path,
    *,
    where: str = "",
    order_by: str = "",
    params: Optional[list[Any]] = None,
    columns: str = "*",
) -> list[dict[str, Any]]:
    """Run ``SELECT … FROM read_parquet(path)`` and return list of row dicts.

    Raises FileNotFoundError if the parquet file is missing.
    Returns [] for zero-row tables.
    """
    if not path.is_file():
        raise FileNotFoundError(str(path))

    # DuckDB needs a path string; escape single quotes for SQL literal
    path_lit = str(path.resolve()).replace("'", "''")
    sql = f"SELECT {columns} FROM read_parquet('{path_lit}')"
    if where:
        sql += f" WHERE {where}"
    if order_by:
        sql += f" ORDER BY {order_by}"

    with session() as con:
        if params:
            rel = con.execute(sql, params)
        else:
            rel = con.execute(sql)
        cols = [d[0] for d in rel.description]
        rows = rel.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def table_exists(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= 0
