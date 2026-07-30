"""Thin Kite Connect REST client (profile + holdings). Read-only product use."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from smallcase_finance.config import (
    KITE_ACCESS_TOKEN,
    KITE_API_BASE,
    KITE_API_KEY,
)

logger = logging.getLogger(__name__)


class KiteError(Exception):
    """Kite API error or unexpected payload."""


class HttpTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response: ...


@dataclass(frozen=True)
class KiteHolding:
    """One equity holding row (delivery book)."""

    tradingsymbol: str
    exchange: str
    quantity: float
    average_price: float | None
    last_price: float | None
    pnl: float | None
    product: str | None
    isin: str | None
    instrument_token: int | None


class KiteClient:
    """Read-only Kite Connect client (holdings + profile only).

    Auth header: ``Authorization: token api_key:access_token``

    **No order placement.** This client only uses HTTP GET for
    ``/user/profile`` and ``/portfolio/holdings``. Zerodha's authorize
    screen may still list order permissions for all Connect apps; that is
    not configurable via login URL scopes (see docs/integrations/kite-connect.md).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        api_base: str | None = None,
        transport: HttpTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (api_key if api_key is not None else KITE_API_KEY).strip()
        self.access_token = (
            access_token if access_token is not None else KITE_ACCESS_TOKEN
        ).strip()
        self.api_base = (api_base or KITE_API_BASE).rstrip("/")
        self.timeout = timeout
        self._transport = transport
        self._owns = transport is None
        self._client: httpx.Client | None = None

    def __enter__(self) -> KiteClient:
        if self._owns:
            self._client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.access_token:
            raise KiteError(
                "Kite session not configured (need KITE_API_KEY and KITE_ACCESS_TOKEN)"
            )
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
        }

    def _get(self, path: str) -> Any:
        url = f"{self.api_base}{path}"
        headers = self._headers()
        if self._transport is not None:
            resp = self._transport.get(url, headers=headers, timeout=self.timeout)
        else:
            if self._client is None:
                self._client = httpx.Client(timeout=self.timeout)
            resp = self._client.get(url, headers=headers)

        if resp.status_code >= 400:
            logger.warning(
                "Kite GET %s HTTP %s (body length %s)",
                path,
                resp.status_code,
                len(resp.text or ""),
            )
            raise KiteError(f"Kite API {path} failed with HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise KiteError(f"Kite API {path} returned non-JSON") from exc

        if isinstance(payload, dict) and payload.get("status") == "error":
            msg = payload.get("message") or "error"
            raise KiteError(f"Kite API {path} error: {msg}")

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def get_profile(self) -> dict[str, Any]:
        data = self._get("/user/profile")
        if not isinstance(data, dict):
            raise KiteError("Unexpected profile payload")
        return data

    def get_holdings(self) -> list[KiteHolding]:
        data = self._get("/portfolio/holdings")
        if not isinstance(data, list):
            raise KiteError("Unexpected holdings payload")
        out: list[KiteHolding] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            sym = row.get("tradingsymbol")
            if not isinstance(sym, str) or not sym.strip():
                continue
            out.append(
                KiteHolding(
                    tradingsymbol=sym.strip(),
                    exchange=str(row.get("exchange") or ""),
                    quantity=float(row.get("quantity") or 0),
                    average_price=_opt_float(row.get("average_price")),
                    last_price=_opt_float(row.get("last_price")),
                    pnl=_opt_float(row.get("pnl")),
                    product=str(row["product"]) if row.get("product") is not None else None,
                    isin=str(row["isin"]) if row.get("isin") is not None else None,
                    instrument_token=_opt_int(row.get("instrument_token")),
                )
            )
        return out


def _opt_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _opt_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
