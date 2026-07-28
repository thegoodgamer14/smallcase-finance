"""Load precomputed NAV / metrics from curated Parquet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from smallcase_finance.data_access.duck import read_parquet_sql, table_exists
from smallcase_finance.data_access.exceptions import CuratedDataUnavailable
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


def get_nav_series(
    smallcase_id: str,
    *,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Return curated nav_series rows (may be empty if file missing or no rows)."""
    path = parquet("nav_series")
    if not table_exists(path):
        return []

    sid = smallcase_id.strip().lower()
    clauses = ["smallcase_id = ?"]
    params: list[Any] = [sid]
    if start is not None:
        clauses.append("date >= ?")
        params.append(start)
    if end is not None:
        clauses.append("date <= ?")
        params.append(end)

    rows = read_parquet_sql(
        path,
        where=" AND ".join(clauses),
        order_by="date",
        params=params,
    )
    for r in rows:
        r["date"] = _coerce_date(r.get("date"))
        # First day may legitimately have daily_return = 0.0 in sample data;
        # leave as-is for performance series (API may map 0 on first row to null later).
    return rows


def get_latest_nav(smallcase_id: str) -> Optional[dict[str, Any]]:
    series = get_nav_series(smallcase_id)
    if not series:
        return None
    return series[-1]


def get_metrics_snapshot(
    smallcase_id: str,
    *,
    window: str = "ITD",
    as_of: Optional[date] = None,
) -> Optional[dict[str, Any]]:
    """Return one metrics_snapshot row for window (latest as_of if not specified)."""
    path = parquet("metrics_snapshot")
    if not table_exists(path):
        return None

    sid = smallcase_id.strip().lower()
    # "window" is a SQL reserved word — always quote the column identifier
    clauses = ["smallcase_id = ?", '"window" = ?']
    params: list[Any] = [sid, window]
    if as_of is not None:
        clauses.append("as_of = ?")
        params.append(as_of)

    rows = read_parquet_sql(
        path,
        where=" AND ".join(clauses),
        order_by="as_of DESC",
        params=params,
    )
    if not rows:
        return None
    row = rows[0]
    for key in ("as_of", "start_date", "end_date"):
        if key in row:
            row[key] = _coerce_date(row[key])
    return row


def get_contribution(
    smallcase_id: str,
    *,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Return contribution rows for a smallcase.

    If period bounds are omitted, returns the longest available period
    (max calendar span of period_end - period_start).
    """
    path = parquet("contribution")
    if not table_exists(path):
        return []

    sid = smallcase_id.strip().lower()
    clauses = ["smallcase_id = ?"]
    params: list[Any] = [sid]
    if period_start is not None:
        clauses.append("period_start = ?")
        params.append(period_start)
    if period_end is not None:
        clauses.append("period_end = ?")
        params.append(period_end)

    rows = read_parquet_sql(
        path,
        where=" AND ".join(clauses),
        order_by="contribution DESC",
        params=params,
    )
    for r in rows:
        r["period_start"] = _coerce_date(r.get("period_start"))
        r["period_end"] = _coerce_date(r.get("period_end"))

    # Explicit period filter → return as-is (possibly empty)
    if period_start is not None or period_end is not None:
        return rows

    if not rows:
        return []

    # No filter: pick the widest (period_start, period_end) span
    periods: dict[tuple[date, date], list[dict[str, Any]]] = {}
    for r in rows:
        ps, pe = r["period_start"], r["period_end"]
        if ps is None or pe is None:
            continue
        periods.setdefault((ps, pe), []).append(r)
    if not periods:
        return rows

    best = max(periods.keys(), key=lambda k: (k[1] - k[0]).days)
    chosen = periods[best]
    chosen.sort(key=lambda r: float(r.get("contribution") or 0.0), reverse=True)
    return chosen
