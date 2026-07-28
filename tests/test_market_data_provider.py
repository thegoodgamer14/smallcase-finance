"""MarketDataProvider protocol shape + UpstoxProvider unit tests (mocked)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from smallcase_finance.integrations.upstox.client import UpstoxClient
from smallcase_finance.market_data import (
    MarketDataError,
    MarketDataProvider,
    OHLCVBar,
    UpstoxProvider,
    get_market_data_provider,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


class _FakeTransport:
    def __init__(self, payload: Any, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code
        self.urls: list[str] = []

    def get(self, url: str, *, headers: dict[str, str] | None = None, timeout: float | None = None):
        self.urls.append(url)
        assert headers is not None
        assert "Authorization" in headers
        return _FakeResponse(self.status_code, self.payload)


SAMPLE_PAYLOAD = {
    "status": "success",
    "data": {
        "candles": [
            ["2024-01-03T00:00:00+05:30", 102.0, 105.0, 101.0, 104.0, 1000, 0],
            ["2024-01-02T00:00:00+05:30", 100.0, 103.0, 99.0, 102.0, 900, 0],
        ]
    },
}


def test_upstox_provider_is_market_data_provider():
    client = UpstoxClient(access_token="test-token", transport=_FakeTransport(SAMPLE_PAYLOAD))
    provider = UpstoxProvider(client=client)
    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "upstox"


def test_upstox_provider_get_history_maps_bars():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="test-token", transport=transport)
    provider = UpstoxProvider(client=client)

    bars = provider.get_history(
        symbol="tcs",
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 10),
    )
    assert len(bars) == 2
    assert all(isinstance(b, OHLCVBar) for b in bars)
    assert bars[0].bar_date <= bars[1].bar_date
    assert bars[0].symbol == "TCS"
    assert bars[0].close == 102.0
    assert bars[0].source == "upstox"
    assert bars[1].close == 104.0
    assert any("historical-candle" in u for u in transport.urls)


def test_upstox_provider_explicit_instrument_key():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="test-token", transport=transport)
    provider = UpstoxProvider(client=client)

    bars = provider.get_history(
        symbol="CUSTOM",
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 10),
        instrument_key="NSE_EQ|INE999A01000",
    )
    assert len(bars) == 2
    assert "INE999A01000" in transport.urls[0] or "NSE_EQ" in transport.urls[0]


def test_upstox_provider_missing_instrument_key():
    client = UpstoxClient(access_token="test-token", transport=_FakeTransport(SAMPLE_PAYLOAD))
    provider = UpstoxProvider(client=client)
    with pytest.raises(MarketDataError, match="instrument_key"):
        provider.get_history(
            symbol="NOTAREALTICKERZZZ",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 10),
        )


def test_upstox_provider_invalid_date_range():
    client = UpstoxClient(access_token="test-token", transport=_FakeTransport(SAMPLE_PAYLOAD))
    provider = UpstoxProvider(client=client)
    with pytest.raises(MarketDataError, match="from_date"):
        provider.get_history(
            symbol="TCS",
            from_date=date(2024, 2, 1),
            to_date=date(2024, 1, 1),
        )


def test_upstox_provider_auth_error_wrapped():
    transport = _FakeTransport({"status": "error"}, status_code=401)
    client = UpstoxClient(access_token="bad-token", transport=transport)
    provider = UpstoxProvider(client=client)
    with pytest.raises(MarketDataError, match="auth|token|401"):
        provider.get_history(
            symbol="TCS",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 10),
        )


def test_protocol_requires_name_and_get_history():
    """Structural check: a minimal duck-typed provider satisfies the Protocol."""

    class _Stub:
        @property
        def name(self) -> str:
            return "stub"

        def get_history(
            self,
            *,
            symbol: str,
            from_date: date,
            to_date: date,
            instrument_key: str | None = None,
        ) -> list[OHLCVBar]:
            return []

    assert isinstance(_Stub(), MarketDataProvider)


def test_get_market_data_provider_factory():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="test-token", transport=transport)
    provider = get_market_data_provider(client=client)
    assert isinstance(provider, UpstoxProvider)
    assert provider.name == "upstox"
    assert provider.status().configured is True
    assert provider.status().source_label == "upstox"


def test_not_configured_returns_empty_history():
    client = UpstoxClient(access_token="", transport=_FakeTransport(SAMPLE_PAYLOAD))
    provider = UpstoxProvider(client=client)
    assert provider.status().configured is False
    assert provider.status().source_label == "sample"
    bars = provider.get_history(
        symbol="TCS",
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 2),
    )
    assert bars == []
