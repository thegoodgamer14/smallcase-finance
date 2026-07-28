"""Liveness + data-root reachability."""

from __future__ import annotations

from fastapi import APIRouter

from smallcase_finance import __version__
from smallcase_finance.config import DATA_CURATED_ROOT
from smallcase_finance.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    reachable = DATA_CURATED_ROOT.is_dir()
    return HealthResponse(
        status="ok" if reachable else "degraded",
        version=__version__,
        data_curated_root=str(DATA_CURATED_ROOT),
        data_reachable=reachable,
    )
