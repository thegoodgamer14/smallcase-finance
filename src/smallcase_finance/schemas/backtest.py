"""Backtest / rebalance simulation request & response DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from smallcase_finance.schemas.metrics import MetricValues
from smallcase_finance.schemas.nav import NavPointDTO


class BacktestRequest(BaseModel):
    """POST /backtest body."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    start: Optional[date] = None
    end: Optional[date] = None
    rebalance_rule: Optional[str] = Field(
        default=None,
        description="Override smallcase rebalance_rule (monthly|quarterly|manual|none|threshold_5pct)",
    )
    methodology: Optional[str] = Field(
        default=None,
        description="Override methodology (equal_weight|custom_weights|…)",
    )
    initial_nav: float = Field(default=100.0, gt=0)
    threshold: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="One-way turnover threshold; skip rebalance if below",
    )


class BacktestParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rebalance_rule: str
    methodology: str
    rebalance_every: int
    threshold: Optional[float] = None
    initial_nav: float = 100.0
    start: Optional[date] = None
    end: Optional[date] = None


class RebalanceEventDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    turnover: float = Field(ge=0, description="One-way turnover at this rebalance")


class BacktestResponse(BaseModel):
    """POST /backtest result — pure simulation, no curated writes."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    params: BacktestParams
    metrics: MetricValues
    nav_series: list[NavPointDTO]
    rebalance_events: list[RebalanceEventDTO]
    buy_hold_metrics: Optional[MetricValues] = None
    notes: str = (
        "In-memory simulation over curated prices; no transaction costs; "
        "does not write curated Parquet."
    )
