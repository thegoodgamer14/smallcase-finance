"""Decision Lab routes — SIP + benchmark + weight gap."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from smallcase_finance.api.deps import get_decision_service
from smallcase_finance.schemas.decision import (
    DecisionRunRequest,
    DecisionRunResponse,
    PriceCoverageResponse,
)
from smallcase_finance.services.decision_service import (
    DecisionService,
    DecisionServiceError,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _raise(exc: DecisionServiceError) -> None:
    raise HTTPException(
        status_code=exc.http_status,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@router.get("/price-coverage", response_model=PriceCoverageResponse)
def price_coverage(
    symbols: str = Query(
        ...,
        description="Comma-separated tickers, e.g. INFY,TCS,NIFTYBEES",
    ),
    svc: DecisionService = Depends(get_decision_service),
) -> PriceCoverageResponse:
    parts = [p.strip() for p in symbols.split(",") if p.strip()]
    return svc.price_coverage(parts)


@router.post("/run", response_model=DecisionRunResponse)
def run_decision(
    body: DecisionRunRequest,
    svc: DecisionService = Depends(get_decision_service),
) -> DecisionRunResponse:
    try:
        return svc.run(body)
    except DecisionServiceError as exc:
        _raise(exc)
        raise  # pragma: no cover
