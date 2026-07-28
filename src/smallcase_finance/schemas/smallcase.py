"""Smallcase list / detail API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SmallcaseListItem(BaseModel):
    """One row in GET /smallcases."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="smallcase_id slug")
    name: str
    description: Optional[str] = None
    theme: Optional[str] = None
    currency: str = "INR"
    methodology: str
    rebalance_rule: str
    inception_date: Optional[date] = None
    as_of: Optional[date] = Field(
        default=None,
        description="Latest holdings/NAV as-of when known",
    )
    constituent_count: Optional[int] = Field(
        default=None,
        description="Count of active constituents at as_of (or latest version)",
    )


class SmallcaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SmallcaseListItem]


class SmallcaseDetail(BaseModel):
    """GET /smallcases/{id}."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: Optional[str] = None
    theme: Optional[str] = None
    currency: str = "INR"
    methodology: str
    rebalance_rule: str
    base_nav: float = 100.0
    inception_date: Optional[date] = None
    benchmark_id: Optional[str] = None
    notes: Optional[str] = None
