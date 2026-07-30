"""Smoke tests against curated sample data (requires data/curated Parquet)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from smallcase_finance.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "version" in body
    assert "data_reachable" in body


def test_portfolio_status_no_secrets():
    r = client.get("/portfolio/status")
    assert r.status_code == 200
    body = r.json()
    assert "kite_app_configured" in body
    assert "kite_session_configured" in body
    assert "has_snapshot" in body
    # Never leak tokens
    blob = str(body).lower()
    assert "access_token" not in blob
    assert "api_secret" not in blob


def test_portfolio_holdings_404_without_snapshot():
    # Without a personal snapshot, latest may 404 — both OK depending on env
    r = client.get("/portfolio/holdings/latest")
    assert r.status_code in (200, 404)


def test_decisions_price_coverage():
    r = client.get("/decisions/price-coverage", params={"symbols": "INFY,TCS"})
    assert r.status_code == 200
    body = r.json()
    assert "symbols" in body
    assert "data_source" in body


def test_cors_allows_next_origin():
    r = client.options(
        "/smallcases",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette CORS responds 200 on preflight when origin allowed
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_list_and_detail():
    r = client.get("/smallcases")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    sid = items[0]["id"]

    r = client.get(f"/smallcases/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_holdings_weights_are_fractions():
    r = client.get("/smallcases/digital-india/holdings")
    assert r.status_code == 200
    body = r.json()
    assert body["weight_sum"] == 1.0 or abs(body["weight_sum"] - 1.0) < 1e-5
    for h in body["holdings"]:
        assert 0 <= h["weight"] <= 1


def test_nav_and_performance():
    r = client.get("/smallcases/digital-india/nav?latest_only=true")
    assert r.status_code == 200
    assert r.json()["nav"] > 0

    r = client.get(
        "/smallcases/digital-india/performance",
        params={"start": "2023-01-02", "end": "2023-01-10"},
    )
    assert r.status_code == 200
    assert len(r.json()["series"]) >= 1


def test_metrics_itd():
    r = client.get("/smallcases/digital-india/metrics", params={"window": "ITD"})
    assert r.status_code == 200
    body = r.json()
    assert "assumptions" in body
    assert body["assumptions"]["periods_per_year"] == 252
    assert body["metrics"]["n_observations"] is not None


def test_metrics_custom_date_range():
    r = client.get(
        "/smallcases/digital-india/metrics",
        params={"start": "2023-06-01", "end": "2024-06-01"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["window"] in ("custom", "ITD", "1Y", "6M", "3M", "1M", "YTD")
    assert body["start"] <= body["end"]


def test_upstox_status_configured_boolean_only():
    """Status reports credential readiness as a boolean — never secrets."""
    r = client.get("/integrations/upstox/status")
    assert r.status_code == 200
    body = r.json()
    assert "configured" in body
    assert isinstance(body["configured"], bool)
    assert "default_years" in body
    assert body["provider"] == "upstox"
    # Must not echo any secret field
    for k in body:
        assert "token" not in k.lower() or k == "configured"
    assert "access_token" not in body
    assert "api_key" not in body
    assert "api_secret" not in body
    # Values must not look like leaked secrets
    for v in body.values():
        if isinstance(v, str):
            assert "Bearer " not in v
            assert not v.startswith("eyJ")  # JWT-ish



def test_upstox_sync_http_disabled_by_default():
    r = client.post("/integrations/upstox/sync", json={"years": 1})
    assert r.status_code == 403


def test_upstox_lookback_preview():
    r = client.get(
        "/integrations/upstox/lookback-preview",
        params={"from_date": "2022-01-01", "to_date": "2023-01-01"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["from_date"] == "2022-01-01"
    assert body["to_date"] == "2023-01-01"


def test_attribution():
    r = client.get("/smallcases/digital-india/attribution")
    assert r.status_code == 200
    body = r.json()
    assert body["smallcase_id"] == "digital-india"
    # Sample pipeline writes contribution rows for digital-india
    assert isinstance(body["items"], list)
    if body["items"]:
        item = body["items"][0]
        assert "symbol" in item
        assert "contribution" in item
        assert 0 <= item["avg_weight"] <= 1


def test_backtest_summary():
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
    assert body["smallcase_id"] == "digital-india"
    assert len(body["nav_series"]) >= 2
    assert body["nav_series"][0]["nav"] == 100.0
    assert "metrics" in body
    assert body["metrics"]["n_observations"] is not None
    assert "params" in body
    assert body["params"]["rebalance_rule"] == "monthly"


def test_unknown_smallcase_404():
    r = client.get("/smallcases/does-not-exist")
    assert r.status_code == 404


def test_bad_date_range_400():
    r = client.get(
        "/smallcases/digital-india/performance",
        params={"start": "2025-01-01", "end": "2020-01-01"},
    )
    assert r.status_code == 400
