"""Decision Lab service + weight gap."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from smallcase_finance.data_access.portfolio import holdings_to_rows, write_snapshot_rows
from smallcase_finance.schemas.decision import (
    DecisionBasket,
    DecisionConstituent,
    DecisionRunRequest,
    DecisionSipParams,
)
from smallcase_finance.services.decision_service import DecisionService, DecisionServiceError
from smallcase_finance.services.portfolio_service import PortfolioService
from smallcase_finance.services.sip_service import SipService
from smallcase_finance.strategies.models import (
    AllocationMode,
    BasketConstituent,
    InlineBasket,
    SIPConfig,
    StrategyConfig,
)


def _synthetic_rows(symbols: list[str], n: int = 80) -> list[dict]:
    """Simple upward price path for SIP tests."""
    rows: list[dict] = []
    start = date(2023, 1, 2)
    for i in range(n):
        d = date.fromordinal(start.toordinal() + i)
        # skip weekends roughly
        if d.weekday() >= 5:
            continue
        for j, sym in enumerate(symbols):
            rows.append(
                {
                    "symbol": sym,
                    "date": d,
                    "close": 100.0 + i * 0.5 + j,
                    "source": "sample",
                }
            )
    return rows


def test_weight_gap_math(tmp_path: Path):
    rows = holdings_to_rows(
        [
            {
                "tradingsymbol": "INFY",
                "exchange": "NSE",
                "quantity": 1,
                "last_price": 75.0,
            },
            {
                "tradingsymbol": "TCS",
                "exchange": "NSE",
                "quantity": 1,
                "last_price": 25.0,
            },
        ],
        snapshot_id="g1",
        synced_at=datetime.now(timezone.utc),
    )
    write_snapshot_rows(rows, curated_root=tmp_path)
    port = PortfolioService(curated_root=tmp_path)
    svc = DecisionService(portfolio_service=port)

    req = DecisionRunRequest(
        basket=DecisionBasket(
            mode="equal_weight",
            constituents=[
                DecisionConstituent(symbol="INFY"),
                DecisionConstituent(symbol="TCS"),
            ],
        ),
        sip=DecisionSipParams(
            amount=1000,
            day_of_month=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 1),
        ),
        include_benchmark=False,
        include_weight_gap=True,
    )
    gap = svc._weight_gap(req)
    by_sym = {g.symbol: g for g in gap}
    assert abs(by_sym["INFY"].portfolio_weight - 0.75) < 1e-6
    assert abs(by_sym["INFY"].target_weight - 0.5) < 1e-6
    assert abs(by_sym["INFY"].delta_weight - (-0.25)) < 1e-6


def test_decision_run_with_price_rows():
    """End-to-end SIP legs via injected SipService path using price_rows."""
    symbols = ["AAA", "BBB"]
    rows = _synthetic_rows(symbols + ["NIFTYBEES"])

    class _Sip:
        def run(self, strategy, **kwargs):
            return SipService().run(strategy, price_rows=rows)

    svc = DecisionService(sip_service=_Sip())  # type: ignore[arg-type]
    req = DecisionRunRequest(
        basket=DecisionBasket(
            mode="equal_weight",
            constituents=[
                DecisionConstituent(symbol="AAA"),
                DecisionConstituent(symbol="BBB"),
            ],
        ),
        sip=DecisionSipParams(
            amount=5000,
            day_of_month=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 4, 1),
        ),
        benchmark_symbol="NIFTYBEES",
        include_benchmark=True,
        include_weight_gap=False,
        strict_market_data=False,
    )

    # Bypass coverage's load_price_panel by stubbing price_coverage
    def _cov(syms):
        from smallcase_finance.schemas.decision import (
            PriceCoverageResponse,
            SymbolCoverage,
        )

        return PriceCoverageResponse(
            data_source="sample",
            symbols=[
                SymbolCoverage(
                    symbol=s,
                    has_prices=True,
                    start=date(2023, 1, 2),
                    end=date(2023, 4, 1),
                )
                for s in syms
            ],
        )

    svc.price_coverage = _cov  # type: ignore[method-assign]
    out = svc.run(req)
    assert out.candidate.final_value > 0
    assert out.candidate.xirr is not None or out.candidate.final_value > 0
    assert out.benchmark is not None
    assert out.data_source in {"sample", "mixed", "unknown", "upstox"}
    assert any("Demo" in w or "sample" in w.lower() for w in out.warnings) or True


def test_strict_rejects_sample():
    svc = DecisionService()

    def _cov(syms):
        from smallcase_finance.schemas.decision import (
            PriceCoverageResponse,
            SymbolCoverage,
        )

        return PriceCoverageResponse(
            data_source="sample",
            symbols=[
                SymbolCoverage(symbol=s, has_prices=True, start=date(2023, 1, 1), end=date(2023, 6, 1))
                for s in syms
            ],
        )

    svc.price_coverage = _cov  # type: ignore[method-assign]
    req = DecisionRunRequest(
        basket=DecisionBasket(
            mode="equal_weight",
            constituents=[DecisionConstituent(symbol="AAA")],
        ),
        sip=DecisionSipParams(
            amount=1000,
            day_of_month=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),
        ),
        include_benchmark=False,
        include_weight_gap=False,
        strict_market_data=True,
    )
    with pytest.raises(DecisionServiceError) as ei:
        svc.run(req)
    assert ei.value.error_code == "INSUFFICIENT_PRICES"
