"""SIP Lab strategy / SIP configuration contracts (Pydantic).

Binding product rules (ADR 004 / sip-engine.md):
- day_of_month ∈ [1, 28]
- sip amount > 0
- equity/ETF symbols only (no MF schemes this version)
- custom_weights must sum ≈ 1.0 (tol 1e-6)
- costs default to zero for MVP

Authoring: nested ``sip: SIPConfig`` (YAML/JSON) or flat fields
(``sip_amount``, ``day_of_month``, …) matching the data dictionary.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

WEIGHT_SUM_TOL = 1e-6

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EXCHANGE_SUFFIX_RE = re.compile(r"\.(NS|BO|NSE|BSE)$", re.IGNORECASE)


class AllocationMode(str, Enum):
    custom_weights = "custom_weights"
    equal_weight = "equal_weight"


class RebalanceMode(str, Enum):
    none = "none"
    on_sip = "on_sip"
    monthly = "monthly"
    quarterly = "quarterly"


class PriceField(str, Enum):
    close = "close"
    adj_close = "adj_close"


class CostConfig(BaseModel):
    """Friction model. MVP: all zeros (binding default)."""

    model_config = ConfigDict(extra="forbid")

    brokerage_bps: float = Field(default=0.0, ge=0)
    stt_bps: float = Field(default=0.0, ge=0)
    slippage_bps: float = Field(default=0.0, ge=0)
    flat_fee: float = Field(default=0.0, ge=0)


class BasketConstituent(BaseModel):
    """One equity/ETF line in an inline basket."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    target_weight: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("symbol must be non-empty")
        if _EXCHANGE_SUFFIX_RE.search(s):
            raise ValueError(
                f"symbol {v!r} must not include exchange suffix "
                "(use bare ticker, e.g. INFY not INFY.NS)"
            )
        if " " in s or "/" in s:
            raise ValueError(f"symbol {v!r} looks invalid for equity/ETF ticker")
        return s


class SmallcaseRefBasket(BaseModel):
    """Reference an existing local smallcase definition."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["smallcase_ref"] = "smallcase_ref"
    smallcase_id: str = Field(min_length=1)

    @field_validator("smallcase_id")
    @classmethod
    def strip_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("smallcase_id must be non-empty")
        return s


class InlineBasket(BaseModel):
    """Inline constituents (authoring path for custom SIP baskets)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["inline"] = "inline"
    constituents: list[BasketConstituent] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_symbols(self) -> InlineBasket:
        symbols = [c.symbol for c in self.constituents]
        if len(symbols) != len(set(symbols)):
            raise ValueError("inline basket symbols must be unique")
        return self


BasketConfig = Annotated[
    Union[SmallcaseRefBasket, InlineBasket],
    Field(discriminator="kind"),
]


class SIPConfig(BaseModel):
    """Monthly SIP schedule: fixed calendar day → next trading session (engine)."""

    model_config = ConfigDict(extra="forbid")

    amount: float = Field(
        gt=0,
        description="Monthly contribution in portfolio currency units (e.g. INR).",
    )
    day_of_month: int = Field(
        ge=1,
        le=28,
        description="Calendar day 1–28 (MVP; avoids month-end / Feb 29 ambiguity).",
    )
    start_date: date = Field(description="First month bound for SIP schedule (inclusive).")
    end_date: Optional[date] = Field(
        default=None,
        description="Last month bound; null = through last usable price date.",
    )
    as_of: Optional[date] = Field(
        default=None,
        description="Terminal valuation date override; null = last usable session.",
    )

    @model_validator(mode="after")
    def date_order(self) -> SIPConfig:
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date when both are set")
        if self.as_of is not None and self.as_of < self.start_date:
            raise ValueError("as_of must be >= start_date when set")
        return self


class StrategyConfig(BaseModel):
    """Full SIP Lab strategy definition (basket + allocation + SIP schedule)."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(description="Stable slug PK; lowercase kebab-case.")
    name: str = Field(min_length=1)
    currency: str = "INR"
    basket: BasketConfig
    allocation_mode: AllocationMode = AllocationMode.custom_weights
    sip: SIPConfig
    price_field: PriceField = PriceField.close
    rebalance_mode: RebalanceMode = RebalanceMode.none
    fractional_units: bool = True
    costs: CostConfig = Field(default_factory=CostConfig)
    version: str = "1"
    notes: Optional[str] = None
    created_at: Optional[str] = Field(
        default=None,
        description="Optional authoring timestamp (ISO string).",
    )

    @field_validator("strategy_id")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        s = v.strip().lower()
        if not _SLUG_RE.match(s):
            raise ValueError(
                "strategy_id must be lowercase kebab-case "
                f"(got {v!r})"
            )
        return s

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name must be non-empty")
        return s

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise ValueError("currency must be non-empty")
        return s

    @model_validator(mode="after")
    def validate_weights_for_mode(self) -> StrategyConfig:
        if not isinstance(self.basket, InlineBasket):
            return self

        weights = [c.target_weight for c in self.basket.constituents]
        if self.allocation_mode == AllocationMode.custom_weights:
            if any(w is None for w in weights):
                raise ValueError(
                    "allocation_mode=custom_weights requires target_weight "
                    "on every inline constituent"
                )
            total = sum(w for w in weights if w is not None)
            if abs(total - 1.0) > WEIGHT_SUM_TOL:
                raise ValueError(
                    f"inline target weights must sum to 1.0 ± {WEIGHT_SUM_TOL} "
                    f"(got {total})"
                )
        # equal_weight: provided weights are ignored by the engine
        return self

    # ── Convenience accessors (engine / API helpers) ──────────────────────

    @property
    def sip_amount(self) -> float:
        return self.sip.amount

    @property
    def day_of_month(self) -> int:
        return self.sip.day_of_month

    @property
    def start_date(self) -> date:
        return self.sip.start_date

    @property
    def end_date(self) -> Optional[date]:
        return self.sip.end_date

    @property
    def as_of(self) -> Optional[date]:
        return self.sip.as_of

    def resolved_weights(self) -> dict[str, float]:
        """Target weights for an inline basket (raises for smallcase_ref).

        equal_weight → 1/n; custom_weights → declared targets.
        """
        if not isinstance(self.basket, InlineBasket):
            raise ValueError(
                "resolved_weights() requires basket.kind=inline; "
                "resolve smallcase_ref constituents from curated data"
            )
        n = len(self.basket.constituents)
        if self.allocation_mode == AllocationMode.equal_weight:
            w = 1.0 / n
            return {c.symbol: w for c in self.basket.constituents}
        return {
            c.symbol: float(c.target_weight)  # type: ignore[arg-type]
            for c in self.basket.constituents
        }
