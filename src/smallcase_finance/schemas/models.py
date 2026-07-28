"""Implementable domain / curated-table contracts for v0.

Canonical field names, grains, and validation match docs/data-dictionary.md.
Data Engineer: validate rows with these models before writing Parquet.
Backend: map domain rows → API DTOs in sibling schema modules (not here).

Requires: pydantic >= 2.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums (preferred values; free-text still allowed on some string fields)
# ---------------------------------------------------------------------------

WEIGHT_SUM_TOL = 1e-6


class HoldingsSource(str, Enum):
    target = "target"
    broker = "broker"
    reconstructed = "reconstructed"


class MetricWindow(str, Enum):
    m1 = "1M"
    m3 = "3M"
    m6 = "6M"
    y1 = "1Y"
    ytd = "YTD"
    itd = "ITD"
    custom = "custom"


class Methodology(str, Enum):
    equal_weight = "equal_weight"
    market_cap_weight = "market_cap_weight"
    custom_weights = "custom_weights"
    factor_score = "factor_score"


class RebalanceRule(str, Enum):
    none = "none"
    monthly = "monthly"
    quarterly = "quarterly"
    threshold_5pct = "threshold_5pct"
    manual = "manual"


# ---------------------------------------------------------------------------
# Curated table row models (1:1 with Parquet columns)
# ---------------------------------------------------------------------------


class Instrument(BaseModel):
    """Master instrument — PK: symbol."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    currency: str = "INR"
    isin: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("symbol must be non-empty")
        return s


class PriceBar(BaseModel):
    """Daily price — PK: (symbol, date)."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    date: date
    close: float = Field(gt=0)
    open: Optional[float] = Field(default=None, gt=0)
    high: Optional[float] = Field(default=None, gt=0)
    low: Optional[float] = Field(default=None, gt=0)
    volume: Optional[float] = Field(default=None, ge=0)
    adj_close: Optional[float] = Field(default=None, gt=0)
    currency: str = "INR"
    source: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Smallcase(BaseModel):
    """Thematic portfolio definition — PK: smallcase_id."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    name: str
    theme: Optional[str] = None
    description: Optional[str] = None
    methodology: str = Methodology.custom_weights.value
    rebalance_rule: str = RebalanceRule.manual.value
    base_nav: float = Field(default=100.0, gt=0)
    currency: str = "INR"
    inception_date: Optional[date] = None
    benchmark_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("smallcase_id")
    @classmethod
    def slug_id(cls, v: str) -> str:
        s = v.strip().lower().replace(" ", "-")
        if not s:
            raise ValueError("smallcase_id must be non-empty")
        return s


class SmallcaseConstituent(BaseModel):
    """Versioned target weight — PK: (smallcase_id, symbol, effective_from)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    symbol: str
    target_weight: float = Field(ge=0, le=1)
    effective_from: date
    effective_to: Optional[date] = None
    version_label: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def check_effective_range(self) -> SmallcaseConstituent:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be >= effective_from")
        if self.target_weight == 0:
            raise ValueError("omit zero-weight symbols; target_weight must be > 0")
        return self


class RebalanceEvent(BaseModel):
    """Rebalance log — PK: (smallcase_id, rebalance_date)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    rebalance_date: date
    reason: Optional[str] = None
    from_effective_from: Optional[date] = None
    to_effective_from: date
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class HoldingsSnapshot(BaseModel):
    """Point-in-time holdings — PK: (smallcase_id, as_of, symbol)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    as_of: date
    symbol: str
    weight: float = Field(ge=0, le=1)
    shares: Optional[float] = None
    market_value: Optional[float] = None
    source: HoldingsSource = HoldingsSource.target

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class NavPoint(BaseModel):
    """Derived daily NAV — PK: (smallcase_id, date)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    date: date
    nav: float = Field(gt=0)
    daily_return: float
    cum_return: Optional[float] = None
    n_constituents: Optional[int] = Field(default=None, ge=0)
    computed_at: datetime


class MetricsSnapshot(BaseModel):
    """Derived risk/return metrics — PK: (smallcase_id, as_of, window)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    as_of: date
    window: MetricWindow
    start_date: date
    end_date: date
    n_obs: int = Field(ge=0)
    total_return: float
    cagr: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    calmar: Optional[float] = None
    rf_rate: Optional[float] = None
    computed_at: datetime

    @model_validator(mode="after")
    def check_window_dates(self) -> MetricsSnapshot:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class Contribution(BaseModel):
    """Derived symbol contribution — PK: (smallcase_id, period_start, period_end, symbol)."""

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    period_start: date
    period_end: date
    symbol: str
    avg_weight: float = Field(ge=0, le=1)
    weight_start: Optional[float] = Field(default=None, ge=0, le=1)
    weight_end: Optional[float] = Field(default=None, ge=0, le=1)
    symbol_return: float
    contribution: float
    computed_at: datetime

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        if v == "_RESIDUAL":
            return v
        return v.strip().upper()

    @model_validator(mode="after")
    def check_period(self) -> Contribution:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be >= period_start")
        return self


# ---------------------------------------------------------------------------
# Raw authoring format — data/raw/smallcases/{smallcase_id}.json
# ---------------------------------------------------------------------------


class DefinitionWeight(BaseModel):
    """One constituent weight inside a definition version."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    target_weight: float = Field(gt=0, le=1)

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class DefinitionVersion(BaseModel):
    """One weight version block in a raw smallcase JSON file."""

    model_config = ConfigDict(extra="forbid")

    effective_from: date
    effective_to: Optional[date] = None
    version_label: Optional[str] = None
    constituents: list[DefinitionWeight] = Field(min_length=1)

    @model_validator(mode="after")
    def check_version(self) -> DefinitionVersion:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be >= effective_from")
        total = sum(c.target_weight for c in self.constituents)
        if abs(total - 1.0) > WEIGHT_SUM_TOL:
            raise ValueError(
                f"constituent weights must sum to 1.0 ± {WEIGHT_SUM_TOL}, got {total}"
            )
        symbols = [c.symbol for c in self.constituents]
        if len(symbols) != len(set(symbols)):
            raise ValueError("duplicate symbols in version constituents")
        return self


