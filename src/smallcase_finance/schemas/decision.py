"""Decision Lab API DTOs — orchestrate SIP + benchmark + weight gap."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

WEIGHT_SUM_TOL = 1e-6


class DecisionConstituent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    target_weight: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def upper_symbol(self) -> DecisionConstituent:
        s = self.symbol.strip().upper()
        if not s:
            raise ValueError("symbol must be non-empty")
        object.__setattr__(self, "symbol", s)
        return self


class DecisionBasket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["custom_weights", "equal_weight"] = "equal_weight"
    constituents: list[DecisionConstituent] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_basket(self) -> DecisionBasket:
        symbols = [c.symbol for c in self.constituents]
        if len(symbols) != len(set(symbols)):
            raise ValueError("basket symbols must be unique")
        if self.mode == "custom_weights":
            if any(c.target_weight is None for c in self.constituents):
                raise ValueError(
                    "custom_weights requires target_weight on every constituent"
                )
            total = sum(float(c.target_weight or 0) for c in self.constituents)
            if abs(total - 1.0) > WEIGHT_SUM_TOL:
                raise ValueError(
                    f"target weights must sum to 1.0 ± {WEIGHT_SUM_TOL} (got {total})"
                )
        return self


class DecisionSipParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float = Field(gt=0, default=10000)
    day_of_month: int = Field(ge=1, le=28, default=1)
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def date_order(self) -> DecisionSipParams:
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        return self


class DecisionRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basket: DecisionBasket
    sip: DecisionSipParams
    benchmark_symbol: Optional[str] = Field(
        default=None,
        description="Defaults to DEFAULT_BENCHMARK_SYMBOL (e.g. NIFTYBEES)",
    )
    include_benchmark: bool = True
    include_weight_gap: bool = True
    strict_market_data: Optional[bool] = Field(
        default=None,
        description="Override STRICT_MARKET_DATA env; null = use env default",
    )


class SymbolCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    has_prices: bool
    start: Optional[date] = None
    end: Optional[date] = None


class PriceCoverageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_source: str
    symbols: list[SymbolCoverage] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basket_symbols: int = 0
    basket_with_prices: int = 0
    benchmark_ok: bool = False
    missing_symbols: list[str] = Field(default_factory=list)
    price_start: Optional[date] = None
    price_end: Optional[date] = None


class DecisionSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    market_value: float
    invested_cum: float = 0.0


class DecisionLegResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[str] = None
    xirr: Optional[float] = None
    total_invested: float = 0.0
    final_value: float = 0.0
    max_drawdown: Optional[float] = None
    series: list[DecisionSeriesPoint] = Field(default_factory=list)
    cashflows_summary: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class WeightGapRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    portfolio_weight: float = 0.0
    target_weight: float = 0.0
    delta_weight: float = 0.0
    approx_value_delta: Optional[float] = None


class DecisionRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    data_source: str
    coverage: CoverageSummary
    warnings: list[str] = Field(default_factory=list)
    candidate: DecisionLegResult
    benchmark: Optional[DecisionLegResult] = None
    delta_xirr: Optional[float] = None
    weight_gap: list[WeightGapRow] = Field(default_factory=list)
    disclaimer: str = (
        "Zero transaction costs. Not investment advice. Execute trades manually on Kite."
    )
