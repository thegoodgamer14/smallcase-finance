"""Pure financial calculations — no I/O, no FastAPI, no DuckDB.

Notebooks and tests should import from here so metrics match the API.
See docs/architecture/backend.md §5 and docs/analytics/metrics-definitions.md.

SIP Lab (primary metric XIRR): sip_schedule, run_sip_simulation, xirr —
see docs/architecture/sip-engine.md and docs/analytics/sip-xirr.md.
"""

from smallcase_finance.calc.nav import (
    active_weights_on,
    build_nav_from_prices,
    cum_return_from_nav,
    nav_from_returns,
    nav_series_from_price_list,
)
from smallcase_finance.calc.rebalance import (
    BacktestPath,
    RebalanceResult,
    RebalanceTrade,
    backtest_rebalance_vs_buyhold,
    rebalance_weights,
)
from smallcase_finance.calc.returns import (
    contribution_by_symbol,
    portfolio_return,
    portfolio_returns,
    residual_contribution,
    simple_returns,
    total_return_from_prices,
)
from smallcase_finance.calc.risk import (
    DEFAULT_RF,
    PERIODS_PER_YEAR,
    calmar,
    cagr,
    downside_deviation,
    max_drawdown,
    metrics_from_nav,
    sharpe,
    sharpe_from_returns,
    sortino,
    summary_metrics,
    total_return,
    volatility,
)
from smallcase_finance.calc.sip_schedule import (
    next_session_on_or_after,
    next_trading_day,
    sip_invest_dates,
    sip_schedule,
)
from smallcase_finance.calc.sip_sim import (
    MarketValuePoint,
    SipBuyEvent,
    SipSimulationResult,
    allocate_sip_buy,
    run_sip_simulation,
    symbol_contribution,
)
from smallcase_finance.calc.weights import normalize_weights, weight_drift, weights_sum
from smallcase_finance.calc.xirr import DAYS_PER_YEAR, Cashflow, npv, xirr, year_fraction

__all__ = [
    "DEFAULT_RF",
    "DAYS_PER_YEAR",
    "PERIODS_PER_YEAR",
    "BacktestPath",
    "Cashflow",
    "MarketValuePoint",
    "RebalanceResult",
    "RebalanceTrade",
    "SipBuyEvent",
    "SipSimulationResult",
    "active_weights_on",
    "allocate_sip_buy",
    "backtest_rebalance_vs_buyhold",
    "build_nav_from_prices",
    "calmar",
    "cagr",
    "contribution_by_symbol",
    "cum_return_from_nav",
    "downside_deviation",
    "max_drawdown",
    "metrics_from_nav",
    "nav_from_returns",
    "nav_series_from_price_list",
    "next_session_on_or_after",
    "next_trading_day",
    "normalize_weights",
    "npv",
    "portfolio_return",
    "portfolio_returns",
    "rebalance_weights",
    "residual_contribution",
    "run_sip_simulation",
    "sharpe",
    "sharpe_from_returns",
    "simple_returns",
    "sip_invest_dates",
    "sip_schedule",
    "sortino",
    "summary_metrics",
    "symbol_contribution",
    "total_return",
    "total_return_from_prices",
    "volatility",
    "weight_drift",
    "weights_sum",
    "xirr",
    "year_fraction",
]
