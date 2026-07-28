"""Upstox-backed MarketDataProvider — sole production historical source.

Wraps ``integrations.upstox.client.UpstoxClient``, instrument-key resolution,
and optional ``sync_prices`` for raw drops.

Does not implement alternate vendors. When no Bearer token is configured,
``get_history`` returns an empty list and ``status().source_label`` is
``\"sample\"`` so callers can fall back to the labeled sample pipeline path
(demo only — not a second market-data vendor).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional, Sequence

from smallcase_finance.integrations.upstox.client import UpstoxClient, UpstoxError
from smallcase_finance.integrations.upstox.instruments import resolve_instrument_key
from smallcase_finance.integrations.upstox.sync import SyncResult, sync_prices
from smallcase_finance.market_data.types import MarketDataError, OHLCVBar, ProviderStatus

logger = logging.getLogger(__name__)


class UpstoxProvider:
    """Concrete ``MarketDataProvider`` for Upstox daily historical candles.

    Pass a custom ``client`` (with mock transport) for unit tests.
    """

    def __init__(
        self,
        *,
        client: Optional[UpstoxClient] = None,
        access_token: Optional[str] = None,
    ) -> None:
        self._client = client or UpstoxClient(access_token=access_token)

    @property
    def name(self) -> str:
        return "upstox"

    @property
    def configured(self) -> bool:
        """True when a non-empty Bearer token is available."""
        return bool(self._client.configured)

    def status(self) -> ProviderStatus:
        """Non-secret readiness for banners / logs (never includes credentials)."""
        ok = self.configured
        return ProviderStatus(
            configured=ok,
            source_label="upstox" if ok else "sample",
            provider_name="upstox",
        )

    def get_history(
        self,
        *,
        symbol: str,
        from_date: date,
        to_date: date,
        instrument_key: Optional[str] = None,
    ) -> list[OHLCVBar]:
        if from_date > to_date:
            raise MarketDataError("from_date must be <= to_date")

        sym = symbol.strip().upper()
        if not sym:
            raise MarketDataError("symbol must be non-empty")

        if not self.configured:
            logger.warning(
                "UpstoxProvider not configured (no UPSTOX_ACCESS_TOKEN); "
                "returning empty history for %s (demo path should use sample prices)",
                sym,
            )
            return []

        key = (instrument_key or "").strip() or resolve_instrument_key(sym)
        if not key:
            raise MarketDataError(
                f"no Upstox instrument_key for symbol {sym!r}; "
                "extend DEFAULT_NSE_INSTRUMENT_KEYS or "
                "data/raw/instruments/upstox_instrument_map.json"
            )

        try:
            candles = self._client.fetch_daily_candles(
                instrument_key=key,
                symbol=sym,
                from_date=from_date,
                to_date=to_date,
            )
        except UpstoxError as exc:
            raise MarketDataError(str(exc)) from exc
        except ValueError as exc:
            raise MarketDataError(str(exc)) from exc

        return [
            OHLCVBar(
                symbol=c.symbol,
                bar_date=c.bar_date,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
                source="upstox",
            )
            for c in candles
        ]

    def sync_to_raw(
        self,
        *,
        symbols: Optional[Sequence[str]] = None,
        years: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        run_pipeline_after: bool = False,
        allow_sample_fallback: bool = True,
    ) -> SyncResult:
        """Delegate to ``integrations.upstox.sync.sync_prices`` (immutable raw drop)."""
        return sync_prices(
            symbols=list(symbols) if symbols is not None else None,
            years=years,
            from_date=from_date,
            to_date=to_date,
            client=self._client,
            run_pipeline_after=run_pipeline_after,
            allow_sample_fallback=allow_sample_fallback,
        )


def get_market_data_provider(
    *,
    client: Optional[UpstoxClient] = None,
    access_token: Optional[str] = None,
) -> UpstoxProvider:
    """Return the sole production market-data provider (Upstox).

    Factory exists so callers do not construct vendor clients directly.
    No alternate providers are selectable in this product version.
    """
    return UpstoxProvider(client=client, access_token=access_token)
