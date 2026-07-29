"""Unit tests for Kite auth checksum and client mapping (mocked HTTP)."""

from __future__ import annotations

import hashlib

import httpx
import pytest

from smallcase_finance.integrations.kite.auth import (
    KiteAuthError,
    checksum_for_token_exchange,
    exchange_request_token,
    kite_login_url,
)
from smallcase_finance.integrations.kite.client import KiteClient, KiteError


def test_checksum_matches_official_rule():
    key, rt, secret = "abc", "req123", "secret"
    expect = hashlib.sha256(f"{key}{rt}{secret}".encode()).hexdigest()
    assert checksum_for_token_exchange(key, rt, secret) == expect


def test_login_url_requires_key(monkeypatch):
    monkeypatch.setattr(
        "smallcase_finance.integrations.kite.auth.KITE_API_KEY", ""
    )
    with pytest.raises(KiteAuthError):
        kite_login_url()


def test_login_url_shape(monkeypatch):
    monkeypatch.setattr(
        "smallcase_finance.integrations.kite.auth.KITE_API_KEY", "mykey"
    )
    url = kite_login_url()
    assert "api_key=mykey" in url
    assert "v=3" in url
    assert "kite.zerodha.com/connect/login" in url


class _FakeTransport:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload
        self.last_url = ""
        self.last_data: dict | None = None

    def post(self, url, data=None, headers=None, **kwargs):
        self.last_url = url
        self.last_data = dict(data) if data else {}
        return httpx.Response(self.status, json=self.payload)

    def get(self, url, headers=None, timeout=None):
        return httpx.Response(self.status, json=self.payload)


def test_exchange_request_token_success():
    transport = _FakeTransport(
        200,
        {
            "status": "success",
            "data": {
                "access_token": "tok_abc",
                "user_id": "AB1234",
                "user_name": "Test User",
                "login_time": "2026-07-30 10:00:00",
            },
        },
    )
    # httpx.Client-like: exchange uses client.post
    session = exchange_request_token(
        "req_once",
        api_key="k",
        api_secret="s",
        transport=transport,  # type: ignore[arg-type]
    )
    assert session.access_token == "tok_abc"
    assert session.user_id == "AB1234"
    assert transport.last_data is not None
    assert "checksum" in transport.last_data
    assert transport.last_data["request_token"] == "req_once"


def test_exchange_fails_on_http_error():
    transport = _FakeTransport(403, {"status": "error", "message": "invalid"})
    with pytest.raises(KiteAuthError):
        exchange_request_token(
            "bad",
            api_key="k",
            api_secret="s",
            transport=transport,  # type: ignore[arg-type]
        )


def test_holdings_mapping():
    payload = {
        "status": "success",
        "data": [
            {
                "tradingsymbol": "INFY",
                "exchange": "NSE",
                "quantity": 10,
                "average_price": 100.0,
                "last_price": 110.0,
                "pnl": 100.0,
                "product": "CNC",
                "isin": "INE009A01021",
                "instrument_token": 1,
            }
        ],
    }

    class T:
        def get(self, url, headers=None, timeout=None):
            assert "Authorization" in (headers or {})
            assert (headers or {})["Authorization"].startswith("token ")
            return httpx.Response(200, json=payload)

    client = KiteClient(api_key="k", access_token="t", transport=T())
    rows = client.get_holdings()
    assert len(rows) == 1
    assert rows[0].tradingsymbol == "INFY"
    assert rows[0].quantity == 10.0


def test_holdings_requires_session():
    client = KiteClient(api_key="", access_token="")
    with pytest.raises(KiteError):
        client.get_holdings()
