"""GET /strategies — list and detail for file-backed SIP strategies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from smallcase_finance.api.deps import get_strategy_service
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


@router.get("", response_model=StrategyListResponse)
def list_strategies(
    svc: StrategyService = Depends(get_strategy_service),
) -> StrategyListResponse:
    """List strategies under ``config/strategies/*.yaml|json``."""
    try:
        return svc.list_strategies()
    except Exception as exc:
        raise _http_for(exc) from exc


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
