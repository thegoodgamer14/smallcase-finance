"""POST /backtest — pure rebalance simulation over curated prices."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from smallcase_finance.api.deps import get_backtest_service
from smallcase_finance.data_access.exceptions import (
    CuratedDataUnavailable,
    SmallcaseNotFound,
)
from smallcase_finance.schemas.backtest import BacktestRequest, BacktestResponse
from smallcase_finance.services.backtest_service import BacktestService

router = APIRouter(tags=["backtest"])


def _http_for(exc: Exception) -> HTTPException:
    if isinstance(exc, SmallcaseNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CuratedDataUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/backtest", response_model=BacktestResponse)
def run_backtest(
    body: BacktestRequest,
    svc: BacktestService = Depends(get_backtest_service),
) -> BacktestResponse:
    """Simulate periodic rebalance vs buy-and-hold; does not write curated data."""
    if body.start is not None and body.end is not None and body.start > body.end:
        raise HTTPException(status_code=400, detail="start must be <= end")
    try:
        return svc.run(body)
    except Exception as exc:
        raise _http_for(exc) from exc
