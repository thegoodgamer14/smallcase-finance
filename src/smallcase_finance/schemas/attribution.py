"""Attribution / contribution API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AttributionItem(BaseModel):
    """One symbol's contribution over a period (fractions, not percent)."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: Optional[str] = None
    avg_weight: float = Field(ge=0, le=1)
    weight_start: Optional[float] = Field(default=None, ge=0, le=1)
    weight_end: Optional[float] = Field(default=None, ge=0, le=1)
    symbol_return: float
    contribution: float


class AttributionResponse(BaseModel):
    """GET /smallcases/{id}/attribution — simple weight × return contribution."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    items: list[AttributionItem]
    residual: Optional[float] = Field(
        default=None,
        description="Portfolio return minus sum of symbol contributions, if known",
    )
    portfolio_return: Optional[float] = None
    notes: str = (
        "Simple single-period contribution (avg_weight × symbol_return); "
        "not multi-period Brinson attribution."
    )
