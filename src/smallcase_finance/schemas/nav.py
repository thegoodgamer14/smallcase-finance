"""NAV series / latest-point API DTOs."""

from __future__ import annotations

from datetime import date
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class NavPointDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    nav: float


class NavSeriesResponse(BaseModel):
    """GET /smallcases/{id}/nav with latest_only=false."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    currency: str = "INR"
    series: list[NavPointDTO]


class NavLatestResponse(BaseModel):
    """GET /smallcases/{id}/nav with latest_only=true."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    currency: str = "INR"
    as_of: date
    nav: float
