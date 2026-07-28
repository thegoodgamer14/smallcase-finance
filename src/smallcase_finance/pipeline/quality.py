"""Explicit data quality checks for curated tables."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import polars as pl

from smallcase_finance.schemas.models import WEIGHT_SUM_TOL

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def raise_if_errors(self) -> None:
        if self.errors:
            msg = "; ".join(self.errors)
            raise ValueError(f"data quality failed: {msg}")

    def log_all(self) -> None:
        for m in self.info:
            logger.info("[dq] %s", m)
        for m in self.warnings:
            logger.warning("[dq] %s", m)
        for m in self.errors:
            logger.error("[dq] %s", m)


def check_instruments(df: pl.DataFrame) -> QualityReport:
    r = QualityReport()
    r.info.append(f"instruments rows={df.height}")
    if df.height == 0:
        r.errors.append("instruments is empty")
        return r
    null_sym = df.filter(pl.col("symbol").is_null() | (pl.col("symbol") == "")).height
    if null_sym:
        r.errors.append(f"instruments: {null_sym} empty symbols")
    dups = df.height - df["symbol"].n_unique()
    if dups:
        r.errors.append(f"instruments: {dups} duplicate symbols")
    null_name = df.filter(pl.col("name").is_null() | (pl.col("name") == "")).height
    if null_name:
        r.errors.append(f"instruments: {null_name} rows missing name")
    return r


def check_prices(df: pl.DataFrame) -> QualityReport:
    r = QualityReport()
    r.info.append(f"prices rows={df.height}")
    if df.height == 0:
        r.errors.append("prices is empty")
        return r
    null_rate_close = df["close"].null_count() / df.height
    r.info.append(f"prices close null_rate={null_rate_close:.4f}")
    if null_rate_close > 0:
        r.errors.append("prices: close has nulls")
    bad = df.filter(pl.col("close") <= 0).height
    if bad:
        r.errors.append(f"prices: {bad} rows with close <= 0")
    dups = df.height - df.unique(subset=["symbol", "date"]).height
    if dups:
        r.errors.append(f"prices: {dups} duplicate (symbol, date)")
    # date continuity per symbol (business-day gaps are OK if holiday-like;
    # flag multi-week holes as warnings)
    for sym in df["symbol"].unique().to_list():
        sub = df.filter(pl.col("symbol") == sym).sort("date")
        dates = sub["date"].to_list()
        if len(dates) < 2:
            continue
        gaps = []
        for a, b in zip(dates, dates[1:]):
            delta = (b - a).days
            if delta > 10:
                gaps.append((a, b, delta))
        if gaps:
            r.warnings.append(
                f"prices[{sym}]: {len(gaps)} large date gaps (>10d), e.g. {gaps[0]}"
            )
    r.info.append(
        f"prices symbols={df['symbol'].n_unique()} "
        f"range={df['date'].min()}→{df['date'].max()}"
    )
    return r


def check_weight_sums(constituents: pl.DataFrame) -> QualityReport:
    r = QualityReport()
    if constituents.height == 0:
        r.errors.append("smallcase_constituents is empty")
        return r
    grouped = (
        constituents.group_by(["smallcase_id", "effective_from"])
        .agg(pl.col("target_weight").sum().alias("wsum"))
        .sort(["smallcase_id", "effective_from"])
    )
    for row in grouped.to_dicts():
        w = row["wsum"]
        if abs(w - 1.0) > WEIGHT_SUM_TOL:
            r.errors.append(
                f"weights {row['smallcase_id']}@{row['effective_from']} sum={w}"
            )
        else:
            r.info.append(
                f"weights ok {row['smallcase_id']}@{row['effective_from']} sum={w:.8f}"
            )
    return r


def check_symbol_fk(
    instruments: pl.DataFrame,
    *tables: tuple[str, pl.DataFrame],
) -> QualityReport:
    r = QualityReport()
    if instruments.height == 0:
        r.errors.append("cannot check symbol FK: instruments empty")
        return r
    universe = set(instruments["symbol"].to_list())
    for name, df in tables:
        if df.height == 0 or "symbol" not in df.columns:
            continue
        missing = sorted(set(df["symbol"].to_list()) - universe)
        if missing:
            r.errors.append(f"{name}: symbols missing from instruments: {missing}")
        else:
            r.info.append(f"{name}: all symbols present in instruments")
    return r


def check_smallcase_fk(
    smallcases: pl.DataFrame,
    *tables: tuple[str, pl.DataFrame],
) -> QualityReport:
    r = QualityReport()
    if smallcases.height == 0:
        r.errors.append("smallcases is empty")
        return r
    ids = set(smallcases["smallcase_id"].to_list())
    for name, df in tables:
        if df.height == 0 or "smallcase_id" not in df.columns:
            continue
        missing = sorted(set(df["smallcase_id"].to_list()) - ids)
        if missing:
            r.errors.append(f"{name}: unknown smallcase_id: {missing}")
    return r


def merge_reports(*reports: QualityReport) -> QualityReport:
    out = QualityReport()
    for r in reports:
        out.errors.extend(r.errors)
        out.warnings.extend(r.warnings)
        out.info.extend(r.info)
    return out


def run_source_quality(
    *,
    instruments: pl.DataFrame,
    prices: pl.DataFrame,
    smallcases: pl.DataFrame,
    constituents: pl.DataFrame,
    rebalances: pl.DataFrame,
) -> QualityReport:
    report = merge_reports(
        check_instruments(instruments),
        check_prices(prices),
        check_weight_sums(constituents),
        check_symbol_fk(
            instruments,
            ("prices", prices),
            ("smallcase_constituents", constituents),
        ),
        check_smallcase_fk(
            smallcases,
            ("smallcase_constituents", constituents),
            ("rebalance_events", rebalances),
        ),
    )
    # coverage: active constituents should have some prices
    if constituents.height and prices.height:
        price_syms = set(prices["symbol"].to_list())
        c_syms = set(constituents["symbol"].to_list())
        missing_px = sorted(c_syms - price_syms)
        if missing_px:
            report.warnings.append(
                f"constituents without any prices: {missing_px}"
            )
        else:
            report.info.append("all constituent symbols have price history")
    report.log_all()
    return report
