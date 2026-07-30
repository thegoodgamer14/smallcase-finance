"""Kite Connect login URL and request_token → access_token exchange.

Official flow: https://kite.trade/docs/connect/v3/user/

Never log api_secret, request_token, or access_token values.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from smallcase_finance.config import (
    KITE_API_BASE,
    KITE_API_KEY,
    KITE_API_SECRET,
    KITE_LOGIN_BASE,
)

logger = logging.getLogger(__name__)


class KiteAuthError(Exception):
    """Login URL or token exchange failed."""


@dataclass(frozen=True)
class KiteSession:
    """Subset of POST /session/token response (no secret fields logged)."""

    access_token: str
    user_id: str | None = None
    user_name: str | None = None
    login_time: str | None = None


def kite_login_url(*, api_key: str | None = None) -> str:
    """Public browser login URL for the registered Kite Connect app.

    Official params are only ``v`` and ``api_key``. There is no scope/query
    flag to hide "place orders" on Zerodha's consent page — Connect apps
    always show the full fixed permission list. Our product still only
    uses holdings (read-only) after the token is issued.
    """
    key = (api_key if api_key is not None else KITE_API_KEY).strip()
    if not key:
        raise KiteAuthError("KITE_API_KEY is not set")
    qs = urlencode({"v": "3", "api_key": key})
    return f"{KITE_LOGIN_BASE}?{qs}"


def checksum_for_token_exchange(
    api_key: str, request_token: str, api_secret: str
) -> str:
    """SHA-256 hex of api_key + request_token + api_secret (official Kite rule)."""
    raw = f"{api_key}{request_token}{api_secret}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def exchange_request_token(
    request_token: str,
    *,
    api_key: str | None = None,
    api_secret: str | None = None,
    api_base: str | None = None,
    transport: httpx.Client | None = None,
    timeout: float = 30.0,
) -> KiteSession:
    """Exchange one-time request_token for a session access_token.

    POST https://api.kite.trade/session/token
    """
    token = (request_token or "").strip()
    if not token:
        raise KiteAuthError("request_token is empty")

    key = (api_key if api_key is not None else KITE_API_KEY).strip()
    secret = (api_secret if api_secret is not None else KITE_API_SECRET).strip()
    base = (api_base or KITE_API_BASE).rstrip("/")
    if not key or not secret:
        raise KiteAuthError("KITE_API_KEY and KITE_API_SECRET are required for exchange")

    checksum = checksum_for_token_exchange(key, token, secret)
    url = f"{base}/session/token"
    form = {
        "api_key": key,
        "request_token": token,
        "checksum": checksum,
    }
    headers = {
        "X-Kite-Version": "3",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    owns = transport is None
    client = transport or httpx.Client(timeout=timeout)
    try:
        resp = client.post(url, data=form, headers=headers)
    finally:
        if owns:
            client.close()

    if resp.status_code >= 400:
        logger.warning(
            "Kite token exchange HTTP %s (body length %s)",
            resp.status_code,
            len(resp.text or ""),
        )
        raise KiteAuthError(
            f"Kite token exchange failed with HTTP {resp.status_code}"
        )

    try:
        payload: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise KiteAuthError("Kite token response was not JSON") from exc

    if payload.get("status") == "error":
        msg = payload.get("message") or payload.get("error_type") or "error"
        raise KiteAuthError(f"Kite token exchange rejected: {msg}")

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    access = data.get("access_token") if isinstance(data, dict) else None
    if not isinstance(access, str) or not access.strip():
        raise KiteAuthError("Kite token response missing access_token")

    return KiteSession(
        access_token=access.strip(),
        user_id=str(data.get("user_id")) if data.get("user_id") is not None else None,
        user_name=str(data.get("user_name"))
        if data.get("user_name") is not None
        else None,
        login_time=str(data.get("login_time"))
        if data.get("login_time") is not None
        else None,
    )
