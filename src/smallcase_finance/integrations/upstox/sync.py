"""Sync historical prices from Upstox into data/raw/prices/{date}_upstox/.

Lookback options (mutually composed):
- ``years``: rolling window ending at ``to_date`` (default today)
- ``from_date`` / ``to_date``: custom inclusive timeline
- defaults: ``UPSTOX_DEFAULT_YEARS`` years ending today

Missing symbols are skipped with warnings; remaining symbols are written.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

import polars as pl

from smallcase_finance.config import UPSTOX_DEFAULT_YEARS
from smallcase_finance.data_access.paths import iter_raw_smallcase_definitions, raw_root
from smallcase_finance.integrations.upstox.client import (
    CandleBar,
    UpstoxClient,
    UpstoxError,
)
from smallcase_finance.integrations.upstox.instruments import (
    instrument_key_map,
    resolve_instrument_key,
)
from smallcase_finance.schemas.models import SmallcaseDefinitionFile

logger = logging.getLogger(__name__)

PRICE_COLUMNS = [
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_close",
    "currency",
    "source",
]


@dataclass
class SyncResult:
    """Outcome of a sync attempt (for CLI / API reporting)."""

    from_date: date
    to_date: date
    requested_symbols: list[str] = field(default_factory=list)
    fetched_symbols: list[str] = field(default_factory=list)
    skipped_symbols: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    output_path: Path | None = None
    used_sample_fallback: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "from_date": self.from_date.isoformat(),
            "to_date": self.to_date.isoformat(),
            "requested_symbols": self.requested_symbols,
            "fetched_symbols": self.fetched_symbols,
            "skipped_symbols": self.skipped_symbols,
            "warnings": self.warnings,
            "row_count": self.row_count,
            "output_path": str(self.output_path) if self.output_path else None,
            "used_sample_fallback": self.used_sample_fallback,
            "message": self.message,
        }


def resolve_lookback(
    *,
    years: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve a custom inclusive [from, to] range.

    Priority:
    1. Explicit from_date and/or to_date (missing side filled from years/default)
    2. years (or UPSTOX_DEFAULT_YEARS) ending at to_date or today
    """
    end = to_date or today or date.today()
    if from_date is not None:
        start = from_date
    else:
        y = years if years is not None else UPSTOX_DEFAULT_YEARS
        if y < 1:
            raise ValueError("years must be >= 1")
        # Approximate calendar years; good enough for lookback UX
        start = end - timedelta(days=int(365.25 * y))
    if start > end:
        raise ValueError(f"from_date {start} must be <= to_date {end}")
    return start, end


def symbols_from_smallcase_defs(paths: Sequence[Path] | None = None) -> list[str]:
    """Union of constituent symbols across all raw smallcase JSON files."""
    files = list(paths) if paths is not None else iter_raw_smallcase_definitions()
    symbols: set[str] = set()
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            defn = SmallcaseDefinitionFile.model_validate(data)
        except Exception as exc:
            logger.warning("skip invalid smallcase def %s: %s", path, exc)
            continue
        for version in defn.versions:
            for c in version.constituents:
                symbols.add(c.symbol.strip().upper())
    return sorted(symbols)


def symbols_from_strategy_configs() -> list[str]:
    """Union of symbols from file-backed SIP strategies under config/strategies/."""
    try:
        from smallcase_finance.config import STRATEGIES_DIR
        from smallcase_finance.strategies.loader import load_strategy_config
        from smallcase_finance.strategies.models import InlineBasket
    except Exception as exc:
        logger.warning("strategy symbol discovery unavailable: %s", exc)
        return []

    symbols: set[str] = set()
    root = STRATEGIES_DIR
    if not root.is_dir():
        return []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        try:
            cfg = load_strategy_config(path)
        except Exception as exc:
            logger.warning("skip strategy file %s: %s", path.name, exc)
            continue
        if isinstance(cfg.basket, InlineBasket):
            for c in cfg.basket.constituents:
                symbols.add(str(c.symbol).strip().upper())
        # smallcase_ref baskets: covered by symbols_from_smallcase_defs
    return sorted(symbols)


def default_sync_symbols() -> list[str]:
    """Union of smallcase + strategy symbols for a full personal sync."""
    return sorted(set(symbols_from_smallcase_defs()) | set(symbols_from_strategy_configs()))