class DefinitionRebalanceEvent(BaseModel):
    """Rebalance event inside a raw smallcase JSON file."""

    model_config = ConfigDict(extra="forbid")

    rebalance_date: date
    reason: Optional[str] = None
    from_effective_from: Optional[date] = None
    to_effective_from: date
    notes: Optional[str] = None


class SmallcaseDefinitionFile(BaseModel):
    """Human-authored smallcase definition (raw JSON).

    Path: data/raw/smallcases/{smallcase_id}.json
    Pipeline expands to Smallcase + SmallcaseConstituent + RebalanceEvent rows.
    """

    model_config = ConfigDict(extra="forbid")

    smallcase_id: str
    name: str
    theme: Optional[str] = None
    description: Optional[str] = None
    methodology: str = Methodology.custom_weights.value
    rebalance_rule: str = RebalanceRule.manual.value
    base_nav: float = Field(default=100.0, gt=0)
    currency: str = "INR"
    inception_date: Optional[date] = None
    notes: Optional[str] = None
    versions: list[DefinitionVersion] = Field(min_length=1)
    rebalance_events: list[DefinitionRebalanceEvent] = Field(default_factory=list)

    @field_validator("smallcase_id")
    @classmethod
    def slug_id(cls, v: str) -> str:
        s = v.strip().lower().replace(" ", "-")
        if not s:
            raise ValueError("smallcase_id must be non-empty")
        return s

    def to_smallcase(self, *, created_at: datetime) -> Smallcase:
        """Flatten header fields into a curated Smallcase row."""
        return Smallcase(
            smallcase_id=self.smallcase_id,
            name=self.name,
            theme=self.theme,
            description=self.description,
            methodology=self.methodology,
            rebalance_rule=self.rebalance_rule,
            base_nav=self.base_nav,
            currency=self.currency,
            inception_date=self.inception_date,
            created_at=created_at,
            notes=self.notes,
        )

    def to_constituents(
        self, *, created_at: Optional[datetime] = None
    ) -> list[SmallcaseConstituent]:
        """Expand versions into flat smallcase_constituents rows."""
        rows: list[SmallcaseConstituent] = []
        for ver in self.versions:
            for c in ver.constituents:
                rows.append(
                    SmallcaseConstituent(
                        smallcase_id=self.smallcase_id,
                        symbol=c.symbol,
                        target_weight=c.target_weight,
                        effective_from=ver.effective_from,
                        effective_to=ver.effective_to,
                        version_label=ver.version_label,
                        created_at=created_at,
                    )
                )
        return rows

    def to_rebalance_events(
        self, *, created_at: Optional[datetime] = None
    ) -> list[RebalanceEvent]:
        """Map definition rebalance_events to curated rows."""
        return [
            RebalanceEvent(
                smallcase_id=self.smallcase_id,
                rebalance_date=ev.rebalance_date,
                reason=ev.reason,
                from_effective_from=ev.from_effective_from,
                to_effective_from=ev.to_effective_from,
                notes=ev.notes,
                created_at=created_at,
            )
            for ev in self.rebalance_events
        ]


# ---------------------------------------------------------------------------
# Helpers for pipeline validation
# ---------------------------------------------------------------------------


def assert_weight_sum(
    rows: list[SmallcaseConstituent],
    *,
    smallcase_id: str,
    effective_from: date,
    tol: float = WEIGHT_SUM_TOL,
) -> None:
    """Raise ValueError if weights for a version do not sum to ~1.0."""
    subset = [
        r
        for r in rows
        if r.smallcase_id == smallcase_id and r.effective_from == effective_from
    ]
    if not subset:
        raise ValueError(
            f"no constituents for {smallcase_id} effective_from={effective_from}"
        )
    total = sum(r.target_weight for r in subset)
    if abs(total - 1.0) > tol:
        raise ValueError(
            f"weights for {smallcase_id}@{effective_from} sum to {total}, expected 1.0±{tol}"
        )


# Public surface for `from smallcase_finance.schemas.models import *` style
__all__ = [
    "WEIGHT_SUM_TOL",
    "HoldingsSource",
    "MetricWindow",
    "Methodology",
    "RebalanceRule",
    "Instrument",
    "PriceBar",
    "Smallcase",
    "SmallcaseConstituent",
    "RebalanceEvent",
    "HoldingsSnapshot",
    "NavPoint",
    "MetricsSnapshot",
    "Contribution",
    "DefinitionWeight",
    "DefinitionVersion",
    "DefinitionRebalanceEvent",
    "SmallcaseDefinitionFile",
    "assert_weight_sum",
]
