"""Ingest instrument masters from data/raw/instruments/."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from smallcase_finance.data_access.paths import raw_root
from smallcase_finance.schemas.models import Instrument

logger = logging.getLogger(__name__)

INSTRUMENT_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "name": pl.Utf8,
    "sector": pl.Utf8,
    "industry": pl.Utf8,
    "exchange": pl.Utf8,
    "currency": pl.Utf8,
    "isin": pl.Utf8,
    "is_active": pl.Boolean,
    "updated_at": pl.Datetime("us", "UTC"),
}


def _load_json_instruments(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "instruments" in data:
        data = data["instruments"]
    if not isinstance(data, list):
        raise ValueError(f"expected list of instruments in {path}")
    return data


def _load_csv_instruments(path: Path) -> list[dict]:
    df = pl.read_csv(path)
    return df.to_dicts()


def discover_instrument_files(root: Path | None = None) -> list[Path]:
    folder = (root or raw_root()) / "instruments"
    if not folder.is_dir():
        return []
    files: list[Path] = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".json", ".csv"}:
            files.append(p)
    return files


def load_raw_instruments(root: Path | None = None) -> pl.DataFrame:
    """Load + validate all instrument drops; last-wins on duplicate symbols."""
    files = discover_instrument_files(root)
    rows: list[dict] = []
    for f in files:
        if f.suffix.lower() == ".json":
            raw = _load_json_instruments(f)
        else:
            raw = _load_csv_instruments(f)
        for item in raw:
            # normalize timestamps for pydantic
            if item.get("updated_at") and isinstance(item["updated_at"], str):
                item["updated_at"] = datetime.fromisoformat(
                    item["updated_at"].replace("Z", "+00:00")
                )
            if "is_active" not in item or item["is_active"] is None:
                item["is_active"] = True
            if not item.get("currency"):
                item["currency"] = "INR"
            inst = Instrument.model_validate(item)
            d = inst.model_dump()
            rows.append(d)

    if not rows:
        logger.warning("no instrument files found under raw/instruments/")
        return pl.DataFrame(schema=INSTRUMENT_SCHEMA)

    # last-wins by symbol (later files override)
    by_sym: dict[str, dict] = {}
    for r in rows:
        by_sym[r["symbol"]] = r
    clean = list(by_sym.values())

    df = pl.DataFrame(clean)
    # ensure dtypes
    if "updated_at" in df.columns and df["updated_at"].dtype != pl.Datetime("us", "UTC"):
        df = df.with_columns(
            pl.col("updated_at").cast(pl.Datetime("us", "UTC"), strict=False)
        )
    for col, dtype in INSTRUMENT_SCHEMA.items():
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))
    df = df.select(list(INSTRUMENT_SCHEMA.keys())).sort("symbol")
    logger.info("instruments loaded: %d unique symbols from %d files", df.height, len(files))
    return df


def instruments_from_prices_and_defs(
    prices: pl.DataFrame,
    constituent_symbols: set[str],
) -> pl.DataFrame:
    """Fallback instrument master inferred from prices + smallcase symbols."""
    now = datetime.now(timezone.utc)
    symbols = set()
    if prices.height and "symbol" in prices.columns:
        symbols |= set(prices["symbol"].unique().to_list())
    symbols |= {s.upper() for s in constituent_symbols}
    rows = [
        {
            "symbol": s,
            "name": s,
            "sector": None,
            "industry": None,
            "exchange": "NSE",
            "currency": "INR",
            "isin": None,
            "is_active": True,
            "updated_at": now,
        }
        for s in sorted(symbols)
    ]
    if not rows:
        return pl.DataFrame(schema=INSTRUMENT_SCHEMA)
    return pl.DataFrame(rows).select(list(INSTRUMENT_SCHEMA.keys())).sort("symbol")
