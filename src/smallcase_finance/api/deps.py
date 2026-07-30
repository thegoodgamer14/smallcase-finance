"""Shared FastAPI dependencies (services / paths)."""

from __future__ import annotations

from pathlib import Path

from smallcase_finance.config import DATA_CURATED_ROOT
from smallcase_finance.services.backtest_service import BacktestService
from smallcase_finance.services.metrics_service import MetricsService
from smallcase_finance.services.performance_service import NavService, PerformanceService
from smallcase_finance.services.decision_service import DecisionService
from smallcase_finance.services.portfolio_service import PortfolioService
from smallcase_finance.services.sip_service import SipService
from smallcase_finance.services.smallcase_service import SmallcaseService
from smallcase_finance.services.strategy_service import StrategyService


def get_curated_root() -> Path:
    return DATA_CURATED_ROOT


def get_smallcase_service() -> SmallcaseService:
    return SmallcaseService()


def get_performance_service() -> PerformanceService:
    return PerformanceService()


def get_nav_service() -> NavService:
    return NavService()


def get_metrics_service() -> MetricsService:
    return MetricsService()


def get_backtest_service() -> BacktestService:
    return BacktestService()


def get_sip_service() -> SipService:
    return SipService()


def get_strategy_service() -> StrategyService:
    return StrategyService()


def get_portfolio_service() -> PortfolioService:
    return PortfolioService()


def get_decision_service() -> DecisionService:
    return DecisionService()
