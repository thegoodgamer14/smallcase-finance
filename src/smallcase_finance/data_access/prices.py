"""Load price history from curated Parquet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from smallcase_finance.data_access.duck import read_parquet_sql, table_exists
from smallcase_finance.data_access.paths import parquet


def _coerce_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v


def get_prices(
    symbols: list[str],
    *,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Return price rows for symbols in date range. Empty if table missing."""
    path = parquet("prices")
    if not table_exists(path) or not symbols:
        return []

    upper = [s.strip().upper() for s in symbols]
    placeholders = ", ".join(["?"] * len(upper))
    clauses = [f"symbol IN ({placeholders})"]
    params: list[Any] = list(upper)
    if start is not None:
        clauses.append("date >= ?")
        params.append(start)
    if end is not None:
        clauses.append("date <= ?")
        params.append(end)

    rows = read_parquet_sql(
        path,
        where=" AND ".join(clauses),
        order_by="symbol, date",
        params=params,
    )
    for r in rows:
        r["date"] = _coerce_date(r.get("date"))
    return rows
