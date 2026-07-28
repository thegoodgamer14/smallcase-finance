#!/usr/bin/env python3
"""Print a sample metrics table for curated smallcases using pure calc/.

Usage (from repo root, package installed editable or PYTHONPATH=src):

    python3 scripts/print_sample_metrics.py

Optionally writes a small summary Parquet under data/curated/metrics/ for demos:
    python3 scripts/print_sample_metrics.py --write
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

# Allow running without install: repo_root/src on path
_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from smallcase_finance.calc.rebalance import backtest_rebalance_vs_buyhold  # noqa: E402
from smallcase_finance.calc.risk import summary_metrics  # noqa: E402
from smallcase_finance.calc.returns import (  # noqa: E402
    contribution_by_symbol,
    total_return_from_prices,
)


def _curated() -> Path:
    return _REPO / "data" / "curated"


def _load() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    root = _curated()
    nav = pl.read_parquet(root / "nav" / "nav_series.parquet")
    sc = pl.read_parquet(root / "smallcases" / "smallcases.parquet")
    cons = pl.read_parquet(root / "smallcases" / "smallcase_constituents.parquet")
    px = pl.read_parquet(root / "prices" / "prices.parquet")
    return nav, sc, cons, px


def _fmt_pct(x: float | None, digits: int = 2) -> str:
    if x is None:
        return "—"
    return f"{100.0 * x:.{digits}f}%"


def _fmt_num(x: float | None, digits: int = 2) -> str:
    if x is None:
        return "—"
    return f"{x:.{digits}f}"


def metrics_for_nav(sub: pl.DataFrame, rf: float = 0.0) -> dict:
    nav = sub.sort("date")["nav"].to_list()
    rets = sub.sort("date")["daily_return"].to_list()
    m = summary_metrics(nav, rets, rf_rate=rf)
    m["start_date"] = sub["date"].min()
    m["end_date"] = sub["date"].max()
    m["start_nav"] = nav[0]
    m["end_nav"] = nav[-1]
    return m


def latest_weights(cons: pl.DataFrame, sid: str) -> dict[str, float]:
    sub = cons.filter(pl.col("smallcase_id") == sid)
    if sub.height == 0:
        return {}
    max_from = sub["effective_from"].max()
    ver = sub.filter(pl.col("effective_from") == max_from)
    return {r["symbol"]: float(r["target_weight"]) for r in ver.to_dicts()}


def simple_itd_contribution(
    cons: pl.DataFrame,
    px: pl.DataFrame,
    sid: str,
    start: object,
    end: object,
) -> list[dict]:
    w = latest_weights(cons, sid)
    rows = []
    for sym, weight in w.items():
        s_px = (
            px.filter(pl.col("symbol") == sym)
            .filter((pl.col("date") >= start) & (pl.col("date") <= end))
            .sort("date")
        )
        if s_px.height < 2:
            continue
        prices = s_px["close"].to_list()
        r = total_return_from_prices(prices)
        rows.append(
            {
                "symbol": sym,
                "weight": weight,
                "symbol_return": r,
                "contribution": weight * r,
            }
        )
    return sorted(rows, key=lambda r: r["contribution"], reverse=True)


def demo_backtest(px: pl.DataFrame, cons: pl.DataFrame, sid: str) -> None:
    w = latest_weights(cons, sid)
    if len(w) < 2:
        return
    # Align common calendar for constituents
    symbols = list(w.keys())
    wide = (
        px.filter(pl.col("symbol").is_in(symbols))
        .select(["date", "symbol", "close"])
        .pivot(on="symbol", index="date", values="close")
        .drop_nulls()
        .sort("date")
    )
    if wide.height < 30:
        print(f"  [backtest] skip {sid}: insufficient aligned prices")
        return
    prices_by = {s: wide[s].to_list() for s in symbols if s in wide.columns}
    path = backtest_rebalance_vs_buyhold(
        prices_by,
        w,
        rebalance_every=63,  # ~quarterly trading days
        start_nav=100.0,
    )
    m_rb = summary_metrics(path.nav_rebalanced, path.returns_rebalanced)
    m_bh = summary_metrics(path.nav_buy_hold, path.returns_buy_hold)
    print(f"  Backtest (quarterly rebalance vs buy-and-hold, n={wide.height}):")
    print(
        f"    Rebalanced  total={_fmt_pct(m_rb['total_return'])}  "
        f"CAGR={_fmt_pct(m_rb['cagr'])}  vol={_fmt_pct(m_rb['volatility'])}  "
        f"mdd={_fmt_pct(m_rb['max_drawdown'])}  turnover={m_rb and path.turnover_total:.3f}"
    )
    print(
        f"    Buy-hold    total={_fmt_pct(m_bh['total_return'])}  "
        f"CAGR={_fmt_pct(m_bh['cagr'])}  vol={_fmt_pct(m_bh['volatility'])}  "
        f"mdd={_fmt_pct(m_bh['max_drawdown'])}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write calc_metrics_sample.parquet under data/curated/metrics/",
    )
    parser.add_argument(
        "--rf",
        type=float,
        default=0.0,
        help="Annual risk-free rate for Sharpe (default 0.0; try 0.06)",
    )
    args = parser.parse_args()

    nav, sc, cons, px = _load()
    print("=" * 72)
    print("Smallcase Finance — sample metrics (calc/ pure engine)")
    print(f"rf_rate={args.rf}  periods_per_year=252  as_of from curated NAV")
    print("=" * 72)

    table_rows: list[dict] = []
    for row in sc.sort("smallcase_id").to_dicts():
        sid = row["smallcase_id"]
        name = row["name"]
        sub = nav.filter(pl.col("smallcase_id") == sid).sort("date")
        if sub.height == 0:
            print(f"\n{name} ({sid}): no NAV")
            continue
        m = metrics_for_nav(sub, rf=args.rf)
        print(f"\n## {name}  [{sid}]")
        print(f"  Window ITD: {m['start_date']} → {m['end_date']}  (n_obs={m['n_obs']})")
        print(f"  NAV:        {m['start_nav']:.2f} → {m['end_nav']:.2f}")
        print(
            f"  Total ret:  {_fmt_pct(m['total_return'])}   "
            f"CAGR: {_fmt_pct(m['cagr'])}   "
            f"Vol: {_fmt_pct(m['volatility'])}"
        )
        print(
            f"  Max DD:     {_fmt_pct(m['max_drawdown'])}   "
            f"Sharpe: {_fmt_num(m['sharpe'])}   "
            f"Sortino: {_fmt_num(m['sortino'])}   "
            f"Calmar: {_fmt_num(m['calmar'])}"
        )

        contrib = simple_itd_contribution(
            cons, px, sid, m["start_date"], m["end_date"]
        )
        if contrib:
            print("  Top contributions (weight × symbol ITD return):")
            for c in contrib[:5]:
                print(
                    f"    {c['symbol']:12s}  w={c['weight']:.2f}  "
                    f"r={_fmt_pct(c['symbol_return'])}  "
                    f"contrib={_fmt_pct(c['contribution'])}"
                )
            # sanity: contribution helper
            _ = contribution_by_symbol(
                {c["symbol"]: c["weight"] for c in contrib},
                {c["symbol"]: c["symbol_return"] for c in contrib},
            )

        demo_backtest(px, cons, sid)

        table_rows.append(
            {
                "smallcase_id": sid,
                "name": name,
                "start_date": m["start_date"],
                "end_date": m["end_date"],
                "n_obs": m["n_obs"],
                "total_return": m["total_return"],
                "cagr": m["cagr"],
                "volatility": m["volatility"],
                "max_drawdown": m["max_drawdown"],
                "sharpe": m["sharpe"],
                "sortino": m["sortino"],
                "calmar": m["calmar"],
                "rf_rate": args.rf,
                "computed_at": datetime.now(timezone.utc),
            }
        )

    print("\n" + "=" * 72)
    print("Summary table")
    print("=" * 72)
    if table_rows:
        summary = pl.DataFrame(table_rows)
        # pretty print without huge timestamps
        show = summary.select(
            [
                "smallcase_id",
                "n_obs",
                "total_return",
                "cagr",
                "volatility",
                "max_drawdown",
                "sharpe",
            ]
        )
        print(show)

        if args.write:
            out = _curated() / "metrics" / "calc_metrics_sample.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            summary.write_parquet(out)
            print(f"\nWrote {out}")

    print("\nDone. Definitions: docs/analytics/metrics-definitions.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
