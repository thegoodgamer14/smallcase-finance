"""Market data provider layer (SIP Lab).

Policy: Upstox is the sole production historical OHLCV provider (ADR 005).
"""

from smallcase_finance.market_data.protocol import MarketDataProvider
from smallcase_finance.market_data.types import MarketDataError, OHLCVBar, ProviderStatus
from smallcase_finance.market_data.upstox_provider import (
    UpstoxProvider,
    get_market_data_provider,
)

__all__ = [
    "MarketDataError",
    "MarketDataProvider",
    "OHLCVBar",
    "ProviderStatus",
    "UpstoxProvider",
    "get_market_data_provider",
]
