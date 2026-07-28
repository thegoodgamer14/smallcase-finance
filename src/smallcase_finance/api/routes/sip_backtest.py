"""POST /backtests/sip — monthly SIP cashflow backtest (XIRR primary).

Separate from v0 ``POST /backtest`` (weight-NAV rebalance simulation).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from smallcase_finance.api.deps import get_sip_service, get_strategy_service
from smallcase_finance.data_access.exceptions import CuratedDataUnavailable
from smallcase_finance.schemas.sip import SipBacktestRequest, SipBacktestResponse
from smallcase_finance.services.sip_service import SipService, SipServiceError
from smallcase_finance.services.strategy_service import StrategyNotFound, StrategyService
from smallcase_finance.strategies.loader import StrategyConfigError
from smallcase_finance.strategies.models import StrategyConfig

router = APIRouter(tags=["sip"])


def _http_for(exc: Exception) -> HTTPException:
    if isinstance(exc, StrategyNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CuratedDataUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (SipServiceError, StrategyConfigError, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/backtests/sip", response_model=SipBacktestResponse)
def run_sip_backtest(
    body: SipBacktestRequest,
    sip_svc: SipService = Depends(get_sip_service),
    strategy_svc: StrategyService = Depends(get_strategy_service),
) -> SipBacktestResponse:
    """Run monthly SIP over curated prices; primary metric is XIRR.

    Costs are zero (MVP). SIP day = fixed calendar day → next trading session.
    ``data_source`` labels sample/demo vs Upstox. Not the v0 rebalance backtest.
    """
    try:
        cfg: Optional[StrategyConfig] = None
        if body.strategy_id:
            # File-backed strategy under config/strategies/
            cfg = strategy_svc.load_config(body.strategy_id)
        # else: SipService parses body.strategy inline config
        return sip_svc.run_request(body, strategy_config=cfg)
    except Exception as exc:
        raise _http_for(exc) from exc
