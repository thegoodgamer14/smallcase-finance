"""Pydantic v2 models.

- ``schemas.models`` — curated-table / raw-definition contracts (data dictionary)
- sibling modules (``smallcase``, ``nav``, …) — HTTP API request/response DTOs

Contract source of truth for Frontend API shapes: docs/architecture/backend.md §6.
"""

from smallcase_finance.schemas.attribution import AttributionItem, AttributionResponse
from smallcase_finance.schemas.backtest import (
    BacktestParams,
    BacktestRequest,
    BacktestResponse,
    RebalanceEventDTO,
)
from smallcase_finance.schemas.common import (
    ErrorResponse,
    HealthResponse,
    MetricsAssumptions,
    MetricWindow,
    SeriesFreq,
)
from smallcase_finance.schemas.holdings import HoldingItem, HoldingsResponse
from smallcase_finance.schemas.metrics import MetricValues, MetricsResponse
from smallcase_finance.schemas.models import (  # noqa: F401
    Contribution,
    HoldingsSnapshot,
    Instrument,
    MetricsSnapshot,
    NavPoint,
    PriceBar,
    RebalanceEvent,
    Smallcase,
    SmallcaseConstituent,
    SmallcaseDefinitionFile,
)
from smallcase_finance.schemas.nav import NavLatestResponse, NavPointDTO, NavSeriesResponse
from smallcase_finance.schemas.performance import PerformancePoint, PerformanceResponse
from smallcase_finance.schemas.smallcase import (
    SmallcaseDetail,
    SmallcaseListItem,
    SmallcaseListResponse,
)

__all__ = [
    "ErrorResponse",
    "HealthResponse",
    "MetricsAssumptions",
    "MetricWindow",
    "SeriesFreq",
    "SmallcaseListItem",
    "SmallcaseListResponse",
    "SmallcaseDetail",
    "HoldingItem",
    "HoldingsResponse",
    "PerformancePoint",
    "PerformanceResponse",
    "MetricValues",
    "MetricsResponse",
    "NavPointDTO",
    "NavSeriesResponse",
    "NavLatestResponse",
    "AttributionItem",
    "AttributionResponse",
    "BacktestRequest",
    "BacktestResponse",
    "BacktestParams",
    "RebalanceEventDTO",
]
