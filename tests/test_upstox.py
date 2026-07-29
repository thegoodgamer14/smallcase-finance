"""Unit tests for Upstox client, market_data provider, lookback, and sync (mocked HTTP)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from smallcase_finance.integrations.upstox.client import (
    UpstoxClient,
    UpstoxError,
    parse_candle_payload,
)
from smallcase_finance.integrations.upstox.instruments import resolve_instrument_key
from smallcase_finance.integrations.upstox.sync import (
    candles_to_frame,
    resolve_lookback,
    sync_prices,
    write_price_drop,
)
from smallcase_finance.market_data import (
    MarketDataProvider,
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
        assert headers["Authorization"].startswith("Bearer ")
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


def test_resolve_lookback_years():
    start, end = resolve_lookback(years=2, to_date=date(2025, 1, 1))
    assert end == date(2025, 1, 1)
    assert start < end
    # ~2 calendar years
    assert (end - start).days >= 700


def test_resolve_lookback_custom_range():
    start, end = resolve_lookback(from_date=date(2020, 6, 1), to_date=date(2021, 6, 1))
    assert start == date(2020, 6, 1)
    assert end == date(2021, 6, 1)


def test_resolve_lookback_invalid():
    with pytest.raises(ValueError):
        resolve_lookback(from_date=date(2022, 1, 1), to_date=date(2021, 1, 1))


def test_parse_candle_payload_sorts_ascending():
    bars = parse_candle_payload(SAMPLE_PAYLOAD, symbol="TCS")
    assert len(bars) == 2
    assert bars[0].bar_date == date(2024, 1, 2)
    assert bars[1].bar_date == date(2024, 1, 3)
    assert bars[0].close == 102.0
    assert bars[1].volume == 1000.0


def test_instrument_keys_for_sample_symbols():
    for sym in ("TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM"):
        assert resolve_instrument_key(sym) is not None


def test_client_fetch_daily_candles_mocked():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="test-token", transport=transport)
    bars = client.fetch_daily_candles(
        instrument_key="NSE_EQ|INE467B01029",
        symbol="TCS",
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 31),
    )
    assert len(bars) == 2
    assert "historical-candle" in transport.urls[0]
    assert "day" in transport.urls[0]


def test_client_auth_error():
    transport = _FakeTransport({"status": "error"}, status_code=401)
    client = UpstoxClient(access_token="bad", transport=transport)
    with pytest.raises(UpstoxError, match="auth"):
        client.fetch_daily_candles(
            instrument_key="NSE_EQ|INE467B01029",
            symbol="TCS",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 2),
        )


def test_candles_to_frame_and_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_CURATED_ROOT", str(tmp_path / "curated"))
    from smallcase_finance.integrations.upstox.client import CandleBar

    bars = [
        CandleBar("TCS", date(2024, 1, 2), 1.0, 2.0, 0.5, 1.5, 10.0),
        CandleBar("INFY", date(2024, 1, 2), 1.0, 2.0, 0.5, 1.5, 10.0),
    ]
    df = candles_to_frame(bars)
    assert df.height == 2
    assert set(df["source"].unique().to_list()) == {"upstox"}
    out = write_price_drop(df, raw=tmp_path / "raw", drop_date=date(2024, 7, 1))
    assert out.is_file()
    assert out.parent.name.endswith("_upstox")


def test_sync_without_credentials_sample_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("UPSTOX_API_KEY", raising=False)
    # Force empty token even if config was already imported
    monkeypatch.setattr(
        "smallcase_finance.integrations.upstox.sync.UpstoxClient",
        lambda **kw: type(
            "C",
            (),
            {
                "configured": False,
                "__enter__": lambda self: self,
                "__exit__": lambda self, *a: None,
            },
        )(),
    )
    result = sync_prices(
        symbols=["TCS"],
        years=1,
        allow_sample_fallback=True,
        run_pipeline_after=False,
    )
    assert result.used_sample_fallback is True
    assert result.row_count == 0
    assert any(
        "credentials" in w.lower() or "token" in w.lower() or "Sample" in result.message
        for w in result.warnings
    ) or "Sample" in result.message


def test_sync_mocked_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="tok", transport=transport)

    # write under tmp raw root
    monkeypatch.setattr(
        "smallcase_finance.integrations.upstox.sync.raw_root",
        lambda: tmp_path / "raw",
    )
    (tmp_path / "raw" / "prices").mkdir(parents=True)

    result = sync_prices(
        symbols=["TCS"],
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 31),
        client=client,
        allow_sample_fallback=False,
        run_pipeline_after=False,
    )
    assert result.used_sample_fallback is False
    assert "TCS" in result.fetched_symbols
    assert result.row_count == 2
    assert result.output_path is not None
    assert Path(result.output_path).is_file()


# ── MarketDataProvider / UpstoxProvider ─────────────────────────────────────


def test_upstox_provider_is_market_data_provider():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="tok", transport=transport)
    provider = UpstoxProvider(client=client)
    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "upstox"
    status = provider.status()
    assert status.configured is True
    assert status.source_label == "upstox"
    # status must never expose secrets
    assert not hasattr(status, "access_token")
    assert not hasattr(status, "api_key")


def test_upstox_provider_get_history_mocked():
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="tok", transport=transport)
    provider = get_market_data_provider(client=client)
    bars = provider.get_history(
        symbol="TCS",
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 31),
    )
    assert len(bars) == 2
    assert bars[0].bar_date == date(2024, 1, 2)
    assert bars[0].source == "upstox"
    assert bars[0].close == 102.0
    assert "historical-candle" in transport.urls[0]


def test_upstox_provider_not_configured_returns_empty():
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


def test_upstox_provider_sync_to_raw_delegates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    transport = _FakeTransport(SAMPLE_PAYLOAD)
    client = UpstoxClient(access_token="tok", transport=transport)
    provider = UpstoxProvider(client=client)
    monkeypatch.setattr(
        "smallcase_finance.integrations.upstox.sync.raw_root",
        lambda: tmp_path / "raw",
    )
    (tmp_path / "raw" / "prices").mkdir(parents=True)

    result = provider.sync_to_raw(
        symbols=["TCS"],
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 31),
        run_pipeline_after=False,
        allow_sample_fallback=False,
    )
    assert result.row_count == 2
    assert "TCS" in result.fetched_symbols


def test_config_api_key_is_not_bearer_alias(monkeypatch: pytest.MonkeyPatch):
    """UPSTOX_API_KEY is client_id, not a substitute for UPSTOX_ACCESS_TOKEN.

    Isolates from a founder ``.env`` by patching module attributes after reload
    (``load_dotenv(override=False)`` would re-fill ACCESS_TOKEN from file if
    we only deleted the env var).
    """
    import importlib

    import smallcase_finance.config as cfg

    monkeypatch.setenv("UPSTOX_API_KEY", "portal-api-key-not-a-token")
    monkeypatch.setenv("UPSTOX_API_SECRET", "portal-secret")
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    # Prevent .env from re-injecting a real access token during reload
    monkeypatch.setattr(cfg, "_env_file", type(cfg._env_file)("/nonexistent/.env"))
    importlib.reload(cfg)
    monkeypatch.setattr(cfg, "UPSTOX_ACCESS_TOKEN", "")
    monkeypatch.setattr(cfg, "UPSTOX_API_KEY", "portal-api-key-not-a-token")
    monkeypatch.setattr(cfg, "UPSTOX_API_SECRET", "portal-secret")
    assert cfg.UPSTOX_ACCESS_TOKEN == ""
    assert cfg.UPSTOX_API_KEY == "portal-api-key-not-a-token"
    assert cfg.UPSTOX_API_SECRET == "portal-secret"
    assert cfg.upstox_configured() is False
    # Client must not pick up API_KEY as Bearer
    client = UpstoxClient(access_token=cfg.UPSTOX_ACCESS_TOKEN)
    assert client.configured is False
