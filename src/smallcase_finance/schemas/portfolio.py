"""Portfolio of record (Kite equity holdings) API DTOs — Portfolio Decision v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PortfolioHoldingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    exchange: str = ""
    quantity: float
    average_price: Optional[float] = None
    last_price: Optional[float] = None
    value: Optional[float] = None
    weight: Optional[float] = Field(
        default=None,
        description="Fraction of total_value in [0, 1]",
    )
    pnl: Optional[float] = None
    product: Optional[str] = None
    isin: Optional[str] = None
    instrument_token: Optional[int] = None
    sector: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Latest equity book snapshot."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    synced_at: datetime
    source: str = "kite"
    currency: str = "INR"
    total_value: Optional[float] = None
    position_count: int = 0
    holdings: list[PortfolioHoldingItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PortfolioStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kite_app_configured: bool
    kite_session_configured: bool
    login_url: Optional[str] = None
    has_snapshot: bool = False
    latest_synced_at: Optional[datetime] = None
    position_count: int = 0
    total_value: Optional[float] = None
    currency: str = "INR"
    message: str = ""


class PortfolioSymbolsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: list[str] = Field(default_factory=list)
    synced_at: Optional[datetime] = None


class ApiErrorBody(BaseModel):
    """Structured error payload (optional use in detail)."""

    model_config = ConfigDict(extra="forbid")

    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
