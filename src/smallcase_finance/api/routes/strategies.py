"""GET /strategies — list and detail for file-backed SIP strategies."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from smallcase_finance.api.deps import get_strategy_service
from smallcase_finance.data_access.price_panel import list_curated_symbols
from smallcase_finance.schemas.sip import StrategyDetailResponse, StrategyListResponse
from smallcase_finance.services.strategy_service import StrategyNotFound, StrategyService
from smallcase_finance.strategies.loader import StrategyConfigError

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _http_for(exc: Exception) -> HTTPException:
    if isinstance(exc, StrategyNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (StrategyConfigError, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


class PriceUniverseResponse(BaseModel):
    """Symbols available in curated prices for on-platform basket authoring."""

    symbols: list[str] = Field(description="Distinct symbols in prices.parquet")
    count: int
    hint: str


class PriceCoverageResponse(BaseModel):
    requested: list[str]
    available: list[str]
    missing: list[str]


@router.get("", response_model=StrategyListResponse)
def list_strategies(
    svc: StrategyService = Depends(get_strategy_service),
) -> StrategyListResponse:
    """List strategies under ``config/strategies/*.yaml|json``."""
    try:
        return svc.list_strategies()
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/meta/price-universe", response_model=PriceUniverseResponse)
def price_universe() -> PriceUniverseResponse:
    """Symbols present in curated Parquet (for create-basket UI)."""
    symbols = list_curated_symbols()
    if symbols:
        hint = (
            "Use these symbols for SIP Lab create-basket demos. "
            "For new NSE names: make sync-upstox SYMBOLS=… with UPSTOX_ACCESS_TOKEN."
        )
    else:
        hint = (
            "No curated prices. Run make pipeline or make sync-upstox first."
        )
    return PriceUniverseResponse(symbols=symbols, count=len(symbols), hint=hint)


@router.get("/meta/price-coverage", response_model=PriceCoverageResponse)
def price_coverage(
    symbols: str = Query(
        ...,
        description="Comma-separated symbols to check against curated prices",
    ),
) -> PriceCoverageResponse:
    """Which requested symbols have curated history."""
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    have = set(list_curated_symbols())
    available = [s for s in requested if s in have]
    missing = [s for s in requested if s not in have]
    return PriceCoverageResponse(
        requested=requested,
        available=available,
        missing=missing,
    )


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
def get_strategy(
    strategy_id: str,
    svc: StrategyService = Depends(get_strategy_service),
) -> StrategyDetailResponse:
    """Full validated strategy config for ``strategy_id``."""
    try:
        return svc.get_strategy(strategy_id)
    except Exception as exc:
        raise _http_for(exc) from exc