def candles_to_frame(bars: Iterable[CandleBar], *, source: str = "upstox") -> pl.DataFrame:
    rows = [
        {
            "symbol": b.symbol,
            "date": b.bar_date,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "adj_close": None,
            "currency": "INR",
            "source": source,
        }
        for b in bars
    ]
    if not rows:
        return pl.DataFrame(
            schema={
                "symbol": pl.Utf8,
                "date": pl.Date,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Float64,
                "adj_close": pl.Float64,
                "currency": pl.Utf8,
                "source": pl.Utf8,
            }
        )
    df = pl.DataFrame(rows)
    return df.select(PRICE_COLUMNS).sort(["symbol", "date"])


def write_price_drop(
    df: pl.DataFrame,
    *,
    raw: Path | None = None,
    drop_date: date | None = None,
    source: str = "upstox",
) -> Path:
    """Write parquet under data/raw/prices/{yyyy-mm-dd}_{source}/prices.parquet."""
    root = raw or raw_root()
    d = drop_date or date.today()
    folder = root / "prices" / f"{d.isoformat()}_{source}"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "prices.parquet"
    df.write_parquet(out)
    # Small manifest for humans
    manifest = {
        "source": source,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "rows": df.height,
        "symbols": sorted(df["symbol"].unique().to_list()) if df.height else [],
        "date_min": str(df["date"].min()) if df.height else None,
        "date_max": str(df["date"].max()) if df.height else None,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


def sync_prices(
    *,
    symbols: Sequence[str] | None = None,
    years: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    client: UpstoxClient | None = None,
    run_pipeline_after: bool = False,
    allow_sample_fallback: bool = True,
) -> SyncResult:
    """Fetch daily prices for symbols and write a raw price drop.

    If credentials are missing and ``allow_sample_fallback`` is True, ensure sample
    raw data exists and return a result noting fallback (no Upstox call).
    """
    start, end = resolve_lookback(years=years, from_date=from_date, to_date=to_date)
    requested = (
        sorted({s.strip().upper() for s in symbols if s and s.strip()})
        if symbols
        else default_sync_symbols()
    )
    result = SyncResult(from_date=start, to_date=end, requested_symbols=requested)

    if not requested:
        result.warnings.append("No symbols to sync (no smallcase defs and none passed).")
        result.message = "Nothing to sync."
        return result

    owns_client = client is None
    client = client or UpstoxClient()

    if not client.configured:
        msg = (
            "Upstox access token not set (UPSTOX_ACCESS_TOKEN). "
            "Using sample price data path instead (demo only)."
        )
        logger.warning(msg)
        result.warnings.append(msg)
        result.used_sample_fallback = True
        if allow_sample_fallback:
            from smallcase_finance.pipeline.generate_sample import generate_sample_raw

            generate_sample_raw(force=False)
            result.message = (
                "Sample data ready. Set UPSTOX_ACCESS_TOKEN and re-run sync for live prices. "
                "Then: python -m smallcase_finance.pipeline"
            )
        else:
            result.message = "Credentials missing; sample fallback disabled."
        return result

    mapping = instrument_key_map()
    all_bars: list[CandleBar] = []

    try:
        if owns_client:
            client.__enter__()

        for sym in requested:
            key = resolve_instrument_key(sym, mapping)
            if not key:
                w = f"No Upstox instrument_key for {sym}; skipped. Add to upstox_instrument_map.json."
                logger.warning(w)
                result.warnings.append(w)
                result.skipped_symbols.append(sym)
                continue
            try:
                bars = client.fetch_daily_candles(
                    instrument_key=key,
                    symbol=sym,
                    from_date=start,
                    to_date=end,
                )
            except (UpstoxError, ValueError) as exc:
                w = f"{sym}: {exc}"
                logger.warning(w)
                result.warnings.append(w)
                result.skipped_symbols.append(sym)
                continue
            if not bars:
                w = f"{sym}: empty candle series"
                logger.warning(w)
                result.warnings.append(w)
                result.skipped_symbols.append(sym)
                continue
            all_bars.extend(bars)
            result.fetched_symbols.append(sym)
            logger.info("%s: %d bars %s→%s", sym, len(bars), bars[0].bar_date, bars[-1].bar_date)
    finally:
        if owns_client:
            client.__exit__(None, None, None)

    if not all_bars:
        result.message = "No bars fetched; check instrument map and token permissions."
        return result

    df = candles_to_frame(all_bars, source="upstox")
    out = write_price_drop(df, drop_date=date.today(), source="upstox")
    result.output_path = out
    result.row_count = df.height
    result.message = f"Wrote {df.height} rows for {len(result.fetched_symbols)} symbols → {out}"

    if run_pipeline_after:
        from smallcase_finance.pipeline.run import run_pipeline

        logger.info("running pipeline after Upstox sync…")
        run_pipeline(skip_sample=True)
        result.message += " Pipeline completed."

    return result
