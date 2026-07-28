"""Load smallcase definitions and constituents from curated Parquet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from smallcase_finance.data_access.duck import read_parquet_sql, table_exists
from smallcase_finance.data_access.exceptions import (
    CuratedDataUnavailable,
    SmallcaseNotFound,
)
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


def _require_table(name: str):
    path = parquet(name)
    if not table_exists(path):
        raise CuratedDataUnavailable(
            f"Curated table '{name}' is missing; run the data pipeline first"
        )
    return path


def list_smallcases(
    *,
    tag: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return all smallcase definition rows (optionally filtered)."""
    path = _require_table("smallcases")
    clauses: list[str] = []
    params: list[Any] = []
    if tag:
        clauses.append("lower(coalesce(theme, '')) LIKE lower(?)")
        params.append(f"%{tag}%")
    if q:
        clauses.append(
            "(lower(name) LIKE lower(?) OR lower(smallcase_id) LIKE lower(?) "
            "OR lower(coalesce(description, '')) LIKE lower(?))"
        )
        like = f"%{q}%"
        params.extend([like, like, like])
    where = " AND ".join(clauses) if clauses else ""
    rows = read_parquet_sql(
        path,
        where=where,
        order_by="smallcase_id",
        params=params or None,
    )
    for r in rows:
        r["inception_date"] = _coerce_date(r.get("inception_date"))
    return rows


def get_smallcase(smallcase_id: str) -> dict[str, Any]:
    """Return one smallcase row or raise SmallcaseNotFound / CuratedDataUnavailable."""
    path = _require_table("smallcases")
    sid = smallcase_id.strip().lower()
    rows = read_parquet_sql(
        path,
        where="smallcase_id = ?",
        params=[sid],
    )
    if not rows:
        # Distinguish missing table (already raised) vs unknown id
        raise SmallcaseNotFound(sid)
    row = rows[0]
    row["inception_date"] = _coerce_date(row.get("inception_date"))
    return row


def get_constituents(
    smallcase_id: str,
    *,
    as_of: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Active constituent version as of ``as_of`` (default: latest effective_from).

    Resolution: ``effective_from <= as_of`` and
    (``effective_to`` is null or ``effective_to >= as_of``).
    If multiple versions match, keep the latest ``effective_from`` set.
    """
    path = _require_table("smallcase_constituents")
    sid = smallcase_id.strip().lower()
    rows = read_parquet_sql(
        path,
        where="smallcase_id = ?",
        order_by="effective_from, symbol",
        params=[sid],
    )
    if not rows:
        return []

    for r in rows:
        r["effective_from"] = _coerce_date(r.get("effective_from"))
        r["effective_to"] = _coerce_date(r.get("effective_to"))

    if as_of is None:
        # Use max effective_from as the "latest" version anchor
        latest_from = max(r["effective_from"] for r in rows if r["effective_from"])
        as_of = latest_from

    active = [
        r
        for r in rows
        if r["effective_from"] is not None
        and r["effective_from"] <= as_of
        and (r["effective_to"] is None or r["effective_to"] >= as_of)
    ]
    if not active:
        # Fallback: most recent version with effective_from <= as_of
        past = [r for r in rows if r["effective_from"] and r["effective_from"] <= as_of]
        if not past:
            return []
        latest_from = max(r["effective_from"] for r in past)
        active = [r for r in past if r["effective_from"] == latest_from]
    else:
        latest_from = max(r["effective_from"] for r in active)
        active = [r for r in active if r["effective_from"] == latest_from]

    return active


def constituent_count(smallcase_id: str, *, as_of: Optional[date] = None) -> int:
    return len(get_constituents(smallcase_id, as_of=as_of))


def get_instruments(symbols: Optional[list[str]] = None) -> dict[str, dict[str, Any]]:
    """Map symbol → instrument row. Empty dict if instruments table missing."""
    path = parquet("instruments")
    if not table_exists(path):
        return {}
    if symbols:
        # Build IN list carefully
        placeholders = ", ".join(["?"] * len(symbols))
        rows = read_parquet_sql(
            path,
            where=f"symbol IN ({placeholders})",
            params=[s.strip().upper() for s in symbols],
        )
    else:
        rows = read_parquet_sql(path)
    return {r["symbol"]: r for r in rows}


def latest_nav_as_of(smallcase_id: str) -> Optional[date]:
    """Latest date in nav_series for the smallcase, if table exists."""
    path = parquet("nav_series")
    if not table_exists(path):
        return None
    sid = smallcase_id.strip().lower()
    rows = read_parquet_sql(
        path,
        columns="max(date) AS max_date",
        where="smallcase_id = ?",
        params=[sid],
    )
    if not rows or rows[0].get("max_date") is None:
        return None
    return _coerce_date(rows[0]["max_date"])
