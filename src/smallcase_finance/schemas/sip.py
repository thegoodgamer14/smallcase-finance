"""SIP Lab request/response DTOs (service + HTTP API).

Primary metric is XIRR. ``data_source`` must be surfaced so UI can banner
demo (sample) vs Upstox-backed runs (ADR 005).

API surface (P2):
- ``GET /strategies`` / ``GET /strategies/{id}``
- ``POST /backtests/sip``  (not ``POST /backtest`` rebalance)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Service-level result fragments ───────────────────────────────────────────


class SipCashflowDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    amount: float = Field(description="Signed: contribution < 0, terminal > 0")
    kind: str = Field(description="contribution | terminal | redemption")


class SipMarketValueDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    market_value: float
    total_invested_to_date: float = 0.0
    has_sip: bool = False


class SipSymbolContributionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    cash_in: float
    units_end: float
    price_end: Optional[float] = None
    market_value_end: float
    contribution: float
    weight_end: Optional[float] = None


class SipMetricsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_invested: float
    final_value: float
    absolute_gain: float
    n_sips: int
    first_sip: Optional[date] = None
    last_sip: Optional[date] = None
    as_of: Optional[date] = None
    max_drawdown: Optional[float] = None
    volatility: Optional[float] = None
    cagr_mv: Optional[float] = Field(
        default=None,
        description="CAGR of MV path only — not cashflow-aware; do not replace XIRR",
    )
    xirr_status: str = "undefined"
    xirr_message: Optional[str] = None
    xirr_day_count: str = "ACT/365.25"


class SipRunResult(BaseModel):
    """Service-level SIP backtest result (maps cleanly to POST /backtests/sip)."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    name: Optional[str] = None
    xirr: Optional[float] = Field(
        default=None,
        description="Primary annualized rate (decimal). Golden abs tol 1e-4.",
    )
    data_source: str = Field(
        description="upstox | sample | fixture | mixed | unknown",
    )
    invest_dates: list[date] = Field(default_factory=list)
    cashflows: list[SipCashflowDTO] = Field(default_factory=list)
    market_value: list[SipMarketValueDTO] = Field(default_factory=list)
    units_end: dict[str, float] = Field(default_factory=dict)
    metrics: SipMetricsDTO
    contribution: list[SipSymbolContributionDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    notes: str = (
        "Monthly SIP cashflow path; primary metric is XIRR. "
        "Zero costs MVP. Not the v0 weight-NAV rebalance backtest."
    )


# ── Strategy list / detail (GET /strategies) ─────────────────────────────────


class StrategySummary(BaseModel):
    """List-card fields for a file-backed strategy under config/strategies/."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="strategy_id slug")
    name: str
    summary: Optional[str] = Field(
        default=None,
        description="Short description (from notes, truncated)",
    )
    currency: str = "INR"
    sip_amount: float
    day_of_month: int
    start_date: date
    end_date: Optional[date] = None
    allocation_mode: str = "custom_weights"
    n_constituents: Optional[int] = None
    version: str = "1"


class StrategyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[StrategySummary]


class StrategyDetailResponse(BaseModel):
    """Full validated strategy config plus file metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    currency: str = "INR"
    version: str = "1"
    notes: Optional[str] = None
    allocation_mode: str
    price_field: str = "close"
    rebalance_mode: str = "none"
    fractional_units: bool = True
    basket: dict[str, Any]
    sip: dict[str, Any]
    costs: dict[str, Any] = Field(default_factory=dict)
    source_path: Optional[str] = Field(
        default=None,
        description="Relative path of the strategy file (no secrets).",
    )


# ── POST /backtests/sip ──────────────────────────────────────────────────────


class SipBacktestRequest(BaseModel):
    """Run a monthly SIP backtest.

    Provide ``strategy_id`` (file under config/strategies/) and/or a full
    inline ``strategy`` payload. Optional overrides apply on top of the
    resolved strategy (amount, day_of_month, start, end, as_of).
    """

    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(
        default=None,
        description="Load strategy from config/strategies/{id}.yaml|.json",
    )
    strategy: Optional[dict[str, Any]] = Field(
        default=None,
        description="Inline StrategyConfig-compatible object (alternative to strategy_id)",
    )
    amount: Optional[float] = Field(
        default=None,
        gt=0,
        description="Override monthly SIP amount",
    )
    day_of_month: Optional[int] = Field(
        default=None,
        ge=1,
        le=28,
        description="Override SIP calendar day (1–28)",
    )
    start: Optional[date] = Field(
        default=None,
        description="Override SIP schedule start_date",
    )
    end: Optional[date] = Field(
        default=None,
        description="Override SIP schedule end_date (null = through last price)",
    )
    as_of: Optional[date] = Field(
        default=None,
        description="Override terminal valuation date",
    )

    @model_validator(mode="after")
    def require_strategy_source(self) -> SipBacktestRequest:
        if not self.strategy_id and not self.strategy:
            raise ValueError("provide strategy_id and/or strategy (inline config)")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be <= end")
        if self.as_of is not None and self.start is not None and self.as_of < self.start:
            raise ValueError("as_of must be >= start when both are set")
        return self


class SipAssumptions(BaseModel):
    """Methodology flags for UI accordion / audit footer."""

    model_config = ConfigDict(extra="forbid")

    primary_metric: str = "xirr"
    sip_day_rule: str = (
        "fixed calendar day-of-month → next trading day if market closed"
    )
    costs: str = "zero"
    costs_zero: bool = True
    price_field: str = "close"
    xirr_day_count: str = "ACT/365.25"
    fractional_units: bool = True
    currency: str = "INR"
    rebalance_mode: str = "none"
    not_v0_rebalance: bool = Field(
        default=True,
        description="True: this is the cashflow SIP path, not POST /backtest NAV",
    )


class SipSeriesPoint(BaseModel):
    """Daily (or session) market-value path for charts."""

    model_config = ConfigDict(extra="forbid")

    date: date
    market_value: float
    total_invested_to_date: float = 0.0
    has_sip: bool = False


class SipBacktestResponse(BaseModel):
    """POST /backtests/sip result — primary metric is XIRR."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    name: Optional[str] = None
    xirr: Optional[float] = Field(
        default=None,
        description="Primary annualized rate (decimal). Golden abs tol 1e-4.",
    )
    total_invested: float
    final_value: float
    max_drawdown: Optional[float] = Field(
        default=None,
        description="Negative fraction (e.g. -0.12)",
    )
    absolute_gain: Optional[float] = None
    n_sips: int = 0
    series: list[SipSeriesPoint] = Field(default_factory=list)
    cashflows: list[SipCashflowDTO] = Field(default_factory=list)
    data_source: str = Field(
        description="upstox | sample | fixture | mixed | unknown",
    )
    assumptions: SipAssumptions
    warnings: list[str] = Field(default_factory=list)
    invest_dates: list[date] = Field(default_factory=list)
    units_end: dict[str, float] = Field(default_factory=dict)
    contribution: list[SipSymbolContributionDTO] = Field(default_factory=list)
    metrics: Optional[SipMetricsDTO] = None
    notes: str = (
        "Monthly SIP cashflow path; primary metric is XIRR. "
        "Zero costs MVP. Not the v0 weight-NAV rebalance backtest."
    )
