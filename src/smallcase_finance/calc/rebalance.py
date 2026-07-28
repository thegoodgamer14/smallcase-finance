"""Rebalance simulation pure logic (target vs drift, periodic backtest)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from smallcase_finance.calc.nav import nav_from_returns
from smallcase_finance.calc.returns import portfolio_return
from smallcase_finance.calc.weights import normalize_weights, weight_drift


@dataclass(frozen=True)
class RebalanceTrade:
    symbol: str
    weight_from: float
    weight_to: float

    @property
    def delta(self) -> float:
        return self.weight_to - self.weight_from


@dataclass
class RebalanceResult:
    weights: dict[str, float]
    trades: list[RebalanceTrade] = field(default_factory=list)
    turnover: float = 0.0  # 0.5 * sum(|delta|) = one-way turnover


def rebalance_weights(
    target: Mapping[str, float],
    current: Mapping[str, float],
    threshold: float | None = None,
) -> RebalanceResult:
    """Suggest a rebalance from ``current`` toward ``target``.

    If ``threshold`` is set, only rebalance when one-way turnover would
    exceed this fraction; otherwise return current weights unchanged.
    """
    t = normalize_weights(target)
    c = normalize_weights(current) if current else {k: 0.0 for k in t}

    symbols = sorted(set(t) | set(c))
    deltas = {s: t.get(s, 0.0) - c.get(s, 0.0) for s in symbols}
    turnover = 0.5 * sum(abs(d) for d in deltas.values())

    if threshold is not None and turnover < float(threshold):
        return RebalanceResult(weights=dict(c), trades=[], turnover=turnover)

    trades = [
        RebalanceTrade(symbol=s, weight_from=c.get(s, 0.0), weight_to=t.get(s, 0.0))
        for s in symbols
        if abs(deltas[s]) > 1e-12
    ]
    return RebalanceResult(weights=dict(t), trades=trades, turnover=turnover)


@dataclass
class BacktestPath:
    """Result of a two-strategy backtest on aligned price paths."""

    returns_rebalanced: list[float]
    returns_buy_hold: list[float]
    nav_rebalanced: list[float]
    nav_buy_hold: list[float]
    rebalance_indices: list[int]
    weights_end_rebalanced: dict[str, float]
    weights_end_buy_hold: dict[str, float]
    turnover_total: float


def backtest_rebalance_vs_buyhold(
    prices_by_symbol: Mapping[str, Sequence[float]],
    target_weights: Mapping[str, float],
    *,
    rebalance_every: int = 21,
    start_nav: float = 100.0,
    threshold: float | None = None,
) -> BacktestPath:
    """Compare periodic rebalance-to-target vs pure buy-and-hold drift.

    - Day 0 return is 0.0; positions open at day-0 closes.
    - No transaction costs in v0.
    - Buy-and-hold: initial target weights drift with returns, never reset.
    - Rebalanced: reset to target every ``rebalance_every`` steps.
    """
    target = normalize_weights(target_weights)
    symbols = list(target.keys())
    if not symbols:
        raise ValueError("target_weights is empty")

    lengths = {s: len(prices_by_symbol[s]) for s in symbols if s in prices_by_symbol}
    missing = [s for s in symbols if s not in prices_by_symbol]
    if missing:
        raise ValueError(f"missing price series for: {missing}")
    t_len = next(iter(lengths.values()))
    if any(n != t_len for n in lengths.values()):
        raise ValueError("all price series must have equal length")
    if t_len < 2:
        raise ValueError("need at least 2 price points")
    if rebalance_every < 1:
        raise ValueError("rebalance_every must be >= 1")

    asset_rets: dict[str, list[float]] = {}
    for s in symbols:
        px = [float(x) for x in prices_by_symbol[s]]
        if any(p <= 0 for p in px):
            raise ValueError(f"prices for {s} must be > 0")
        rs = [0.0]
        for i in range(1, t_len):
            rs.append(px[i] / px[i - 1] - 1.0)
        asset_rets[s] = rs

    w_rb = dict(target)
    w_bh = dict(target)
    rets_rb: list[float] = [0.0]
    rets_bh: list[float] = [0.0]
    rebalance_indices = [0]
    turnover_total = 0.0

    for i in range(1, t_len):
        day_rets = {s: asset_rets[s][i] for s in symbols}

        r_rb = portfolio_return(day_rets, w_rb, renormalize=True)
        r_bh = portfolio_return(day_rets, w_bh, renormalize=True)
        rets_rb.append(r_rb)
        rets_bh.append(r_bh)

        w_rb = weight_drift(w_rb, day_rets)
        w_bh = weight_drift(w_bh, day_rets)

        if i % rebalance_every == 0:
            result = rebalance_weights(target, w_rb, threshold=threshold)
            if result.trades:
                rebalance_indices.append(i)
                turnover_total += result.turnover
                w_rb = result.weights

    return BacktestPath(
        returns_rebalanced=rets_rb,
        returns_buy_hold=rets_bh,
        nav_rebalanced=nav_from_returns(rets_rb, start_nav=start_nav),
        nav_buy_hold=nav_from_returns(rets_bh, start_nav=start_nav),
        rebalance_indices=rebalance_indices,
        weights_end_rebalanced=w_rb,
        weights_end_buy_hold=w_bh,
        turnover_total=turnover_total,
    )
