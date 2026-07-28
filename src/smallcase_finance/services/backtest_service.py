"""Optional rebalance / backtest simulation orchestration."""

from __future__ import annotations

from datetime import date
from typing import Optional

from smallcase_finance.calc.rebalance import backtest_rebalance_vs_buyhold
from smallcase_finance.calc.risk import metrics_from_nav
from smallcase_finance.calc.weights import normalize_weights
from smallcase_finance.config import DEFAULT_RF, PERIODS_PER_YEAR
from smallcase_finance.data_access import smallcases as sc_da
from smallcase_finance.data_access.prices import get_prices
from smallcase_finance.schemas.backtest import (
    BacktestParams,
    BacktestRequest,
    BacktestResponse,
    RebalanceEventDTO,
)
from smallcase_finance.schemas.metrics import MetricValues
from smallcase_finance.schemas.nav import NavPointDTO

# Trading-day approximations for periodic rebalance rules
_REBALANCE_EVERY: dict[str, int] = {
    "monthly": 21,
    "quarterly": 63,
    "threshold_5pct": 1,
    "manual": 10**9,
    "none": 10**9,
}


def _resolve_rebalance(rule: str, threshold: Optional[float]) -> tuple[int, Optional[float]]:
    key = (rule or "manual").strip().lower()
    every = _REBALANCE_EVERY.get(key, 63)
    thr = threshold
    if key == "threshold_5pct" and thr is None:
        thr = 0.05
    return every, thr


def _metric_values(nav: list[float], dates: list[date]) -> MetricValues:
    m = metrics_from_nav(
        nav,
        dates=dates,
        periods_per_year=float(PERIODS_PER_YEAR),
        risk_free_rate=DEFAULT_RF,
    )
    return MetricValues(
        cagr=m.get("cagr"),  # type: ignore[arg-type]
        volatility=m.get("volatility"),  # type: ignore[arg-type]
        max_drawdown=m.get("max_drawdown"),  # type: ignore[arg-type]
        sharpe=m.get("sharpe"),  # type: ignore[arg-type]
        total_return=m.get("total_return"),  # type: ignore[arg-type]
        n_observations=int(m["n_observations"] or 0),
    )


def _align_price_matrix(
    price_rows: list[dict],
    symbols: list[str],
    *,
    start: Optional[date],
    end: Optional[date],
) -> tuple[list[date], dict[str, list[float]]]:
    """Build date-aligned close series (intersection of available dates)."""
    by_sym: dict[str, dict[date, float]] = {s: {} for s in symbols}
    for r in price_rows:
        sym = str(r["symbol"]).upper()
        d = r["date"]
        if d is None or sym not in by_sym:
            continue
        if start is not None and d < start:
            continue
        if end is not None and d > end:
            continue
        close = r.get("close")
        if close is None or float(close) <= 0:
            continue
        by_sym[sym][d] = float(close)

    # Intersection of dates where every symbol has a price
    common: set[date] | None = None
    for sym in symbols:
        dates_s = set(by_sym[sym].keys())
        common = dates_s if common is None else common & dates_s
    if not common:
        return [], {}

    ordered = sorted(common)
    matrix = {sym: [by_sym[sym][d] for d in ordered] for sym in symbols}
    return ordered, matrix


class BacktestService:
    def run(self, body: BacktestRequest) -> BacktestResponse:
        sc = sc_da.get_smallcase(body.smallcase_id)
        sid = sc["smallcase_id"]
        methodology = (body.methodology or sc.get("methodology") or "custom_weights").strip()
        rebalance_rule = (
            body.rebalance_rule or sc.get("rebalance_rule") or "manual"
        ).strip()
        rebalance_every, threshold = _resolve_rebalance(rebalance_rule, body.threshold)

        start = body.start or sc.get("inception_date")
        end = body.end

        # Weights as of start (or latest if start unknown)
        constituents = sc_da.get_constituents(sid, as_of=start)
        if not constituents:
            raise ValueError(f"No constituents available for {sid}")

        raw_weights = {
            str(c["symbol"]).upper(): float(c["target_weight"]) for c in constituents
        }
        if methodology.lower() == "equal_weight":
            n = len(raw_weights)
            target = {s: 1.0 / n for s in raw_weights}
        else:
            target = normalize_weights(raw_weights)

        symbols = sorted(target.keys())
        price_rows = get_prices(symbols, start=start, end=end)
        dates, prices_by_symbol = _align_price_matrix(
            price_rows, symbols, start=start, end=end
        )
        if len(dates) < 2:
            raise ValueError(
                "Insufficient aligned price history for backtest "
                f"(need ≥2 days; got {len(dates)} for {len(symbols)} symbols)"
            )

        path = backtest_rebalance_vs_buyhold(
            prices_by_symbol,
            target,
            rebalance_every=rebalance_every,
            start_nav=float(body.initial_nav),
            threshold=threshold,
        )

        nav_series = [
            NavPointDTO(date=dates[i], nav=path.nav_rebalanced[i])
            for i in range(len(dates))
        ]

        # Approximate turnover per rebalance event (uniform split of total if multi)
        events: list[RebalanceEventDTO] = []
        n_ev = max(len(path.rebalance_indices) - 1, 1)  # exclude day-0 open
        per = path.turnover_total / n_ev if path.turnover_total else 0.0
        for idx in path.rebalance_indices:
            if idx == 0:
                continue  # open, not a rebalance
            events.append(
                RebalanceEventDTO(date=dates[idx], turnover=round(per, 6))
            )

        metrics = _metric_values(path.nav_rebalanced, dates)
        bh_metrics = _metric_values(path.nav_buy_hold, dates)

        return BacktestResponse(
            smallcase_id=sid,
            params=BacktestParams(
                rebalance_rule=rebalance_rule,
                methodology=methodology,
                rebalance_every=rebalance_every,
                threshold=threshold,
                initial_nav=float(body.initial_nav),
                start=dates[0],
                end=dates[-1],
            ),
            metrics=metrics,
            nav_series=nav_series,
            rebalance_events=events,
            buy_hold_metrics=bh_metrics,
        )
