"""Lightweight derived tables for demo (NAV, metrics, contribution).

Not a full calc engine — backend ``calc/`` may recompute with richer logic later.
Gap policy: exclude symbols missing a return that day; renormalize remaining weights.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone
from typing import Optional

import polars as pl

from smallcase_finance.config import DEFAULT_RF, PERIODS_PER_YEAR

logger = logging.getLogger(__name__)

NAV_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "date": pl.Date,
    "nav": pl.Float64,
    "daily_return": pl.Float64,
    "cum_return": pl.Float64,
    "n_constituents": pl.Int64,
    "computed_at": pl.Datetime("us", "UTC"),
}

METRICS_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "as_of": pl.Date,
    "window": pl.Utf8,
    "start_date": pl.Date,
    "end_date": pl.Date,
    "n_obs": pl.Int64,
    "total_return": pl.Float64,
    "cagr": pl.Float64,
    "volatility": pl.Float64,
    "max_drawdown": pl.Float64,
    "sharpe": pl.Float64,
    "sortino": pl.Float64,
    "calmar": pl.Float64,
    "rf_rate": pl.Float64,
    "computed_at": pl.Datetime("us", "UTC"),
}

CONTRIB_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "period_start": pl.Date,
    "period_end": pl.Date,
    "symbol": pl.Utf8,
    "avg_weight": pl.Float64,
    "weight_start": pl.Float64,
    "weight_end": pl.Float64,
    "symbol_return": pl.Float64,
    "contribution": pl.Float64,
    "computed_at": pl.Datetime("us", "UTC"),
}


def _weights_on(
    constituents: pl.DataFrame,
    smallcase_id: str,
    d: date,
) -> dict[str, float]:
    """Active version = max effective_from <= d with open/closed range containing d."""
    sub = constituents.filter(pl.col("smallcase_id") == smallcase_id)
    if sub.height == 0:
        return {}
    rows = sub.to_dicts()
    candidates = [
        r
        for r in rows
        if r["effective_from"] <= d
        and (r["effective_to"] is None or r["effective_to"] >= d)
    ]
    if not candidates:
        return {}
    max_from = max(r["effective_from"] for r in candidates)
    version = [r for r in candidates if r["effective_from"] == max_from]
    return {r["symbol"]: float(r["target_weight"]) for r in version}


def build_nav_series(
    *,
    smallcases: pl.DataFrame,
    constituents: pl.DataFrame,
    prices: pl.DataFrame,
    price_field: str = "close",
) -> pl.DataFrame:
    """Full rebuild of nav_series for all smallcases."""
    computed_at = datetime.now(timezone.utc)
    if smallcases.height == 0 or prices.height == 0:
        return pl.DataFrame(schema=NAV_SCHEMA)

    # pivot closes: date x symbol
    px = prices.select(["symbol", "date", price_field]).rename({price_field: "px"})
    px = px.unique(subset=["symbol", "date"], keep="last")

    all_nav_rows: list[dict] = []
    gap_log: list[str] = []

    for sc in smallcases.to_dicts():
        sid = sc["smallcase_id"]
        base_nav = float(sc["base_nav"] or 100.0)
        inception: Optional[date] = sc.get("inception_date")

        # trading calendar = union of dates with any price for constituents of this sc
        c_syms = set(
            constituents.filter(pl.col("smallcase_id") == sid)["symbol"].to_list()
        )
        if not c_syms:
            logger.warning("no constituents for %s — skip NAV", sid)
            continue
        cal = (
            px.filter(pl.col("symbol").is_in(list(c_syms)))
            .select("date")
            .unique()
            .sort("date")
        )
        dates = cal["date"].to_list()
        if inception is not None:
            dates = [d for d in dates if d >= inception]
        if not dates:
            continue

        # map symbol -> {date: px}
        price_map: dict[str, dict[date, float]] = {}
        for sym in c_syms:
            sub = px.filter(pl.col("symbol") == sym)
            price_map[sym] = {
                row["date"]: float(row["px"]) for row in sub.to_dicts()
            }

        nav = base_nav
        prev_prices: dict[str, float] = {}
        first = True

        for d in dates:
            w = _weights_on(constituents, sid, d)
            if not w:
                continue
            # build returns for symbols with both prev and today price
            port_ret = 0.0
            used_w = 0.0
            n_used = 0
            for sym, weight in w.items():
                today = price_map.get(sym, {}).get(d)
                if today is None:
                    gap_log.append(f"{sid} {d} missing price {sym}")
                    continue
                if first:
                    prev_prices[sym] = today
                    used_w += weight
                    n_used += 1
                    continue
                prev = prev_prices.get(sym)
                if prev is None or prev <= 0:
                    # first time seeing this symbol mid-stream: seed, no return
                    prev_prices[sym] = today
                    gap_log.append(f"{sid} {d} seed {sym} (no prior)")
                    continue
                r_i = today / prev - 1.0
                port_ret += weight * r_i
                used_w += weight
                n_used += 1
                prev_prices[sym] = today

            if first:
                daily_ret = 0.0
                first = False
            else:
                if used_w <= 0:
                    daily_ret = 0.0
                elif abs(used_w - 1.0) > 1e-9:
                    # renormalize contribution of available weights
                    daily_ret = port_ret / used_w
                else:
                    daily_ret = port_ret
                nav = nav * (1.0 + daily_ret)

            all_nav_rows.append(
                {
                    "smallcase_id": sid,
                    "date": d,
                    "nav": nav,
                    "daily_return": daily_ret,
                    "cum_return": nav / base_nav - 1.0,
                    "n_constituents": n_used,
                    "computed_at": computed_at,
                }
            )

    if gap_log:
        logger.info("NAV gap log: %d events (showing up to 5): %s", len(gap_log), gap_log[:5])

    if not all_nav_rows:
        return pl.DataFrame(schema=NAV_SCHEMA)

    df = pl.DataFrame(all_nav_rows).with_columns(
        pl.col("n_constituents").cast(pl.Int64),
        pl.col("computed_at").cast(pl.Datetime("us", "UTC")),
    )
    return df.select(list(NAV_SCHEMA.keys())).sort(["smallcase_id", "date"])


def _max_drawdown(navs: list[float]) -> float:
    if not navs:
        return 0.0
    peak = navs[0]
    mdd = 0.0
    for v in navs:
        if v > peak:
            peak = v
        if peak > 0:
            dd = v / peak - 1.0
            if dd < mdd:
                mdd = dd
    return mdd


def _window_start(as_of: date, window: str, itd_start: date) -> Optional[date]:
    from datetime import timedelta

    if window == "ITD":
        return itd_start
    if window == "YTD":
        return date(as_of.year, 1, 1)
    days = {"1M": 30, "3M": 91, "6M": 182, "1Y": 365}.get(window)
    if days is None:
        return None
    return as_of - timedelta(days=days)


def build_metrics_snapshot(
    nav: pl.DataFrame,
    *,
    windows: tuple[str, ...] = ("1M", "3M", "6M", "1Y", "YTD", "ITD"),
    rf_rate: float = DEFAULT_RF,
) -> pl.DataFrame:
    computed_at = datetime.now(timezone.utc)
    if nav.height == 0:
        return pl.DataFrame(schema=METRICS_SCHEMA)

    rows: list[dict] = []
    for sid in nav["smallcase_id"].unique().to_list():
        sub = nav.filter(pl.col("smallcase_id") == sid).sort("date")
        dates = sub["date"].to_list()
        navs = sub["nav"].to_list()
        rets = sub["daily_return"].to_list()
        as_of = dates[-1]
        itd_start = dates[0]

        for window in windows:
            start = _window_start(as_of, window, itd_start)
            if start is None:
                continue
            # slice by date
            idx = [i for i, d in enumerate(dates) if start <= d <= as_of]
            if not idx:
                continue
            # drop first daily_return if it is the series start (often 0) —
            # use all returns in window except we keep them as stored
            w_navs = [navs[i] for i in idx]
            w_rets = [rets[i] for i in idx]
            # total return from first to last nav in window
            total_return = w_navs[-1] / w_navs[0] - 1.0 if w_navs[0] else 0.0
            n_obs = len(w_rets)
            years = n_obs / PERIODS_PER_YEAR if n_obs else 0.0
            cagr = None
            if years >= 1 / 12 and w_navs[0] > 0:  # at least ~1 month
                cagr = (w_navs[-1] / w_navs[0]) ** (1.0 / years) - 1.0

            vol = None
            if n_obs >= 2:
                mean = sum(w_rets) / n_obs
                var = sum((x - mean) ** 2 for x in w_rets) / (n_obs - 1)
                vol = math.sqrt(var) * math.sqrt(PERIODS_PER_YEAR)

            mdd = _max_drawdown(w_navs)
            sharpe = None
            if cagr is not None and vol and vol > 0:
                sharpe = (cagr - rf_rate) / vol

            sortino = None
            if n_obs >= 2:
                downside = [min(x, 0.0) for x in w_rets]
                dvar = sum(x * x for x in downside) / (n_obs - 1)
                dvol = math.sqrt(dvar) * math.sqrt(PERIODS_PER_YEAR)
                if cagr is not None and dvol > 0:
                    sortino = (cagr - rf_rate) / dvol

            calmar = None
            if cagr is not None and mdd < 0:
                calmar = cagr / abs(mdd)

            rows.append(
                {
                    "smallcase_id": sid,
                    "as_of": as_of,
                    "window": window,
                    "start_date": dates[idx[0]],
                    "end_date": as_of,
                    "n_obs": n_obs,
                    "total_return": total_return,
                    "cagr": cagr,
                    "volatility": vol,
                    "max_drawdown": mdd,
                    "sharpe": sharpe,
                    "sortino": sortino,
                    "calmar": calmar,
                    "rf_rate": rf_rate,
                    "computed_at": computed_at,
                }
            )

    if not rows:
        return pl.DataFrame(schema=METRICS_SCHEMA)
    df = pl.DataFrame(rows)
    df = df.with_columns(
        pl.col("n_obs").cast(pl.Int64),
        pl.col("computed_at").cast(pl.Datetime("us", "UTC")),
    )
    return df.select(list(METRICS_SCHEMA.keys())).sort(
        ["smallcase_id", "as_of", "window"]
    )


def build_contribution(
    *,
    smallcases: pl.DataFrame,
    constituents: pl.DataFrame,
    prices: pl.DataFrame,
    nav: pl.DataFrame,
    price_field: str = "close",
) -> pl.DataFrame:
    """Simple ITD contribution: avg_weight * symbol_return over full NAV span."""
    computed_at = datetime.now(timezone.utc)
    if nav.height == 0 or prices.height == 0:
        return pl.DataFrame(schema=CONTRIB_SCHEMA)

    px = prices.select(["symbol", "date", price_field]).rename({price_field: "px"})
    rows: list[dict] = []

    for sc in smallcases.to_dicts():
        sid = sc["smallcase_id"]
        sub_nav = nav.filter(pl.col("smallcase_id") == sid).sort("date")
        if sub_nav.height < 2:
            continue
        period_start = sub_nav["date"][0]
        period_end = sub_nav["date"][-1]

        # use latest constituent version as of period_end for weights
        w = _weights_on(constituents, sid, period_end)
        w_start = _weights_on(constituents, sid, period_start)
        if not w:
            continue

        for sym, weight in w.items():
            s_px = (
                px.filter(pl.col("symbol") == sym)
                .filter(
                    (pl.col("date") >= period_start) & (pl.col("date") <= period_end)
                )
                .sort("date")
            )
            if s_px.height < 2:
                continue
            p0 = float(s_px["px"][0])
            p1 = float(s_px["px"][-1])
            if p0 <= 0:
                continue
            sym_ret = p1 / p0 - 1.0
            avg_w = (weight + w_start.get(sym, weight)) / 2.0
            rows.append(
                {
                    "smallcase_id": sid,
                    "period_start": period_start,
                    "period_end": period_end,
                    "symbol": sym,
                    "avg_weight": avg_w,
                    "weight_start": w_start.get(sym),
                    "weight_end": weight,
                    "symbol_return": sym_ret,
                    "contribution": avg_w * sym_ret,
                    "computed_at": computed_at,
                }
            )

    if not rows:
        return pl.DataFrame(schema=CONTRIB_SCHEMA)
    df = pl.DataFrame(rows).with_columns(
        pl.col("computed_at").cast(pl.Datetime("us", "UTC"))
    )
    return df.select(list(CONTRIB_SCHEMA.keys())).sort(
        ["smallcase_id", "period_start", "period_end", "symbol"]
    )
