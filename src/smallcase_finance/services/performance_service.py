"""Performance, NAV series, and simple attribution orchestration."""

from __future__ import annotations

from datetime import date
from typing import Optional, Union

from smallcase_finance.config import DEFAULT_CURRENCY
from smallcase_finance.data_access import smallcases as sc_da
from smallcase_finance.data_access.performance import (
    get_contribution,
    get_latest_nav,
    get_nav_series,
)
from smallcase_finance.schemas.attribution import AttributionItem, AttributionResponse
from smallcase_finance.schemas.nav import NavLatestResponse, NavPointDTO, NavSeriesResponse
from smallcase_finance.schemas.performance import PerformancePoint, PerformanceResponse


class PerformanceService:
    def get_performance(
        self,
        smallcase_id: str,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
        benchmark: bool = False,
        freq: str = "D",
    ) -> PerformanceResponse:
        sc = sc_da.get_smallcase(smallcase_id)
        sid = sc["smallcase_id"]
        currency = sc.get("currency") or DEFAULT_CURRENCY

        rows = get_nav_series(sid, start=start, end=end)
        # TODO: if empty, recompute from constituents × prices via calc/
        # (see docs/architecture/backend.md §6.5 source priority)

        series: list[PerformancePoint] = []
        for i, r in enumerate(rows):
            d = r["date"]
            nav = float(r["nav"])
            dr = r.get("daily_return")
            # First point: expose null daily_return when value is exactly 0.0
            # and it is the series start (common pipeline convention).
            if i == 0 and dr is not None and float(dr) == 0.0:
                daily = None
            else:
                daily = float(dr) if dr is not None else None
            series.append(PerformancePoint(date=d, nav=nav, daily_return=daily))

        # freq downsampling placeholder — daily only in v0
        _ = freq
        # benchmark reserved
        _ = benchmark
        benchmark_series = None

        series_start = series[0].date if series else start
        series_end = series[-1].date if series else end

        return PerformanceResponse(
            smallcase_id=sid,
            currency=currency,
            start=series_start,
            end=series_end,
            series=series,
            benchmark_series=benchmark_series,
        )

    def get_attribution(
        self,
        smallcase_id: str,
        *,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> AttributionResponse:
        """Simple contribution from curated table (graceful empty if missing)."""
        sc = sc_da.get_smallcase(smallcase_id)
        sid = sc["smallcase_id"]

        rows = get_contribution(
            sid, period_start=period_start, period_end=period_end
        )
        residual_row = None
        symbol_rows: list[dict] = []
        for r in rows:
            if str(r.get("symbol")) == "_RESIDUAL":
                residual_row = r
            else:
                symbol_rows.append(r)

        symbols = [str(r["symbol"]) for r in symbol_rows]
        instruments = sc_da.get_instruments(symbols) if symbols else {}

        items: list[AttributionItem] = []
        for r in symbol_rows:
            sym = str(r["symbol"])
            inst = instruments.get(sym, {})
            ws = r.get("weight_start")
            we = r.get("weight_end")
            items.append(
                AttributionItem(
                    symbol=sym,
                    name=inst.get("name"),
                    avg_weight=float(r.get("avg_weight") or 0.0),
                    weight_start=float(ws) if ws is not None else None,
                    weight_end=float(we) if we is not None else None,
                    symbol_return=float(r.get("symbol_return") or 0.0),
                    contribution=float(r.get("contribution") or 0.0),
                )
            )
        # Keep contribution desc (data_access already sorts; residual stripped)
        items.sort(key=lambda x: x.contribution, reverse=True)

        ps = period_start
        pe = period_end
        if symbol_rows:
            ps = ps or symbol_rows[0].get("period_start")
            pe = pe or symbol_rows[0].get("period_end")

        residual = None
        if residual_row is not None:
            residual = float(residual_row.get("contribution") or 0.0)

        # Portfolio return ≈ sum(contrib) + residual when residual known
        port_ret = None
        if items:
            s = sum(i.contribution for i in items)
            port_ret = s + (residual or 0.0) if residual is not None else s

        return AttributionResponse(
            smallcase_id=sid,
            period_start=ps,
            period_end=pe,
            items=items,
            residual=residual,
            portfolio_return=port_ret,
        )


class NavService:
    def get_nav(
        self,
        smallcase_id: str,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
        latest_only: bool = False,
    ) -> Union[NavSeriesResponse, NavLatestResponse]:
        sc = sc_da.get_smallcase(smallcase_id)
        sid = sc["smallcase_id"]
        currency = sc.get("currency") or DEFAULT_CURRENCY

        if latest_only:
            row = get_latest_nav(sid)
            if row is None:
                # Empty-state: still 200 with no series is for full path;
                # for latest_only with no data, raise so router can 404-ish
                # Prefer empty graceful: use inception base_nav if known
                inception = sc.get("inception_date")
                base = float(sc.get("base_nav") or 100.0)
                if inception is None:
                    return NavLatestResponse(
                        smallcase_id=sid,
                        currency=currency,
                        as_of=date.today(),
                        nav=base,
                    )
                return NavLatestResponse(
                    smallcase_id=sid,
                    currency=currency,
                    as_of=inception,
                    nav=base,
                )
            return NavLatestResponse(
                smallcase_id=sid,
                currency=currency,
                as_of=row["date"],
                nav=float(row["nav"]),
            )

        rows = get_nav_series(sid, start=start, end=end)
        # TODO: on-the-fly calc when curated nav_series missing
        series = [
            NavPointDTO(date=r["date"], nav=float(r["nav"])) for r in rows
        ]
        return NavSeriesResponse(
            smallcase_id=sid,
            currency=currency,
            series=series,
        )
