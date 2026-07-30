"""Portfolio snapshot normalize + service (mocked Kite)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from smallcase_finance.data_access.portfolio import (
    holdings_to_rows,
    read_latest_snapshot,
    write_snapshot_rows,
)
from smallcase_finance.integrations.kite.client import KiteClient, KiteHolding
from smallcase_finance.services.portfolio_service import (
    PortfolioService,
    PortfolioServiceError,
)


def test_holdings_to_rows_weights():
    holdings = [
        KiteHolding(
            tradingsymbol="INFY",
            exchange="NSE",
            quantity=10,
            average_price=1000.0,
            last_price=1500.0,
            pnl=5000.0,
            product="CNC",
            isin=None,
            instrument_token=1,
        ),
        KiteHolding(
            tradingsymbol="TCS",
            exchange="NSE",
            quantity=5,
            average_price=3000.0,
            last_price=3000.0,
            pnl=0.0,
            product="CNC",
            isin=None,
            instrument_token=2,
        ),
    ]
    rows = holdings_to_rows(holdings, snapshot_id="snap1")
    assert len(rows) == 2
    total = sum(r["value"] for r in rows)
    assert total == 10 * 1500 + 5 * 3000
    assert abs(sum(r["weight"] for r in rows) - 1.0) < 1e-9


def test_write_read_snapshot(tmp_path: Path):
    rows = holdings_to_rows(
        [
            {
                "tradingsymbol": "INFY",
                "exchange": "NSE",
                "quantity": 1,
                "last_price": 100.0,
            }
        ],
        snapshot_id="s1",
        synced_at=datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc),
    )
    write_snapshot_rows(rows, curated_root=tmp_path)
    snap = read_latest_snapshot(curated_root=tmp_path)
    assert snap is not None
    assert snap["snapshot_id"] == "s1"
    assert len(snap["rows"]) == 1


class _HoldingsTransport:
    def get(self, url, headers=None, timeout=None):
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": [
                    {
                        "tradingsymbol": "INFY",
                        "exchange": "NSE",
                        "quantity": 2,
                        "average_price": 1000,
                        "last_price": 1100,
                        "pnl": 200,
                        "product": "CNC",
                        "isin": "INE009A01021",
                        "instrument_token": 408065,
                    }
                ],
            },
        )


def test_portfolio_refresh_mocked(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "smallcase_finance.services.portfolio_service.kite_session_configured",
        lambda: True,
    )
    client = KiteClient(
        api_key="k",
        access_token="t",
        transport=_HoldingsTransport(),  # type: ignore[arg-type]
    )
    svc = PortfolioService(curated_root=tmp_path, kite_client=client)
    res = svc.refresh()
    assert res.position_count == 1
    assert res.holdings[0].symbol == "INFY"
    assert res.total_value == 2200.0

    latest = svc.latest()
    assert latest.snapshot_id == res.snapshot_id


def test_portfolio_no_snapshot(tmp_path: Path):
    svc = PortfolioService(curated_root=tmp_path)
    with pytest.raises(PortfolioServiceError) as ei:
        svc.latest()
    assert ei.value.error_code == "NO_SNAPSHOT"
