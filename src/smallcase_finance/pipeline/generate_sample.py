"""Generate realistic sample instruments + daily OHLCV under data/raw/.

Idempotent: skips generation when a sample price drop already exists unless
``force=True``.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import polars as pl

from smallcase_finance.data_access.paths import raw_root

logger = logging.getLogger(__name__)

# ~3y business days: 2023-01-02 → 2025-12-31 (covers smallcase inception)
SAMPLE_START = date(2023, 1, 2)
SAMPLE_END = date(2025, 12, 31)
SAMPLE_SOURCE_TAG = "sample"
SAMPLE_DROP_DATE = "2026-07-28"  # folder stamp for the generated drop

# 12 NSE-like large/mid caps with plausible base prices (INR) and drift/vol
# (daily drift, daily vol) — illustrative only, not calibrated forecasts.
UNIVERSE: list[dict] = [
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "sector": "Energy",
        "industry": "Oil & Gas Refining",
        "base": 2450.0,
        "mu": 0.00035,
        "sigma": 0.015,
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 3200.0,
        "mu": 0.00028,
        "sigma": 0.013,
    },
    {
        "symbol": "INFY",
        "name": "Infosys",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 1450.0,
        "mu": 0.00025,
        "sigma": 0.014,
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank",
        "sector": "Financials",
        "industry": "Private Banks",
        "base": 1600.0,
        "mu": 0.00030,
        "sigma": 0.014,
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank",
        "sector": "Financials",
        "industry": "Private Banks",
        "base": 950.0,
        "mu": 0.00032,
        "sigma": 0.015,
    },
    {
        "symbol": "HCLTECH",
        "name": "HCL Technologies",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 1250.0,
        "mu": 0.00027,
        "sigma": 0.015,
    },
    {
        "symbol": "WIPRO",
        "name": "Wipro",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 420.0,
        "mu": 0.00018,
        "sigma": 0.016,
    },
    {
        "symbol": "TECHM",
        "name": "Tech Mahindra",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 1180.0,
        "mu": 0.00020,
        "sigma": 0.017,
    },
    {
        "symbol": "LTIM",
        "name": "LTIMindtree",
        "sector": "Information Technology",
        "industry": "IT Services",
        "base": 5100.0,
        "mu": 0.00022,
        "sigma": 0.018,
    },
    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel",
        "sector": "Communication Services",
        "industry": "Telecom",
        "base": 980.0,
        "mu": 0.00040,
        "sigma": 0.014,
    },
    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints",
        "sector": "Materials",
        "industry": "Paints",
        "base": 2900.0,
        "mu": 0.00015,
        "sigma": 0.014,
    },
    {
        "symbol": "ITC",
        "name": "ITC",
        "sector": "Consumer Staples",
        "industry": "Diversified Tobacco",
        "base": 440.0,
        "mu": 0.00025,
        "sigma": 0.012,
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "sector": "Financials",
        "industry": "Public Banks",
        "base": 620.0,
        "mu": 0.00033,
        "sigma": 0.016,
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance",
        "sector": "Financials",
        "industry": "NBFC",
        "base": 6800.0,
        "mu": 0.00030,
        "sigma": 0.020,
    },
]


def _business_days(start: date, end: date) -> list[date]:
    """Mon–Fri calendar days (no holiday calendar in v0 sample)."""
    days: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def sample_prices_dir(root: Path | None = None) -> Path:
    r = root or raw_root()
    return r / "prices" / f"{SAMPLE_DROP_DATE}_{SAMPLE_SOURCE_TAG}"


def sample_instruments_dir(root: Path | None = None) -> Path:
    r = root or raw_root()
    return r / "instruments" / f"{SAMPLE_DROP_DATE}_{SAMPLE_SOURCE_TAG}"


def sample_drop_exists(root: Path | None = None) -> bool:
    prices = sample_prices_dir(root) / "prices.parquet"
    instruments = sample_instruments_dir(root) / "instruments.json"
    return prices.is_file() and instruments.is_file()


def _simulate_ohlcv(
    *,
    symbol: str,
    base: float,
    mu: float,
    sigma: float,
    dates: list[date],
    rng: np.random.Generator,
) -> list[dict]:
    """GBM-ish path with simple OHLC around close."""
    n = len(dates)
    shocks = rng.normal(mu, sigma, size=n)
    # mild mean reversion toward base to avoid blow-ups
    closes = np.empty(n, dtype=np.float64)
    px = float(base)
    for i, r in enumerate(shocks):
        px = max(px * float(np.exp(r)), 1.0)
        # soft pull back if far from base
        if px > base * 3.5:
            px *= 0.98
        if px < base * 0.35:
            px *= 1.02
        closes[i] = px

    rows: list[dict] = []
    for i, d in enumerate(dates):
        c = float(closes[i])
        prev = float(closes[i - 1]) if i else c
        open_ = prev * float(1.0 + rng.normal(0, 0.002))
        high = max(open_, c) * float(1.0 + abs(rng.normal(0, 0.004)))
        low = min(open_, c) * float(1.0 - abs(rng.normal(0, 0.004)))
        low = max(low, 0.01)
        volume = float(rng.integers(200_000, 5_000_000))
        rows.append(
            {
                "symbol": symbol,
                "date": d.isoformat(),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(c, 2),
                "adj_close": round(c, 2),
                "volume": volume,
                "currency": "INR",
                "source": SAMPLE_SOURCE_TAG,
            }
        )
    return rows


def generate_sample_raw(
    *,
    force: bool = False,
    seed: int = 42,
    start: date = SAMPLE_START,
    end: date = SAMPLE_END,
    root: Path | None = None,
) -> dict[str, Path]:
    """Write sample instruments + prices under data/raw/. Returns written paths."""
    root = root or raw_root()
    prices_dir = sample_prices_dir(root)
    instruments_dir = sample_instruments_dir(root)
    prices_path = prices_dir / "prices.parquet"
    instruments_path = instruments_dir / "instruments.json"

    if sample_drop_exists(root) and not force:
        logger.info(
            "sample drop already present at %s — skip generation (use force=True to overwrite)",
            prices_dir,
        )
        return {"prices": prices_path, "instruments": instruments_path}

    dates = _business_days(start, end)
    if not dates:
        raise ValueError(f"no business days between {start} and {end}")

    rng = np.random.default_rng(seed)
    all_rows: list[dict] = []
    instruments: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for meta in UNIVERSE:
        all_rows.extend(
            _simulate_ohlcv(
                symbol=meta["symbol"],
                base=meta["base"],
                mu=meta["mu"],
                sigma=meta["sigma"],
                dates=dates,
                rng=rng,
            )
        )
        instruments.append(
            {
                "symbol": meta["symbol"],
                "name": meta["name"],
                "sector": meta["sector"],
                "industry": meta["industry"],
                "exchange": "NSE",
                "currency": "INR",
                "isin": None,
                "is_active": True,
                "updated_at": now,
            }
        )

    prices_dir.mkdir(parents=True, exist_ok=True)
    instruments_dir.mkdir(parents=True, exist_ok=True)

    df = pl.DataFrame(all_rows).with_columns(
        pl.col("date").str.to_date("%Y-%m-%d"),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("adj_close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64),
    )
    df = df.sort(["symbol", "date"])
    df.write_parquet(prices_path)

    instruments_path.write_text(
        json.dumps(instruments, indent=2) + "\n", encoding="utf-8"
    )

    # Lightweight README so humans know this is synthetic
    note = prices_dir / "README.md"
    note.write_text(
        (
            "# Sample price drop (synthetic)\n\n"
            f"- Generated: {now}\n"
            f"- Range: {start.isoformat()} → {end.isoformat()} (Mon–Fri)\n"
            f"- Symbols: {len(UNIVERSE)}\n"
            f"- Source label: `{SAMPLE_SOURCE_TAG}`\n"
            f"- Seed: {seed}\n\n"
            "Prices are **synthetic** GBM-style paths for demos only — "
            "not real market data.\n"
        ),
        encoding="utf-8",
    )

    logger.info(
        "generated sample: %d price rows, %d instruments → %s",
        df.height,
        len(instruments),
        prices_dir,
    )
    return {"prices": prices_path, "instruments": instruments_path}
