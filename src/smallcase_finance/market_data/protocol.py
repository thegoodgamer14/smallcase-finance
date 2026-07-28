"""MarketDataProvider protocol — vendor-agnostic history interface.

Binding policy (ADR 005): the **only** production concrete provider for
equity/ETF historical OHLCV is ``UpstoxProvider``. Do not add yfinance,
bhavcopy, or Fyers implementations in this product version.

Sample / synthetic prices for demos are **not** a MarketDataProvider
implementation of live history; they stay on the local sample pipeline path.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, runtime_checkable

from smallcase_finance.market_data.types import OHLCVBar


@runtime_checkable
class MarketDataProvider(Protocol):
    """Fetch daily historical OHLCV for a symbol over an inclusive date range.

    Implementers must not invent prices or fall back to alternate vendors.
    Missing instrument coverage should raise or return empty with clear errors
    at the call site — never silent vendor substitution.
    """

    @property
    def name(self) -> str:
        """Stable provider id (e.g. ``\"upstox\"``)."""
        ...

    def get_history(
        self,
        *,
        symbol: str,
        from_date: date,
        to_date: date,
        instrument_key: Optional[str] = None,
    ) -> list[OHLCVBar]:
        """Return daily bars sorted ascending by ``bar_date``.

        Args:
            symbol: Uppercase ticker (e.g. ``INFY``).
            from_date: Inclusive start.
            to_date: Inclusive end.
            instrument_key: Optional vendor key (Upstox ``NSE_EQ|…``).
                When omitted, the provider may resolve via its instrument map.
        """
        ...
