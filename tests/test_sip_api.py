"""Smoke tests for SIP Lab API: strategies + POST /backtests/sip.

Uses curated sample prices when present; also covers inline strategy path
and validation errors. Never asserts secrets.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from smallcase_finance.main import app

client = TestClient(app)


def test_list_strategies_includes_example():
    r = client.get("/strategies")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert len(body["items"]) >= 1
    ids = {it["id"] for it in body["items"]}
    assert "example-sip-equity" in ids
    item = next(it for it in body["items"] if it["id"] == "example-sip-equity")
    assert item["name"]
    assert item["sip_amount"] > 0
    assert 1 <= item["day_of_month"] <= 28
    assert "currency" in item
    # No secrets
    blob = r.text.lower()
    assert "access_token" not in blob
    assert "api_secret" not in blob
    assert "bearer " not in blob


def test_get_strategy_detail():
    r = client.get("/strategies/example-sip-equity")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "example-sip-equity"
    assert body["basket"]["kind"] == "inline"
    assert len(body["basket"]["constituents"]) >= 1
    assert body["sip"]["amount"] > 0
    assert body["sip"]["day_of_month"] == 5
    assert body["costs"]["brokerage_bps"] == 0
    assert "source_path" in body


def test_get_strategy_unknown_404():
    r = client.get("/strategies/does-not-exist-xyz")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_get_strategy_path_traversal_404():
    r = client.get("/strategies/../secrets")
    assert r.status_code in (404, 422)


def test_sip_backtest_missing_strategy_400():
    r = client.post("/backtests/sip", json={})
    assert r.status_code == 422  # pydantic validation


def test_sip_backtest_unknown_strategy_404():
    r = client.post(
        "/backtests/sip",
        json={"strategy_id": "no-such-strategy", "start": "2023-01-01", "end": "2023-06-30"},
    )
    assert r.status_code == 404
    assert "detail" in r.json()


def test_sip_backtest_invalid_day_400():
    r = client.post(
        "/backtests/sip",
        json={
            "strategy_id": "example-sip-equity",
            "day_of_month": 31,
            "start": "2023-01-01",
            "end": "2023-03-31",
        },
    )
    assert r.status_code == 422


def test_sip_backtest_file_strategy_sample_prices():
    """Happy path: example strategy + curated sample prices (demo-labeled)."""
    r = client.post(
        "/backtests/sip",
        json={
            "strategy_id": "example-sip-equity",
            "amount": 5000,
            "day_of_month": 5,
            "start": "2023-01-01",
            "end": "2023-06-30",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["strategy_id"] == "example-sip-equity"
    assert "xirr" in body
    assert body["total_invested"] > 0
    assert body["final_value"] > 0
    assert body["n_sips"] >= 1
    assert isinstance(body["series"], list) and len(body["series"]) >= 1
    assert isinstance(body["cashflows"], list) and len(body["cashflows"]) >= 2
    # contributions negative, terminal positive
    assert body["cashflows"][0]["amount"] < 0
    assert body["cashflows"][-1]["amount"] > 0
    assert body["cashflows"][-1]["kind"] == "terminal"
    assert body["data_source"] in ("sample", "upstox", "fixture", "mixed", "unknown")
    assert "assumptions" in body
    assert body["assumptions"]["costs_zero"] is True
    assert body["assumptions"]["primary_metric"] == "xirr"
    assert body["assumptions"]["not_v0_rebalance"] is True
    assert isinstance(body["warnings"], list)
    # max_drawdown present (may be 0 or negative)
    assert "max_drawdown" in body
    # no secrets
    for k in body:
        assert "token" not in k.lower() or k == "data_source"
    assert "access_token" not in body
    assert "api_secret" not in body


def test_sip_backtest_inline_strategy():
    """Inline strategy with symbols present in sample curated prices."""
    r = client.post(
        "/backtests/sip",
        json={
            "strategy": {
                "strategy_id": "inline-api-smoke",
                "name": "Inline API Smoke",
                "basket": {
                    "kind": "inline",
                    "constituents": [
                        {"symbol": "TCS", "target_weight": 0.5},
                        {"symbol": "INFY", "target_weight": 0.5},
                    ],
                },
                "sip": {
                    "amount": 2000,
                    "day_of_month": 15,
                    "start_date": "2023-01-01",
                    "end_date": "2023-03-31",
                },
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["strategy_id"] == "inline-api-smoke"
    assert body["total_invested"] == 6000.0  # 3 months × 2000
    assert body["n_sips"] == 3
    assert body["final_value"] > 0
    assert body["data_source"] in ("sample", "upstox", "fixture", "mixed", "unknown")
    # series points have expected keys
    pt = body["series"][0]
    assert "date" in pt and "market_value" in pt


def test_sip_backtest_invalid_inline_weights_400():
    r = client.post(
        "/backtests/sip",
        json={
            "strategy": {
                "strategy_id": "bad-weights",
                "name": "Bad Weights",
                "basket": {
                    "kind": "inline",
                    "constituents": [
                        {"symbol": "TCS", "target_weight": 0.3},
                        {"symbol": "INFY", "target_weight": 0.3},
                    ],
                },
                "sip": {
                    "amount": 1000,
                    "day_of_month": 5,
                    "start_date": "2023-01-01",
                    "end_date": "2023-03-31",
                },
            }
        },
    )
    assert r.status_code == 400
    assert "detail" in r.json()


def test_sip_backtest_bad_date_range_422_or_400():
    r = client.post(
        "/backtests/sip",
        json={
            "strategy_id": "example-sip-equity",
            "start": "2024-01-01",
            "end": "2023-01-01",
        },
    )
    assert r.status_code in (400, 422)


def test_existing_backtest_route_untouched():
    """v0 POST /backtest must still work (not repurposed as SIP)."""
    r = client.post(
        "/backtest",
        json={
            "smallcase_id": "digital-india",
            "start": "2023-01-02",
            "end": "2023-06-30",
            "rebalance_rule": "monthly",
            "initial_nav": 100.0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "nav_series" in body
    assert "xirr" not in body  # SIP-only field
