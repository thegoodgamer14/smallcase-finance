"""Shared API response fragments and query enums."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricWindow(str, Enum):
    """Windows aligned with curated ``metrics_snapshot.window``."""

    m1 = "1M"
    m3 = "3M"
    m6 = "6M"
    y1 = "1Y"
    ytd = "YTD"
    itd = "ITD"
    custom = "custom"


class SeriesFreq(str, Enum):
    daily = "D"
    weekly = "W"
    monthly = "M"


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    version: str
    data_curated_root: str
    data_reachable: bool


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


class MetricsAssumptions(BaseModel):
    """Always present so UI tooltips stay honest about metric definitions."""

    model_config = ConfigDict(extra="forbid")

    periods_per_year: int = 252
    risk_free_rate: float = 0.0
    return_type: str = "simple"
    price_field: str = "close"


class DateRangeParams(BaseModel):
    """Optional inclusive date window (validated in routers/services)."""

    model_config = ConfigDict(extra="forbid")

    start: Optional[date] = None
    end: Optional[date] = None

    def assert_order(self) -> None:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be <= end")
