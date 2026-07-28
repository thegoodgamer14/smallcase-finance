"""Performance series API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PerformancePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    nav: float
    daily_return: Optional[float] = None


class PerformanceResponse(BaseModel):
    """GET /smallcases/{id}/performance."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    currency: str = "INR"
    start: Optional[date] = None
    end: Optional[date] = None
    series: list[PerformancePoint]
    benchmark_series: Optional[list[PerformancePoint]] = None
