"""Read/write founder equity portfolio snapshots (Kite).

Curated path: ``portfolio/holdings_snapshot.parquet`` under DATA_CURATED_ROOT.
Personal dumps should stay gitignored.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
from uuid import uuid4

import polars as pl

from smallcase_finance.config import DATA_CURATED_ROOT, PORTFOLIO_CURATED_DIR
from smallcase_finance.data_access.paths import raw_root
from smallcase_finance.pipeline.io import atomic_write_parquet

logger = logging.getLogger(__name__)

SNAPSHOT_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.Utf8,
    "synced_at": pl.Datetime("us", "UTC"),
    "source": pl.Utf8,
    "symbol": pl.Utf8,
    "exchange": pl.Utf8,
    "quantity": pl.Float64,
    "average_price": pl.Float64,
    "last_price": pl.Float64,
    "pnl": pl.Float64,
    "product": pl.Utf8,
    "isin": pl.Utf8,
    "instrument_token": pl.Int64,
    "value": pl.Float64,
    "weight": pl.Float64,
}


def portfolio_parquet_path(curated_root: Path | None = None) -> Path:
    if curated_root is not None:
        return Path(curated_root) / "portfolio" / "holdings_snapshot.parquet"
    # Prefer PORTFOLIO_CURATED_DIR/holdings_snapshot if it points at a dir
    p = PORTFOLIO_CURATED_DIR
    if p.suffix == ".parquet":
        return p
    return p / "holdings_snapshot.parquet"


def write_raw_kite_drop(
    payload: Any,
    *,
    raw_base: Path | None = None,
) -> Path:
    """Write immutable raw JSON drop under data/raw/holdings/kite/<ts>/."""
    base = Path(raw_base) if raw_base is not None else raw_root() / "holdings" / "kite"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = base / ts
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "holdings.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("wrote raw kite holdings %s", path)
    return path


def holdings_to_rows(
    holdings: Sequence[Any],
    *,
    snapshot_id: str | None = None,
    synced_at: datetime | None = None,
    source: str = "kite",
) -> list[dict[str, Any]]:
    """Normalize KiteHolding-like objects into parquet rows with value/weight."""
    sid = snapshot_id or f"kite_{uuid4().hex[:12]}"
    when = synced_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)

    interim: list[dict[str, Any]] = []
    for h in holdings:
        if hasattr(h, "tradingsymbol"):
            symbol = str(h.tradingsymbol).strip().upper()
            exchange = str(getattr(h, "exchange", "") or "")
            qty = float(getattr(h, "quantity", 0) or 0)
            avg = getattr(h, "average_price", None)
            last = getattr(h, "last_price", None)
            pnl = getattr(h, "pnl", None)
            product = getattr(h, "product", None)
            isin = getattr(h, "isin", None)
            token = getattr(h, "instrument_token", None)
        elif isinstance(h, dict):
            symbol = str(h.get("tradingsymbol") or h.get("symbol") or "").strip().upper()
            exchange = str(h.get("exchange") or "")
            qty = float(h.get("quantity") or 0)
            avg = h.get("average_price")
            last = h.get("last_price")
            pnl = h.get("pnl")
            product = h.get("product")
            isin = h.get("isin")
            token = h.get("instrument_token")
        else:
            continue
        if not symbol or qty == 0:
            continue
        last_f = float(last) if last is not None else None
        value = (qty * last_f) if last_f is not None else None
        interim.append(
            {
                "snapshot_id": sid,
                "synced_at": when,
                "source": source,
                "symbol": symbol,
                "exchange": exchange,
                "quantity": qty,
                "average_price": float(avg) if avg is not None else None,
                "last_price": last_f,
                "pnl": float(pnl) if pnl is not None else None,
                "product": str(product) if product is not None else None,
                "isin": str(isin) if isin is not None else None,
                "instrument_token": int(token) if token is not None else None,
                "value": value,
                "weight": None,
            }
        )

    total = sum(r["value"] or 0.0 for r in interim)
    if total > 0:
        for r in interim:
            if r["value"] is not None:
                r["weight"] = float(r["value"]) / total
    return interim


def write_snapshot_rows(
    rows: Sequence[dict[str, Any]],
    *,
    curated_root: Path | None = None,
) -> Path:
    """Replace curated portfolio snapshot with these rows."""
    path = portfolio_parquet_path(curated_root)
    if not rows:
        df = pl.DataFrame(schema=SNAPSHOT_SCHEMA)
    else:
        df = pl.DataFrame(rows)
        # Ensure schema-friendly dtypes
        for col, dtype in SNAPSHOT_SCHEMA.items():
            if col not in df.columns:
                df = df.with_columns(pl.lit(None).cast(dtype).alias(col))
        df = df.select(list(SNAPSHOT_SCHEMA.keys()))
    return atomic_write_parquet(df, path, sort_by=["symbol", "exchange", "product"])


def read_latest_snapshot(
    *,
    curated_root: Path | None = None,
) -> Optional[dict[str, Any]]:
    """Return {snapshot_id, synced_at, source, rows: list[dict]} or None."""
    path = portfolio_parquet_path(curated_root)
    if not path.is_file():
        return None
    try:
        df = pl.read_parquet(path)
    except Exception as exc:
        logger.warning("failed to read portfolio snapshot %s: %s", path, exc)
        return None
    if df.is_empty():
        return None

    # Prefer max synced_at group
    if "synced_at" in df.columns:
        max_ts = df.select(pl.col("synced_at").max()).item()
        if max_ts is not None:
            df = df.filter(pl.col("synced_at") == max_ts)

    rows = df.to_dicts()
    if not rows:
        return None
    first = rows[0]
    synced = first.get("synced_at")
    if isinstance(synced, datetime) and synced.tzinfo is None:
        synced = synced.replace(tzinfo=timezone.utc)
    return {
        "snapshot_id": str(first.get("snapshot_id") or "unknown"),
        "synced_at": synced,
        "source": str(first.get("source") or "kite"),
        "rows": rows,
    }


def sector_lookup(symbols: Sequence[str]) -> dict[str, Optional[str]]:
    """Best-effort sector from instruments parquet."""
    path = Path(DATA_CURATED_ROOT) / "instruments" / "instruments.parquet"
    out: dict[str, Optional[str]] = {s.upper(): None for s in symbols}
    if not path.is_file() or not symbols:
        return out
    try:
        df = pl.read_parquet(path)
        if "symbol" not in df.columns:
            return out
        want = {s.upper() for s in symbols}
        df = df.filter(pl.col("symbol").str.to_uppercase().is_in(list(want)))
        sector_col = "sector" if "sector" in df.columns else None
        if not sector_col:
            return out
        for row in df.select(["symbol", sector_col]).to_dicts():
            sym = str(row["symbol"]).upper()
            sec = row.get(sector_col)
            out[sym] = str(sec) if sec is not None else None
    except Exception as exc:
        logger.debug("sector lookup failed: %s", exc)
    return out
