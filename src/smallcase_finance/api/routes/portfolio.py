"""Portfolio of record (Kite equity holdings) routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from smallcase_finance.api.deps import get_portfolio_service
from smallcase_finance.schemas.portfolio import (
    PortfolioResponse,
    PortfolioStatusResponse,
    PortfolioSymbolsResponse,
)
from smallcase_finance.services.portfolio_service import (
    PortfolioService,
    PortfolioServiceError,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _raise(exc: PortfolioServiceError) -> None:
    raise HTTPException(
        status_code=exc.http_status,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": {},
        },
    )


@router.get("/status", response_model=PortfolioStatusResponse)
def portfolio_status(
    svc: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioStatusResponse:
    return svc.status()


@router.post("/refresh", response_model=PortfolioResponse)
def portfolio_refresh(
    svc: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    try:
        return svc.refresh()
    except PortfolioServiceError as exc:
        _raise(exc)
        raise  # pragma: no cover


@router.get("/holdings/latest", response_model=PortfolioResponse)
def portfolio_holdings_latest(
    svc: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    try:
        return svc.latest()
    except PortfolioServiceError as exc:
        _raise(exc)
        raise  # pragma: no cover


@router.get("/symbols", response_model=PortfolioSymbolsResponse)
def portfolio_symbols(
    svc: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioSymbolsResponse:
    return svc.symbols()
