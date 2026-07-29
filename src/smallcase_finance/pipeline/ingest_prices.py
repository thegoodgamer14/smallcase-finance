"""Ingest price bulk drops from data/raw/prices/."""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from smallcase_finance.data_access.paths import raw_root
from smallcase_finance.schemas.models import PriceBar

logger = logging.getLogger(__name__)

PRICE_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "date": pl.Date,
    "close": pl.Float64,
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "volume": pl.Float64,
    "adj_close": pl.Float64,
    "currency": pl.Utf8,
    "source": pl.Utf8,
}

# Common vendor column aliases → dictionary names
_COLUMN_ALIASES: dict[str, str] = {
    "ticker": "symbol",
    "Symbol": "symbol",
    "Date": "date",
    "Close": "close",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Volume": "volume",
    "Adj Close": "adj_close",
    "adjclose": "adj_close",
    "AdjClose": "adj_close",
}


def discover_price_files(root: Path | None = None) -> list[Path]:
    folder = (root or raw_root()) / "prices"
    if not folder.is_dir():
        return []
    files: list[Path] = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        if p.name.upper().startswith("README"):
            continue
        if p.suffix.lower() in {".parquet", ".csv"}:
            files.append(p)
    return files


def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    rename = {c: _COLUMN_ALIASES[c] for c in df.columns if c in _COLUMN_ALIASES}
    if rename:
        df = df.rename(rename)
    # strip exchange suffix e.g. INFY.NS → INFY
    if "symbol" in df.columns:
        df = df.with_columns(
            pl.col("symbol")
            .cast(pl.Utf8)
            .str.to_uppercase()
            .str.replace(r"\.(NS|BO|NSE|BSE)$", "")
            .str.strip_chars()
            .alias("symbol")
        )
    if "date" in df.columns:
        if df["date"].dtype == pl.Utf8:
            df = df.with_columns(pl.col("date").str.to_date(strict=False))
        elif df["date"].dtype in (pl.Datetime, pl.Datetime("us"), pl.Datetime("ms")):
            df = df.with_columns(pl.col("date").cast(pl.Date))
        else:
            df = df.with_columns(pl.col("date").cast(pl.Date, strict=False))
    return df


def _read_price_file(path: Path) -> pl.DataFrame:
    if path.suffix.lower() == ".parquet":
        df = pl.read_parquet(path)
    else:
        df = pl.read_csv(path, try_parse_dates=True)
    df = _normalize_columns(df)
    # infer source from parent folder name if missing
    if "source" not in df.columns:
        parent = path.parent.name  # e.g. 2026-07-28_sample
        source = parent.split("_", 1)[-1] if "_" in parent else parent
        df = df.with_columns(pl.lit(source).alias("source"))
    if "currency" not in df.columns:
        df = df.with_columns(pl.lit("INR").alias("currency"))
    return df


def load_raw_prices(root: Path | None = None) -> pl.DataFrame:
    """Load all price drops, validate, dedupe PK (symbol, date) last-wins."""
    files = discover_price_files(root)
    if not files:
        logger.warning("no price files under raw/prices/")
        return pl.DataFrame(schema=PRICE_SCHEMA)

    frames: list[pl.DataFrame] = []
    for f in files:
        try:
            frames.append(_read_price_file(f))
        except Exception as e:
            logger.error("failed to read %s: %s", f, e)
            raise

    df = pl.concat(frames, how="diagonal_relaxed")

    required = {"symbol", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"price files missing required columns: {missing}")

    # ensure optional cols exist
    for col, dtype in PRICE_SCHEMA.items():
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))

    df = df.select(list(PRICE_SCHEMA.keys()))
    df = df.drop_nulls(subset=["symbol", "date", "close"])
    df = df.filter(pl.col("close") > 0)
    # Prefer live Upstox over sample/demo when both cover the same (symbol, date).
    # Rank: upstox=2, other=1, sample/demo/synthetic=0 → keep last after sort.
    src = pl.col("source").cast(pl.Utf8).fill_null("").str.to_lowercase()
    rank = (
        pl.when(src.str.contains("upstox"))
        .then(pl.lit(2))
        .when(
            src.str.contains("sample")
            | src.str.contains("demo")
            | src.str.contains("synthetic")
        )
        .then(pl.lit(0))
        .otherwise(pl.lit(1))
        .alias("_src_rank")
    )
    df = (
        df.with_columns(rank)
        .sort(["symbol", "date", "_src_rank"])
        .unique(subset=["symbol", "date"], keep="last")
        .drop("_src_rank")
        .sort(["symbol", "date"])
    )

    # light pydantic sample validation (first/last few rows)
    sample = df.head(5).to_dicts() + df.tail(5).to_dicts()
    for row in sample:
        PriceBar.model_validate(row)

    logger.info(
        "prices loaded: %d rows, %d symbols, from %d files",
        df.height,
        df["symbol"].n_unique(),
        len(files),
    )
    return df
