"""Summary risk/return metrics API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from smallcase_finance.schemas.common import MetricsAssumptions, MetricWindow


class MetricValues(BaseModel):
    """Ratios as decimals (0.142 = 14.2%); max_drawdown is negative."""

    model_config = ConfigDict(extra="forbid")

    cagr: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = Field(
        default=None,
        description="Negative fraction, e.g. -0.27 = −27%",
    )
    sharpe: Optional[float] = None
    total_return: Optional[float] = None
    n_observations: Optional[int] = None


class MetricsResponse(BaseModel):
    """GET /smallcases/{id}/metrics."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    start: Optional[date] = None
    end: Optional[date] = None
    window: MetricWindow = MetricWindow.itd
    currency: str = "INR"
    metrics: MetricValues
    assumptions: MetricsAssumptions
