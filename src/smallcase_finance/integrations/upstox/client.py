"""Minimal Upstox REST client for historical daily candles.

Docs: https://upstox.com/developer/api-documentation/get-historical-candle-data/
Endpoint: GET /v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from smallcase_finance.config import UPSTOX_ACCESS_TOKEN, UPSTOX_API_BASE

logger = logging.getLogger(__name__)


class UpstoxError(Exception):
    """Raised when the Upstox API returns an error or unexpected payload."""


class HttpTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response: ...


@dataclass(frozen=True)
class CandleBar:
    """One daily OHLCV bar mapped into our price contract."""

    symbol: str
    bar_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: float | None


class UpstoxClient:
    """Thin wrapper around Upstox historical candle API.

    Pass a custom ``transport`` (e.g. ``httpx.Client`` or a mock) for tests.
    """

    def __init__(
        self,
        *,
        access_token: str | None = None,
        api_base: str | None = None,
        transport: HttpTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.access_token = (access_token if access_token is not None else UPSTOX_ACCESS_TOKEN).strip()
        self.api_base = (api_base or UPSTOX_API_BASE).rstrip("/")
        self.timeout = timeout
        self._transport = transport
        self._owns_client = transport is None
        self._client: httpx.Client | None = None

    def __enter__(self) -> UpstoxClient:
        if self._owns_client:
            self._client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    @property
    def configured(self) -> bool:
        return bool(self.access_token)

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise UpstoxError(
                "Upstox access token not configured. "
                "Set UPSTOX_ACCESS_TOKEN in the environment "
                "(Bearer from Upstox Developer Apps → Generate)."
            )
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def _get(self, url: str) -> httpx.Response:
        headers = self._headers()
        if self._transport is not None:
            return self._transport.get(url, headers=headers, timeout=self.timeout)
        if self._client is not None:
            return self._client.get(url, headers=headers)
        # one-shot without context manager
        with httpx.Client(timeout=self.timeout) as client:
            return client.get(url, headers=headers)

    def fetch_daily_candles(
        self,
        *,
        instrument_key: str,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[CandleBar]:
        """Fetch daily OHLC for ``instrument_key`` between inclusive dates."""
        if from_date > to_date:
            raise ValueError("from_date must be <= to_date")

        # Path segment must be URL-encoded (instrument keys contain '|')
        encoded_key = quote(instrument_key, safe="")
        # Upstox path order: .../{interval}/{to_date}/{from_date}
        url = (
            f"{self.api_base}/historical-candle/{encoded_key}/day/"
            f"{to_date.isoformat()}/{from_date.isoformat()}"
        )
        logger.debug("GET %s (symbol=%s)", url, symbol)
        try:
            resp = self._get(url)
        except httpx.HTTPError as exc:
            raise UpstoxError(f"HTTP error fetching {symbol}: {exc}") from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise UpstoxError(
                f"Upstox auth failed (HTTP {resp.status_code}). "
                "Check UPSTOX_ACCESS_TOKEN is valid and not expired."
            )
        if resp.status_code >= 400:
            body = _safe_text(resp)
            raise UpstoxError(
                f"Upstox error for {symbol} (HTTP {resp.status_code}): {body[:300]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstoxError(f"Invalid JSON for {symbol}") from exc

        return parse_candle_payload(payload, symbol=symbol)


def parse_candle_payload(payload: Any, *, symbol: str) -> list[CandleBar]:
    """Parse Upstox historical candle JSON into CandleBar rows.

    Expected shape (v2)::

        {
          "status": "success",
          "data": {
            "candles": [
              ["2024-01-02T00:00:00+05:30", open, high, low, close, volume, oi],
              ...
            ]
          }
        }
    """
    if not isinstance(payload, dict):
        raise UpstoxError(f"Unexpected payload type for {symbol}")

    status = payload.get("status")
    if status and status != "success":
        raise UpstoxError(f"Upstox status={status!r} for {symbol}: {payload.get('errors')}")

    data = payload.get("data") or {}
    candles = data.get("candles") if isinstance(data, dict) else None
    if candles is None:
        # some error envelopes put messages at top level
        raise UpstoxError(f"No candles in response for {symbol}")

    bars: list[CandleBar] = []
    for row in candles:
        bar = _row_to_bar(row, symbol=symbol)
        if bar is not None:
            bars.append(bar)
    # API often returns newest-first; sort ascending for pipeline friendliness
    bars.sort(key=lambda b: b.bar_date)
    return bars


def _row_to_bar(row: Any, *, symbol: str) -> CandleBar | None:
    if not isinstance(row, (list, tuple)) or len(row) < 5:
        logger.warning("skip malformed candle for %s: %r", symbol, row)
        return None
    ts, o, h, l, c = row[0], row[1], row[2], row[3], row[4]
    vol = row[5] if len(row) > 5 else None
    try:
        bar_date = _parse_ts(ts)
        close = float(c)
    except (TypeError, ValueError) as exc:
        logger.warning("skip unparseable candle for %s: %s", symbol, exc)
        return None

    def _opt_float(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return CandleBar(
        symbol=symbol.upper(),
        bar_date=bar_date,
        open=_opt_float(o),
        high=_opt_float(h),
        low=_opt_float(l),
        close=close,
        volume=_opt_float(vol),
    )


def _parse_ts(ts: Any) -> date:
    if isinstance(ts, datetime):
        return ts.date()
    if isinstance(ts, date):
        return ts
    s = str(ts)
    # "2024-01-02T00:00:00+05:30" or "2024-01-02"
    return date.fromisoformat(s[:10])


def _safe_text(resp: httpx.Response) -> str:
    try:
        return resp.text or ""
    except Exception:
        return ""
