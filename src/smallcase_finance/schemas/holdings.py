"""Holdings / composition API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HoldingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: Optional[str] = None
    weight: float = Field(ge=0, le=1, description="Fraction in [0, 1], not percent")
    sector: Optional[str] = None


class HoldingsResponse(BaseModel):
    """GET /smallcases/{id}/holdings — target constituents as of a date."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    as_of: date
    effective_from: Optional[date] = None
    methodology: Optional[str] = None
    holdings: list[HoldingItem]
    weight_sum: float
