"""Smallcase list/detail/holdings/performance/metrics/nav routes."""

from __future__ import annotations

from datetime import date
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query

from smallcase_finance.api.deps import (
    get_metrics_service,
    get_nav_service,
    get_performance_service,
    get_smallcase_service,
)
from smallcase_finance.data_access.exceptions import (
    CuratedDataUnavailable,
    SmallcaseNotFound,
)
from smallcase_finance.schemas.attribution import AttributionResponse
from smallcase_finance.schemas.common import MetricWindow, SeriesFreq
from smallcase_finance.schemas.holdings import HoldingsResponse
from smallcase_finance.schemas.metrics import MetricsResponse
from smallcase_finance.schemas.nav import NavLatestResponse, NavSeriesResponse
from smallcase_finance.schemas.performance import PerformanceResponse
from smallcase_finance.schemas.smallcase import SmallcaseDetail, SmallcaseListResponse
from smallcase_finance.services.metrics_service import MetricsService
from smallcase_finance.services.performance_service import NavService, PerformanceService
from smallcase_finance.services.smallcase_service import SmallcaseService

router = APIRouter(prefix="/smallcases", tags=["smallcases"])


def _http_for(exc: Exception) -> HTTPException:
    if isinstance(exc, SmallcaseNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CuratedDataUnavailable):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


def _check_range(start: Optional[date], end: Optional[date]) -> None:
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=400, detail="start must be <= end")


@router.get("", response_model=SmallcaseListResponse)
def list_smallcases(
    tag: Optional[str] = Query(default=None, description="Filter by theme substring"),
    q: Optional[str] = Query(default=None, description="Search name / id / description"),
    svc: SmallcaseService = Depends(get_smallcase_service),
) -> SmallcaseListResponse:
    try:
        return svc.list_smallcases(tag=tag, q=q)
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/{smallcase_id}", response_model=SmallcaseDetail)
def get_smallcase(
    smallcase_id: str,
    svc: SmallcaseService = Depends(get_smallcase_service),
) -> SmallcaseDetail:
    try:
        return svc.get_smallcase(smallcase_id)
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/{smallcase_id}/holdings", response_model=HoldingsResponse)
def get_holdings(
    smallcase_id: str,
    as_of: Optional[date] = Query(default=None, description="ISO date; default latest"),
    svc: SmallcaseService = Depends(get_smallcase_service),
) -> HoldingsResponse:
    try:
        return svc.get_holdings(smallcase_id, as_of=as_of)
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/{smallcase_id}/performance", response_model=PerformanceResponse)
def get_performance(
    smallcase_id: str,
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    benchmark: bool = Query(default=False),
    freq: SeriesFreq = Query(default=SeriesFreq.daily),
    svc: PerformanceService = Depends(get_performance_service),
) -> PerformanceResponse:
    _check_range(start, end)
    try:
        return svc.get_performance(
            smallcase_id,
            start=start,
            end=end,
            benchmark=benchmark,
            freq=freq.value,
        )
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/{smallcase_id}/metrics", response_model=MetricsResponse)
def get_metrics(
    smallcase_id: str,
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    window: MetricWindow = Query(default=MetricWindow.itd),
    svc: MetricsService = Depends(get_metrics_service),
) -> MetricsResponse:
    _check_range(start, end)
    try:
        return svc.get_metrics(
            smallcase_id,
            start=start,
            end=end,
            window=window,
        )
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get("/{smallcase_id}/attribution", response_model=AttributionResponse)
def get_attribution(
    smallcase_id: str,
    period_start: Optional[date] = Query(
        default=None, description="Exact period_start match in contribution table"
    ),
    period_end: Optional[date] = Query(
        default=None, description="Exact period_end match in contribution table"
    ),
    svc: PerformanceService = Depends(get_performance_service),
) -> AttributionResponse:
    """Simple symbol contribution (avg_weight × symbol_return) for UI top contributors."""
    _check_range(period_start, period_end)
    try:
        return svc.get_attribution(
            smallcase_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as exc:
        raise _http_for(exc) from exc


@router.get(
    "/{smallcase_id}/nav",
    response_model=None,
    responses={
        200: {
            "description": "NAV series or latest point",
            "content": {
                "application/json": {
                    "examples": {
                        "series": {
                            "summary": "series",
                            "value": {
                                "smallcase_id": "digital-india",
                                "currency": "INR",
                                "series": [{"date": "2023-01-02", "nav": 100.0}],
                            },
                        },
                        "latest": {
                            "summary": "latest_only",
                            "value": {
                                "smallcase_id": "digital-india",
                                "currency": "INR",
                                "as_of": "2025-12-31",
                                "nav": 120.0,
                            },
                        },
                    }
                }
            },
        }
    },
)
def get_nav(
    smallcase_id: str,
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    latest_only: bool = Query(default=False),
    svc: NavService = Depends(get_nav_service),
) -> Union[NavSeriesResponse, NavLatestResponse]:
    _check_range(start, end)
    try:
        return svc.get_nav(
            smallcase_id,
            start=start,
            end=end,
            latest_only=latest_only,
        )
    except Exception as exc:
        raise _http_for(exc) from exc
