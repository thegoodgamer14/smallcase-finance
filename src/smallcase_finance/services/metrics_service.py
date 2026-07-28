"""Summary metrics orchestration (wraps calc.risk + curated snapshots)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from smallcase_finance.calc.risk import metrics_from_nav
from smallcase_finance.config import DEFAULT_CURRENCY, DEFAULT_RF, PERIODS_PER_YEAR
from smallcase_finance.data_access import smallcases as sc_da
from smallcase_finance.data_access.performance import get_metrics_snapshot, get_nav_series
from smallcase_finance.schemas.common import MetricsAssumptions, MetricWindow
from smallcase_finance.schemas.metrics import MetricValues, MetricsResponse


class MetricsService:
    def get_metrics(
        self,
        smallcase_id: str,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
        window: MetricWindow = MetricWindow.itd,
    ) -> MetricsResponse:
        sc = sc_da.get_smallcase(smallcase_id)
        sid = sc["smallcase_id"]
        currency = sc.get("currency") or DEFAULT_CURRENCY

        assumptions = MetricsAssumptions(
            periods_per_year=PERIODS_PER_YEAR,
            risk_free_rate=DEFAULT_RF,
            return_type="simple",
            price_field="close",
        )

        # Prefer curated snapshot for named windows when no custom range override
        use_snapshot = window != MetricWindow.custom and start is None and end is None
        if use_snapshot:
            snap = get_metrics_snapshot(sid, window=window.value)
            if snap is not None:
                return MetricsResponse(
                    smallcase_id=sid,
                    start=snap.get("start_date"),
                    end=snap.get("end_date"),
                    window=window,
                    currency=currency,
                    metrics=MetricValues(
                        cagr=snap.get("cagr"),
                        volatility=snap.get("volatility"),
                        max_drawdown=snap.get("max_drawdown"),
                        sharpe=snap.get("sharpe"),
                        total_return=snap.get("total_return"),
                        n_observations=snap.get("n_obs"),
                    ),
                    assumptions=assumptions.model_copy(
                        update={"risk_free_rate": snap.get("rf_rate") or DEFAULT_RF}
                    ),
                )

        # Compute from NAV series via calc.risk
        rows = get_nav_series(sid, start=start, end=end)
        if not rows:
            return MetricsResponse(
                smallcase_id=sid,
                start=start,
                end=end,
                window=window if start is None else MetricWindow.custom,
                currency=currency,
                metrics=MetricValues(n_observations=0),
                assumptions=assumptions,
            )

        nav = [float(r["nav"]) for r in rows]
        dates = [r["date"] for r in rows]
        daily = [r.get("daily_return") for r in rows]
        # drop first-day synthetic 0 for vol/sharpe if present
        if daily and daily[0] is not None and float(daily[0]) == 0.0:
            daily = [None] + list(daily[1:])

        m = metrics_from_nav(
            nav,
            dates=dates,
            daily_returns=daily,
            periods_per_year=float(PERIODS_PER_YEAR),
            risk_free_rate=DEFAULT_RF,
        )
        resolved_window = (
            window
            if start is None and end is None
            else MetricWindow.custom
        )
        return MetricsResponse(
            smallcase_id=sid,
            start=dates[0],
            end=dates[-1],
            window=resolved_window,
            currency=currency,
            metrics=MetricValues(
                cagr=m.get("cagr"),  # type: ignore[arg-type]
                volatility=m.get("volatility"),  # type: ignore[arg-type]
                max_drawdown=m.get("max_drawdown"),  # type: ignore[arg-type]
                sharpe=m.get("sharpe"),  # type: ignore[arg-type]
                total_return=m.get("total_return"),  # type: ignore[arg-type]
                n_observations=int(m["n_observations"] or 0),
            ),
            assumptions=assumptions,
        )
