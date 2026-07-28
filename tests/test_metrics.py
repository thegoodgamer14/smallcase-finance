"""Lightweight pytest coverage for pure calc metrics on synthetic series."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from smallcase_finance.calc.nav import (
    active_weights_on,
    build_nav_from_prices,
    nav_from_returns,
)
from smallcase_finance.calc.rebalance import (
    backtest_rebalance_vs_buyhold,
    rebalance_weights,
)
from smallcase_finance.calc.returns import (
    contribution_by_symbol,
    portfolio_return,
    residual_contribution,
    simple_returns,
    total_return_from_prices,
)
from smallcase_finance.calc.risk import (
    cagr,
    max_drawdown,
    sharpe,
    summary_metrics,
    total_return,
    volatility,
)
from smallcase_finance.calc.weights import normalize_weights, weight_drift


# ---------------------------------------------------------------------------
# weights
# ---------------------------------------------------------------------------


def test_normalize_weights_sums_to_one():
    w = normalize_weights({"A": 1.0, "B": 3.0})
    assert abs(sum(w.values()) - 1.0) < 1e-12
    assert abs(w["A"] - 0.25) < 1e-12
    assert abs(w["B"] - 0.75) < 1e-12


def test_normalize_weights_drops_non_positive():
    w = normalize_weights({"A": 0.5, "B": 0.0, "C": -1.0, "D": 0.5})
    assert set(w) == {"A", "D"}
    assert abs(w["A"] - 0.5) < 1e-12


def test_normalize_weights_empty_raises():
    with pytest.raises(ValueError):
        normalize_weights({})
    with pytest.raises(ValueError):
        normalize_weights({"A": 0.0})


# ---------------------------------------------------------------------------
# returns / NAV
# ---------------------------------------------------------------------------


def test_simple_returns_first_zero():
    rets = simple_returns([100.0, 110.0, 99.0])
    assert rets[0] == 0.0
    assert abs(rets[1] - 0.10) < 1e-12
    assert abs(rets[2] - (99.0 / 110.0 - 1.0)) < 1e-12


def test_nav_from_returns_roundtrip():
    prices = [100.0, 110.0, 121.0]
    rets = simple_returns(prices)
    nav = nav_from_returns(rets, start_nav=100.0)
    assert len(nav) == 3
    assert abs(nav[0] - 100.0) < 1e-12
    assert abs(nav[1] - 110.0) < 1e-12
    assert abs(nav[2] - 121.0) < 1e-12


def test_portfolio_return_weighted():
    r = portfolio_return({"A": 0.10, "B": -0.05}, {"A": 0.6, "B": 0.4})
    assert abs(r - (0.6 * 0.10 + 0.4 * -0.05)) < 1e-12


def test_portfolio_return_renormalize_gap():
    # B missing → only A contributes, weight renormalized to 1
    r = portfolio_return({"A": 0.10}, {"A": 0.5, "B": 0.5}, renormalize=True)
    assert abs(r - 0.10) < 1e-12


def test_total_return_from_prices():
    assert abs(total_return_from_prices([100.0, 150.0]) - 0.5) < 1e-12


# ---------------------------------------------------------------------------
# risk metrics
# ---------------------------------------------------------------------------


def test_total_return_and_cagr_known_path():
    # Double over exactly 252 periods → CAGR ≈ 100% when years = n_obs/252 = 1
    nav = [100.0] + [100.0 * (2.0 ** (i / 252.0)) for i in range(1, 253)]
    # len(nav) = 253
    assert abs(total_return(nav) - 1.0) < 1e-9
    # years = 253/252 → slightly less than 100% CAGR for full double
    c = cagr(nav, periods_per_year=252)
    assert c is not None
    assert c > 0.95


def test_cagr_short_window_none():
    nav = [100.0, 101.0]  # 2 obs → years = 2/252 < 1/12
    assert cagr(nav, periods_per_year=252) is None


def test_volatility_constant_returns_zero():
    rets = [0.01] * 50
    vol = volatility(rets, periods_per_year=252)
    assert vol is not None
    assert abs(vol) < 1e-12


def test_volatility_known_series():
    # returns [0.0, 0.02, -0.02]; sample stdev * sqrt(252)
    rets = [0.0, 0.02, -0.02]
    mean = sum(rets) / 3
    var = sum((x - mean) ** 2 for x in rets) / 2
    expected = math.sqrt(var) * math.sqrt(252)
    got = volatility(rets, periods_per_year=252)
    assert got is not None
    assert abs(got - expected) < 1e-12


def test_max_drawdown_negative():
    nav = [100.0, 120.0, 90.0, 95.0]
    # peak 120 → trough 90 → dd = 90/120 - 1 = -0.25
    assert abs(max_drawdown(nav) - (-0.25)) < 1e-12


def test_max_drawdown_no_drawdown():
    assert abs(max_drawdown([100.0, 110.0, 120.0]) - 0.0) < 1e-12


def test_sharpe_formula():
    s = sharpe(cagr_value=0.12, volatility_value=0.20, rf_rate=0.06)
    assert s is not None
    assert abs(s - 0.30) < 1e-12
    assert sharpe(cagr_value=0.12, volatility_value=0.0) is None


def test_summary_metrics_keys():
    nav = [100.0, 102.0, 101.0, 105.0]
    m = summary_metrics(nav, rf_rate=0.0)
    for key in (
        "n_obs",
        "total_return",
        "cagr",
        "volatility",
        "max_drawdown",
        "sharpe",
        "sortino",
        "calmar",
        "rf_rate",
    ):
        assert key in m
    assert m["n_obs"] == 4
    assert abs(m["total_return"] - 0.05) < 1e-12
    assert m["max_drawdown"] <= 0.0


# ---------------------------------------------------------------------------
# contribution / attribution
# ---------------------------------------------------------------------------


def test_contribution_by_symbol():
    c = contribution_by_symbol(
        {"A": 0.6, "B": 0.4},
        {"A": 0.10, "B": -0.05},
    )
    assert abs(c["A"] - 0.06) < 1e-12
    assert abs(c["B"] - (-0.02)) < 1e-12
    port = sum(c.values())
    assert abs(residual_contribution(port, c) - 0.0) < 1e-12


# ---------------------------------------------------------------------------
# rebalance / backtest
# ---------------------------------------------------------------------------


def test_rebalance_weights_full_reset():
    res = rebalance_weights({"A": 0.5, "B": 0.5}, {"A": 0.8, "B": 0.2})
    assert abs(res.weights["A"] - 0.5) < 1e-12
    assert abs(res.turnover - 0.3) < 1e-12
    assert len(res.trades) == 2


def test_rebalance_threshold_skips():
    res = rebalance_weights(
        {"A": 0.5, "B": 0.5},
        {"A": 0.52, "B": 0.48},
        threshold=0.05,
    )
    # one-way turnover = 0.02 < 0.05 → keep current
    assert abs(res.weights["A"] - 0.52) < 1e-12
    assert res.trades == []


def test_weight_drift():
    w = weight_drift({"A": 0.5, "B": 0.5}, {"A": 0.10, "B": 0.0})
    # A: 0.55, B: 0.5 → total 1.05 → A=0.55/1.05, B=0.5/1.05
    assert abs(w["A"] - 0.55 / 1.05) < 1e-12
    assert abs(w["B"] - 0.5 / 1.05) < 1e-12


def test_backtest_rebalance_vs_buyhold_diverges():
    # Two assets with very different paths → BH drifts, rebalance stays near target
    t = 60
    a = [100.0 * (1.01**i) for i in range(t)]  # strong up
    b = [100.0 * (0.995**i) for i in range(t)]  # mild down
    path = backtest_rebalance_vs_buyhold(
        {"A": a, "B": b},
        {"A": 0.5, "B": 0.5},
        rebalance_every=10,
        start_nav=100.0,
    )
    assert len(path.nav_rebalanced) == t
    assert len(path.nav_buy_hold) == t
    assert path.nav_rebalanced[0] == 100.0
    assert path.nav_buy_hold[0] == 100.0
    # buy-hold should end overweight A
    assert path.weights_end_buy_hold["A"] > path.weights_end_rebalanced["A"]
    # rebalance should be closer to 50/50 than BH
    assert abs(path.weights_end_rebalanced["A"] - 0.5) < abs(
        path.weights_end_buy_hold["A"] - 0.5
    )
    assert path.turnover_total > 0.0
    assert 0 in path.rebalance_indices


def test_backtest_equal_assets_same_path():
    # Identical assets → rebalance and BH identical
    px = [100.0, 101.0, 102.0, 103.0, 104.0]
    path = backtest_rebalance_vs_buyhold(
        {"A": px, "B": list(px)},
        {"A": 0.5, "B": 0.5},
        rebalance_every=2,
    )
    for x, y in zip(path.nav_rebalanced, path.nav_buy_hold):
        assert abs(x - y) < 1e-10


# ---------------------------------------------------------------------------
# NAV from prices + versioned weights
# ---------------------------------------------------------------------------


def test_active_weights_on_version_pick():
    versions = [
        {
            "symbol": "A",
            "target_weight": 0.6,
            "effective_from": date(2024, 1, 1),
            "effective_to": date(2024, 6, 30),
        },
        {
            "symbol": "B",
            "target_weight": 0.4,
            "effective_from": date(2024, 1, 1),
            "effective_to": date(2024, 6, 30),
        },
        {
            "symbol": "A",
            "target_weight": 0.5,
            "effective_from": date(2024, 7, 1),
            "effective_to": None,
        },
        {
            "symbol": "B",
            "target_weight": 0.5,
            "effective_from": date(2024, 7, 1),
            "effective_to": None,
        },
    ]
    w1 = active_weights_on(versions, date(2024, 3, 15))
    assert abs(w1["A"] - 0.6) < 1e-12
    w2 = active_weights_on(versions, date(2024, 8, 1))
    assert abs(w2["A"] - 0.5) < 1e-12
    assert active_weights_on(versions, date(2023, 1, 1)) == {}


def test_build_nav_from_prices_two_assets():
    d0 = date(2024, 1, 2)
    dates = [d0 + timedelta(days=i) for i in range(5)]
    prices = {
        "A": {dates[i]: 100.0 * (1.01**i) for i in range(5)},
        "B": {dates[i]: 100.0 for i in range(5)},
    }
    weights = lambda d: {"A": 0.5, "B": 0.5}  # noqa: E731
    rows = build_nav_from_prices(
        dates=dates,
        prices=prices,
        weights_for_date=weights,
        start_nav=100.0,
    )
    assert len(rows) == 5
    assert rows[0]["nav"] == 100.0
    assert rows[0]["daily_return"] == 0.0
    assert rows[-1]["nav"] > 100.0
    assert rows[-1]["cum_return"] == pytest.approx(rows[-1]["nav"] / 100.0 - 1.0)
