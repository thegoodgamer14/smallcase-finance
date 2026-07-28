"""SIP simulation: allocate contributions → units → market value → cashflows.

Pure functions (no I/O). Zero costs MVP: full SIP amount deploys into fractional
units at session close. Missing prices on invest day → exclude symbol and
renormalize remaining weights (v0 gap policy spirit).

Task API: ``run_sip_simulation(weights, prices, amount, schedule)``.

Schedule resolution: ``calc/sip_schedule.py``. XIRR: ``calc/xirr.py``.
I/O + StrategyConfig orchestration: ``services/sip_service.py`` (not this module).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from smallcase_finance.calc.risk import max_drawdown
from smallcase_finance.calc.weights import normalize_weights
from smallcase_finance.calc.xirr import Cashflow, xirr


@dataclass(frozen=True, slots=True)
class MarketValuePoint:
    date: date
    market_value: float


@dataclass(frozen=True, slots=True)
class SipBuyEvent:
    """One SIP contribution allocation on an invest session."""

    date: date
    amount: float
    weights_used: dict[str, float]
    units_bought: dict[str, float]
    gap_symbols: tuple[str, ...] = ()


@dataclass
class SipSimulationResult:
    """Result of a pure SIP run (units path + cashflows + metrics)."""

    invest_dates: list[date]
    cashflows: list[Cashflow]
    units_end: dict[str, float]
    market_value: list[MarketValuePoint]
    buys: list[SipBuyEvent]
    xirr: Optional[float]
    total_invested: float
    final_value: float
    absolute_gain: float
    max_drawdown: float
    n_sips: int
    as_of: Optional[date]
    warnings: list[str] = field(default_factory=list)
    cash_in_by_symbol: dict[str, float] = field(default_factory=dict)
    units_path: list[tuple[date, dict[str, float]]] = field(default_factory=list)


def _price_on(
    prices: Mapping[str, Mapping[date, float]],
    symbol: str,
    d: date,
) -> Optional[float]:
    series = prices.get(symbol)
    if series is None:
        return None
    p = series.get(d)
    if p is None:
        return None
    p = float(p)
    if p <= 0.0 or p != p:  # NaN guard
        return None
    return p


def _sessions_from_prices(
    prices: Mapping[str, Mapping[date, float]],
    symbols: Sequence[str],
) -> list[date]:
    dates: set[date] = set()
    for sym in symbols:
        series = prices.get(sym)
        if series:
            dates.update(series.keys())
    return sorted(dates)


def _mark_value(
    units: Mapping[str, float],
    prices: Mapping[str, Mapping[date, float]],
    d: date,
    *,
    use_stale: bool = True,
    last_px: Optional[dict[str, float]] = None,
) -> tuple[float, list[str]]:
    mv = 0.0
    warnings: list[str] = []
    for sym, q in units.items():
        if q == 0.0:
            continue
        p = _price_on(prices, sym, d)
        if p is None and use_stale and last_px is not None and sym in last_px:
            p = last_px[sym]
            warnings.append(f"stale_mark:{sym}:{d.isoformat()}")
        if p is None:
            warnings.append(f"missing_mark:{sym}:{d.isoformat()}")
            continue
        mv += float(q) * p
        if last_px is not None:
            last_px[sym] = p
    return mv, warnings


def allocate_sip_buy(
    amount: float,
    weights: Mapping[str, float],
    prices_on_day: Mapping[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], list[str]]:
    """Allocate ``amount`` across symbols at same-day prices (zero costs).

    Returns
    -------
    units_bought, cash_allocated, weights_used, gap_symbols
    """
    if amount <= 0:
        raise ValueError("amount must be > 0")
    w_all = normalize_weights(weights)
    available = {
        s: float(prices_on_day[s])
        for s in w_all
        if s in prices_on_day and float(prices_on_day[s]) > 0
    }
    gap = [s for s in w_all if s not in available]
    if not available:
        return {}, {}, {}, gap

    w_use = normalize_weights({s: w_all[s] for s in available})
    units: dict[str, float] = {}
    cash: dict[str, float] = {}
    for s, w in w_use.items():
        cash_s = amount * w
        units[s] = cash_s / available[s]
        cash[s] = cash_s
    return units, cash, w_use, gap


def run_sip_simulation(
    weights: Mapping[str, float],
    prices: Mapping[str, Mapping[date, float]],
    amount: float,
    schedule: Sequence[date],
    *,
    as_of: date | None = None,
    trading_dates: Sequence[date] | None = None,
    mark_daily: bool = True,
) -> SipSimulationResult:
    """Simulate monthly SIP into a static-weight equity/ETF basket.

    Parameters
    ----------
    weights
        Target weights (renormalized). Non-positive dropped.
    prices
        ``{symbol: {date: close, ...}, ...}`` daily bars.
    amount
        Fixed contribution per SIP date. Full amount deploys (fractional units,
        zero costs).
    schedule
        Invest dates from :func:`sip_schedule` (next-trading-day resolved).
    as_of
        Terminal valuation date. Default = last session in the mark calendar.
    trading_dates
        Session calendar for daily MV marks. Default = union of price dates
        for symbols in ``weights``.
    mark_daily
        If True, emit MV for every session from first SIP through ``as_of``.

    Returns
    -------
    SipSimulationResult
        Units path, MV series, cashflows (contributions negative, terminal
        positive), XIRR, and secondary metrics (total_invested, final_value,
        max_drawdown).
    """
    if amount <= 0:
        raise ValueError("amount must be > 0")
    w_target = normalize_weights(weights)
    symbols = list(w_target.keys())

    sessions = (
        list(trading_dates)
        if trading_dates is not None
        else _sessions_from_prices(prices, symbols)
    )
    if not sessions:
        return SipSimulationResult(
            invest_dates=[],
            cashflows=[],
            units_end={},
            market_value=[],
            buys=[],
            xirr=None,
            total_invested=0.0,
            final_value=0.0,
            absolute_gain=0.0,
            max_drawdown=0.0,
            n_sips=0,
            as_of=as_of,
            warnings=["empty_sessions"],
        )

    invest_dates = sorted({d for d in schedule})

    units: dict[str, float] = {s: 0.0 for s in symbols}
    cash_in: dict[str, float] = {s: 0.0 for s in symbols}
    buys: list[SipBuyEvent] = []
    cashflows: list[Cashflow] = []
    units_path: list[tuple[date, dict[str, float]]] = []
    warnings: list[str] = []
    actual_invests: list[date] = []

    for s in invest_dates:
        px_day: dict[str, float] = {}
        for sym in symbols:
            p = _price_on(prices, sym, s)
            if p is not None:
                px_day[sym] = p
        bought, cash_alloc, w_use, gap = allocate_sip_buy(amount, w_target, px_day)
        if not bought:
            warnings.append(f"no_session_prices:{s.isoformat()}")
            continue
        if gap:
            warnings.append(
                f"gap_symbols:{s.isoformat()}:{','.join(sorted(gap))}"
            )
        for sym, dq in bought.items():
            units[sym] = units.get(sym, 0.0) + dq
            cash_in[sym] = cash_in.get(sym, 0.0) + cash_alloc.get(sym, 0.0)
        buys.append(
            SipBuyEvent(
                date=s,
                amount=float(amount),
                weights_used=dict(w_use),
                units_bought=dict(bought),
                gap_symbols=tuple(sorted(gap)),
            )
        )
        cashflows.append(
            Cashflow(date=s, amount=-float(amount), kind="contribution")
        )
        actual_invests.append(s)
        units_path.append((s, {k: float(v) for k, v in units.items() if v != 0.0}))

    if not actual_invests:
        return SipSimulationResult(
            invest_dates=[],
            cashflows=[],
            units_end={},
            market_value=[],
            buys=[],
            xirr=None,
            total_invested=0.0,
            final_value=0.0,
            absolute_gain=0.0,
            max_drawdown=0.0,
            n_sips=0,
            as_of=as_of,
            warnings=warnings or ["no_successful_sips"],
            cash_in_by_symbol={},
            units_path=[],
        )

    first_sip = actual_invests[0]
    last_session = sessions[-1]
    terminal = as_of if as_of is not None else last_session
    mark_sessions = [d for d in sessions if first_sip <= d <= terminal]
    if not mark_sessions:
        mark_sessions = list(actual_invests)

    if not mark_daily:
        keep = set(actual_invests) | {mark_sessions[-1]}
        mark_sessions = [d for d in mark_sessions if d in keep]

    last_px: dict[str, float] = {}
    mv_series: list[MarketValuePoint] = []
    for d in mark_sessions:
        mv, w = _mark_value(units, prices, d, use_stale=True, last_px=last_px)
        warnings.extend(w)
        mv_series.append(MarketValuePoint(date=d, market_value=mv))

    final_value = mv_series[-1].market_value if mv_series else 0.0
    terminal_date = mv_series[-1].date if mv_series else terminal
    cashflows.append(
        Cashflow(date=terminal_date, amount=float(final_value), kind="terminal")
    )

    total_invested = float(amount) * len(actual_invests)
    rate = xirr(cashflows)
    mv_values = [p.market_value for p in mv_series]
    mdd = max_drawdown(mv_values) if mv_values else 0.0
    units_end = {k: float(v) for k, v in units.items() if v != 0.0}

    return SipSimulationResult(
        invest_dates=list(actual_invests),
        cashflows=cashflows,
        units_end=units_end,
        market_value=mv_series,
        buys=buys,
        xirr=rate,
        total_invested=total_invested,
        final_value=float(final_value),
        absolute_gain=float(final_value) - total_invested,
        max_drawdown=float(mdd),
        n_sips=len(actual_invests),
        as_of=terminal_date,
        warnings=warnings,
        cash_in_by_symbol={k: float(v) for k, v in cash_in.items() if v != 0.0},
        units_path=units_path,
    )


def symbol_contribution(
    result: SipSimulationResult,
    prices: Mapping[str, Mapping[date, float]],
) -> list[dict[str, float | str]]:
    """SIP P&L contribution: market_value_end − cash_in per symbol."""
    if not result.as_of:
        return []
    T = result.as_of
    rows: list[dict[str, float | str]] = []
    total_mv = result.final_value
    for sym, q in result.units_end.items():
        p = _price_on(prices, sym, T)
        if p is None:
            continue
        mv_end = q * p
        cash = result.cash_in_by_symbol.get(sym, 0.0)
        rows.append(
            {
                "symbol": sym,
                "cash_in": cash,
                "market_value_end": mv_end,
                "contribution": mv_end - cash,
                "weight_end": (mv_end / total_mv) if total_mv > 0 else 0.0,
            }
        )
    rows.sort(key=lambda r: str(r["symbol"]))
    return rows
