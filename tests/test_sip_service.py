"""Unit tests for SIP service + price panel (fixture prices, no network)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from smallcase_finance.data_access.price_panel import (
    DATA_SOURCE_FIXTURE,
    DATA_SOURCE_SAMPLE,
    DATA_SOURCE_UPSTOX,
    build_price_panel_from_rows,
    classify_data_source,
    load_price_panel,
)
from smallcase_finance.schemas.sip import SipRunResult
from smallcase_finance.services.sip_service import SipService, SipServiceError
from smallcase_finance.strategies import strategy_config_from_dict

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_YAML = REPO_ROOT / "config" / "strategies" / "example-sip-equity.yaml"


def _weekdays(start: date, end: date) -> list[date]:
    out: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _fixture_rows(
    symbols: list[str],
    sessions: list[date],
    *,
    source: str = "fixture",
    base: float = 100.0,
) -> list[dict]:
    rows: list[dict] = []
    for si, sym in enumerate(symbols):
        for i, d in enumerate(sessions):
            px = base * (1 + 0.1 * si) * (1.0 + 0.0004) ** i
            rows.append(
                {
                    "symbol": sym,
                    "date": d,
                    "close": px,
                    "adj_close": px,
                    "source": source,
                }
            )
    return rows


def _inline_strategy(**overrides) -> dict:
    base = {
        "strategy_id": "fixture-sip",
        "name": "Fixture SIP",
        "basket": {
            "kind": "inline",
            "constituents": [
                {"symbol": "AAA", "target_weight": 0.5},
                {"symbol": "BBB", "target_weight": 0.5},
            ],
        },
        "sip": {
            "amount": 1000.0,
            "day_of_month": 15,
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "as_of": "2024-06-28",
        },
    }
    base.update(overrides)
    return base


# ── data_source classification ───────────────────────────────────────────────


def test_classify_data_source_upstox():
    assert classify_data_source(["upstox"]) == DATA_SOURCE_UPSTOX
    assert classify_data_source(["UPSTOX", "upstox"]) == DATA_SOURCE_UPSTOX


def test_classify_data_source_sample():
    assert classify_data_source(["sample"]) == DATA_SOURCE_SAMPLE
    assert classify_data_source(["demo", "synthetic"]) == DATA_SOURCE_SAMPLE


def test_classify_data_source_fixture():
    assert classify_data_source(["fixture"]) == DATA_SOURCE_FIXTURE


def test_classify_data_source_mixed():
    assert classify_data_source(["upstox", "sample"]) == "mixed"


# ── price panel from rows (no I/O) ───────────────────────────────────────────


def test_build_price_panel_from_fixture_rows():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 3, 31))
    rows = _fixture_rows(["AAA", "BBB"], sessions, source="fixture")
    panel = build_price_panel_from_rows(
        rows, ["AAA", "BBB"], start=date(2024, 1, 1), end=date(2024, 3, 31)
    )
    assert panel.data_source == DATA_SOURCE_FIXTURE
    assert panel.missing_symbols == []
    assert set(panel.available_symbols) == {"AAA", "BBB"}
    assert panel.sessions[0] >= date(2024, 1, 1)
    assert any("data_source=fixture" in w for w in panel.warnings)


def test_price_panel_missing_symbol_warning():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 1, 31))
    rows = _fixture_rows(["AAA"], sessions, source="sample")
    panel = build_price_panel_from_rows(rows, ["AAA", "MISSING"])
    assert panel.missing_symbols == ["MISSING"]
    assert any("missing_symbols" in w for w in panel.warnings)
    assert panel.data_source == DATA_SOURCE_SAMPLE


def test_price_panel_upstox_source_label():
    sessions = [date(2024, 1, 15)]
    rows = _fixture_rows(["TCS"], sessions, source="upstox")
    panel = build_price_panel_from_rows(rows, ["TCS"])
    assert panel.data_source == DATA_SOURCE_UPSTOX
    # real market path — no demo banner required
    assert not any("demo" in w for w in panel.warnings)


# ── SipService with injected fixture prices ──────────────────────────────────


def test_sip_service_run_with_fixture_prices():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 6, 28))
    rows = _fixture_rows(["AAA", "BBB"], sessions, source="fixture")
    panel = build_price_panel_from_rows(
        rows,
        ["AAA", "BBB"],
        start=date(2024, 1, 1),
        end=date(2024, 6, 28),
    )

    svc = SipService()
    result = svc.run(_inline_strategy(), price_panel=panel)

    assert isinstance(result, SipRunResult)
    assert result.strategy_id == "fixture-sip"
    assert result.data_source == DATA_SOURCE_FIXTURE
    assert result.metrics.n_sips == 6  # Jan–Jun day 15
    assert result.metrics.total_invested == pytest.approx(6000.0)
    assert result.xirr is not None
    assert result.metrics.xirr_status == "ok"
    assert len(result.cashflows) == result.metrics.n_sips + 1  # + terminal
    assert result.cashflows[0].amount < 0
    assert result.cashflows[-1].kind == "terminal"
    assert result.cashflows[-1].amount > 0
    assert result.units_end
    assert result.market_value
    # must not look like v0 rebalance backtest
    assert "XIRR" in result.notes or "xirr" in result.notes.lower() or "SIP" in result.notes
    assert any("fixture" in w or "demo" in w for w in result.warnings)


def test_sip_service_price_rows_injection():
    """price_rows path (no PricePanel object) still works offline."""
    sessions = _weekdays(date(2024, 1, 1), date(2024, 3, 29))
    rows = _fixture_rows(["AAA", "BBB"], sessions, source="sample")
    svc = SipService()
    result = svc.run(
        _inline_strategy(
            sip={
                "amount": 2000.0,
                "day_of_month": 15,
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
            }
        ),
        price_rows=rows,
    )
    assert result.data_source == DATA_SOURCE_SAMPLE
    assert result.metrics.n_sips == 3
    assert result.metrics.total_invested == pytest.approx(6000.0)


def test_sip_service_missing_all_symbols_raises():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 2, 28))
    rows = _fixture_rows(["ZZZ"], sessions, source="fixture")
    panel = build_price_panel_from_rows(rows, ["AAA", "BBB"])
    svc = SipService()
    with pytest.raises(SipServiceError, match="no price history"):
        svc.run(_inline_strategy(), price_panel=panel)


def test_sip_service_partial_missing_renormalizes():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 3, 29))
    rows = _fixture_rows(["AAA"], sessions, source="fixture")
    panel = build_price_panel_from_rows(rows, ["AAA", "BBB"])
    svc = SipService()
    result = svc.run(_inline_strategy(), price_panel=panel)
    assert "BBB" not in result.units_end
    assert "AAA" in result.units_end
    assert any("missing_symbols" in w or "renormalized" in w for w in result.warnings)


def test_sip_service_weekend_sip_rolls_forward():
    """day_of_month=15 in June 2024 is Saturday → Monday 17."""
    sessions = _weekdays(date(2024, 6, 1), date(2024, 6, 30))
    rows = _fixture_rows(["AAA", "BBB"], sessions, source="fixture")
    panel = build_price_panel_from_rows(rows, ["AAA", "BBB"])
    svc = SipService()
    result = svc.run(
        _inline_strategy(
            sip={
                "amount": 1000.0,
                "day_of_month": 15,
                "start_date": "2024-06-01",
                "end_date": "2024-06-30",
                "as_of": "2024-06-28",
            }
        ),
        price_panel=panel,
    )
    assert result.invest_dates == [date(2024, 6, 17)]
    assert result.metrics.n_sips == 1


def test_sip_service_invalid_strategy():
    svc = SipService()
    with pytest.raises(SipServiceError):
        svc.run({"strategy_id": "bad", "name": "x"})  # missing basket/sip


def test_sip_service_from_example_yaml_with_fixture_panel():
    """Example strategy symbols with synthetic fixture prices (no curated I/O)."""
    assert EXAMPLE_YAML.is_file()
    cfg = strategy_config_from_dict(
        {
            **_inline_strategy(),
            "strategy_id": "example-like",
            "name": "Example-like",
            "basket": {
                "kind": "inline",
                "constituents": [
                    {"symbol": "TCS", "target_weight": 0.25},
                    {"symbol": "INFY", "target_weight": 0.25},
                    {"symbol": "RELIANCE", "target_weight": 0.25},
                    {"symbol": "HDFCBANK", "target_weight": 0.25},
                ],
            },
            "sip": {
                "amount": 5000.0,
                "day_of_month": 5,
                "start_date": "2023-01-01",
                "end_date": "2023-06-30",
            },
        }
    )
    symbols = list(cfg.resolved_weights().keys())
    sessions = _weekdays(date(2023, 1, 1), date(2023, 6, 30))
    rows = _fixture_rows(symbols, sessions, source="fixture")
    panel = build_price_panel_from_rows(rows, symbols)

    result = SipService().run(cfg, price_panel=panel)
    assert result.metrics.n_sips == 6
    assert result.xirr is not None
    assert abs(result.metrics.total_invested - 30000.0) < 1e-6


def test_load_price_panel_from_curated_if_present():
    """Optional: curated sample prices (local FS, still no network)."""
    # Uses repo curated Parquet if pipeline has been run; skip if missing.
    try:
        panel = load_price_panel(
            ["TCS", "INFY"],
            start=date(2023, 1, 1),
            end=date(2023, 3, 31),
            require_table=True,
        )
    except Exception as exc:
        pytest.skip(f"curated prices unavailable: {exc}")
    assert panel.data_source in {
        DATA_SOURCE_SAMPLE,
        DATA_SOURCE_UPSTOX,
        DATA_SOURCE_FIXTURE,
        "mixed",
        "unknown",
    }
    if panel.by_symbol:
        assert "TCS" in panel.by_symbol or "INFY" in panel.by_symbol
