"""Risk and performance summary metrics (pure).

Conventions (API-aligned, see docs/analytics/metrics-definitions.md):
- ratios as decimals (0.14 = 14%)
- max_drawdown is **negative** (worst peak-to-trough fraction)
- periods_per_year default 252
- default risk-free rate for Sharpe is 0.0 (override with 0.06 for India-like)
- metrics_snapshot Sharpe uses (CAGR - rf) / vol (not mean-excess form)
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from typing import Optional

# Pure-module defaults (no env reads). Match config defaults.
PERIODS_PER_YEAR: int = 252
DEFAULT_RF: float = 0.0


def total_return(nav: Sequence[float]) -> float:
    """``nav_T / nav_0 - 1``. Empty raises; single point → 0.0."""
    if len(nav) < 1:
        raise ValueError("nav series must be non-empty")
    if len(nav) < 2:
        return 0.0
    start = float(nav[0])
    end = float(nav[-1])
    if start <= 0.0:
        raise ValueError("start nav must be > 0")
    return end / start - 1.0


def cagr(
    nav: Sequence[float],
    *,
    dates: Optional[Sequence[date]] = None,
    n_periods: int | None = None,
    periods_per_year: float = PERIODS_PER_YEAR,
    min_years: float = 1.0 / 12.0,
) -> Optional[float]:
    """Annualized compound growth rate from a NAV path.

    Year fraction (first match wins):
    1. Calendar: ``(dates[-1] - dates[0]).days / 365.25`` when ``dates`` given.
    2. Observation count: ``n_periods / periods_per_year`` where
       ``n_periods`` defaults to ``len(nav)`` (pipeline metrics_snapshot).

    Returns None if window shorter than ``min_years`` or NAV invalid.
    """
    if len(nav) < 2:
        return None
    start = float(nav[0])
    end = float(nav[-1])
    if start <= 0.0 or end <= 0.0:
        return None

    if dates is not None and len(dates) == len(nav):
        days = (dates[-1] - dates[0]).days
        if days <= 0:
            return None
        years = days / 365.25
    else:
        periods = int(n_periods if n_periods is not None else len(nav))
        if periods <= 0 or periods_per_year <= 0:
            return None
        years = periods / float(periods_per_year)

    if years < min_years:
        return None
    return (end / start) ** (1.0 / years) - 1.0


def volatility(
    returns: Sequence[float],
    *,
    periods_per_year: float = PERIODS_PER_YEAR,
    ddof: int = 1,
) -> Optional[float]:
    """Annualized stdev of periodic returns: ``stdev * sqrt(ppy)``."""
    r = [float(x) for x in returns]
    n = len(r)
    if n < 2:
        return None
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be > 0")
    mean = sum(r) / n
    denom = n - ddof
    if denom <= 0:
        return None
    var = sum((x - mean) ** 2 for x in r) / denom
    return math.sqrt(var) * math.sqrt(periods_per_year)


def max_drawdown(nav: Sequence[float]) -> float:
    """Worst peak-to-trough drawdown as a **negative** fraction (0 if flat/up)."""
    if not nav:
        return 0.0
    peak = float(nav[0])
    worst = 0.0
    for v in nav:
        x = float(v)
        if x > peak:
            peak = x
        if peak > 0.0:
            dd = x / peak - 1.0
            if dd < worst:
                worst = dd
    return worst


def downside_deviation(
    returns: Sequence[float],
    *,
    periods_per_year: float = PERIODS_PER_YEAR,
    mar: float = 0.0,
    ddof: int = 1,
) -> Optional[float]:
    """Annualized downside deviation of returns below ``mar`` (default 0)."""
    r = [float(x) for x in returns]
    n = len(r)
    if n < 2:
        return None
    downs = [min(x - mar, 0.0) for x in r]
    denom = n - ddof
    if denom <= 0:
        return None
    dvar = sum(x * x for x in downs) / denom
    return math.sqrt(dvar) * math.sqrt(periods_per_year)


def sharpe(
    *,
    cagr_value: float | None,
    volatility_value: float | None,
    rf_rate: float = DEFAULT_RF,
) -> Optional[float]:
    """``(cagr - rf_rate) / volatility`` when defined (metrics_snapshot form).

    ``rf_rate`` is an **annual** risk-free rate in decimal form.
    """
    if cagr_value is None or volatility_value is None:
        return None
    if volatility_value <= 0.0:
        return None
    return (float(cagr_value) - float(rf_rate)) / float(volatility_value)


def sharpe_from_returns(
    returns: Sequence[float],
    *,
    rf: float = DEFAULT_RF,
    periods_per_year: float = PERIODS_PER_YEAR,
) -> Optional[float]:
    """Classic annualized Sharpe: mean excess daily return / stdev × √ppy.

    ``rf`` is annualized; converted to per-period as ``rf / periods_per_year``.
    Prefer ``sharpe(cagr_value=..., volatility_value=...)`` for curated metrics.
    """
    r = [float(x) for x in returns]
    n = len(r)
    if n < 2:
        return None
    rf_per = float(rf) / float(periods_per_year)
    excess = [x - rf_per for x in r]
    mean = sum(excess) / n
    var = sum((x - mean) ** 2 for x in excess) / (n - 1)
    if var <= 0:
        return None
    return (mean / math.sqrt(var)) * math.sqrt(periods_per_year)


def sortino(
    *,
    cagr_value: float | None,
    downside_dev: float | None,
    rf_rate: float = DEFAULT_RF,
) -> Optional[float]:
    """``(cagr - rf_rate) / downside_deviation`` when defined."""
    if cagr_value is None or downside_dev is None:
        return None
    if downside_dev <= 0.0:
        return None
    return (float(cagr_value) - float(rf_rate)) / float(downside_dev)


def calmar(
    *,
    cagr_value: float | None,
    max_dd: float | None,
) -> Optional[float]:
    """``cagr / abs(max_drawdown)`` when drawdown is strictly negative."""
    if cagr_value is None or max_dd is None:
        return None
    if max_dd >= 0.0:
        return None
    return float(cagr_value) / abs(float(max_dd))


def summary_metrics(
    nav: Sequence[float],
    returns: Sequence[float] | None = None,
    *,
    dates: Optional[Sequence[date]] = None,
    rf_rate: float = DEFAULT_RF,
    periods_per_year: float = PERIODS_PER_YEAR,
) -> dict[str, float | int | None]:
    """Bundle core metrics for a window (CAGR-form Sharpe)."""
    if returns is None:
        if not nav:
            rets: list[float] = []
        else:
            rets = [0.0]
            for i in range(1, len(nav)):
                prev = float(nav[i - 1])
                if prev <= 0.0:
                    raise ValueError("nav must be > 0")
                rets.append(float(nav[i]) / prev - 1.0)
    else:
        rets = [float(x) for x in returns]

    if not nav:
        return {
            "n_obs": 0,
            "total_return": None,
            "cagr": None,
            "volatility": None,
            "max_drawdown": 0.0,
            "sharpe": None,
            "sortino": None,
            "calmar": None,
            "rf_rate": float(rf_rate),
            "periods_per_year": int(periods_per_year),
        }

    tr = total_return(nav)
    cagr_v = cagr(nav, dates=dates, periods_per_year=periods_per_year)
    vol = volatility(rets, periods_per_year=periods_per_year)
    mdd = max_drawdown(nav)
    ddev = downside_deviation(rets, periods_per_year=periods_per_year)
    return {
        "n_obs": len(rets),
        "total_return": tr,
        "cagr": cagr_v,
        "volatility": vol,
        "max_drawdown": mdd,
        "sharpe": sharpe(cagr_value=cagr_v, volatility_value=vol, rf_rate=rf_rate),
        "sortino": sortino(cagr_value=cagr_v, downside_dev=ddev, rf_rate=rf_rate),
        "calmar": calmar(cagr_value=cagr_v, max_dd=mdd),
        "rf_rate": float(rf_rate),
        "periods_per_year": int(periods_per_year),
    }


def metrics_from_nav(
    nav: Sequence[float],
    *,
    dates: Optional[Sequence[date]] = None,
    daily_returns: Optional[Sequence[Optional[float]]] = None,
    periods_per_year: float = PERIODS_PER_YEAR,
    risk_free_rate: float = DEFAULT_RF,
) -> dict[str, Optional[float | int]]:
    """Bundle summary metrics from a NAV path (backend-compatible keys)."""
    if not nav:
        return {
            "cagr": None,
            "volatility": None,
            "max_drawdown": None,
            "sharpe": None,
            "total_return": None,
            "n_observations": 0,
        }

    if daily_returns is not None:
        rets = [float(r) for r in daily_returns if r is not None]
    else:
        rets = []
        for i in range(1, len(nav)):
            prev = float(nav[i - 1])
            if prev > 0:
                rets.append(float(nav[i]) / prev - 1.0)

    cagr_v = cagr(nav, dates=dates, periods_per_year=periods_per_year)
    vol = volatility(rets, periods_per_year=periods_per_year)
    return {
        "cagr": cagr_v,
        "volatility": vol,
        "max_drawdown": max_drawdown(nav),
        "sharpe": sharpe(
            cagr_value=cagr_v, volatility_value=vol, rf_rate=risk_free_rate
        ),
        "total_return": total_return(nav),
        "n_observations": len(nav),
    }
