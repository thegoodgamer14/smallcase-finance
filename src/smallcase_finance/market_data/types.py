"""Shared market-data types for the provider layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class OHLCVBar:
    """One daily OHLCV bar in product-normalized form.

    Aligns with curated ``prices`` columns and Upstox ``CandleBar``.
    """

    symbol: str
    bar_date: date
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: float
    volume: Optional[float]
    source: Optional[str] = None


@dataclass(frozen=True)
class ProviderStatus:
    """Non-secret status snapshot for logs / API / UI banners.

    Never include tokens, API keys, or secrets on this object.
    """

    configured: bool
    source_label: str
    provider_name: str = "upstox"


class MarketDataError(Exception):
    """Raised when market data cannot be fetched or resolved."""
