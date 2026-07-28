"""Pipeline orchestration: sample generate → ingest → quality → curated Parquet.

Entrypoint::

    python -m smallcase_finance.pipeline
    make data
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from smallcase_finance.data_access.paths import CURATED_FILES, parquet, raw_root
from smallcase_finance.pipeline.derived import (
    build_contribution,
    build_metrics_snapshot,
    build_nav_series,
)
from smallcase_finance.pipeline.generate_sample import (
    generate_sample_raw,
    sample_drop_exists,
)
from smallcase_finance.pipeline.ingest_instruments import (
    instruments_from_prices_and_defs,
    load_raw_instruments,
)
from smallcase_finance.pipeline.ingest_prices import load_raw_prices
from smallcase_finance.pipeline.ingest_smallcases import (
    constituent_symbols,
    load_raw_smallcases,
)
from smallcase_finance.pipeline.io import atomic_write_parquet
from smallcase_finance.pipeline.quality import run_source_quality

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def run_pipeline(
    *,
    force_sample: bool = False,
    skip_sample: bool = False,
    skip_derived: bool = False,
    verbose: bool = False,
) -> dict[str, Path]:
    """Run full raw → curated pipeline. Returns map of logical table → path written."""
    _configure_logging(verbose)
    written: dict[str, Path] = {}

    # --- 1. Ensure sample raw exists if prices missing ---
    if not skip_sample:
        price_files = list((raw_root() / "prices").rglob("*.parquet")) if (
            raw_root() / "prices"
        ).is_dir() else []
        price_files += list((raw_root() / "prices").rglob("*.csv")) if (
            raw_root() / "prices"
        ).is_dir() else []
        if force_sample or not price_files or not sample_drop_exists():
            if not price_files or force_sample:
                logger.info("generating sample raw prices/instruments…")
                generate_sample_raw(force=force_sample)
            elif not sample_drop_exists():
                # other price drops may exist; only generate if truly empty
                logger.info("price drops present; skipping sample generator")
        else:
            logger.info("sample raw drop present; skipping generator")

    # --- 2. Ingest raw ---
    prices = load_raw_prices()
    smallcases, constituents, rebalances = load_raw_smallcases()
    instruments = load_raw_instruments()
    c_syms = constituent_symbols(constituents)

    if instruments.height == 0:
        logger.warning("inferring instruments from prices + constituents")
        instruments = instruments_from_prices_and_defs(prices, c_syms)
    else:
        # ensure all price/constituent symbols are present
        extra = instruments_from_prices_and_defs(prices, c_syms)
        if extra.height:
            instruments = (
                instruments.vstack(extra)
                .unique(subset=["symbol"], keep="first")
                .sort("symbol")
            )

    # --- 3. Quality checks (source tables) ---
    report = run_source_quality(
        instruments=instruments,
        prices=prices,
        smallcases=smallcases,
        constituents=constituents,
        rebalances=rebalances,
    )
    report.raise_if_errors()

    # --- 4. Write source curated tables ---
    written["instruments"] = atomic_write_parquet(
        instruments, parquet("instruments"), sort_by=["symbol"]
    )
    written["prices"] = atomic_write_parquet(
        prices, parquet("prices"), sort_by=["symbol", "date"]
    )
    written["smallcases"] = atomic_write_parquet(
        smallcases, parquet("smallcases"), sort_by=["smallcase_id"]
    )
    written["smallcase_constituents"] = atomic_write_parquet(
        constituents,
        parquet("smallcase_constituents"),
        sort_by=["smallcase_id", "effective_from", "symbol"],
    )
    written["rebalance_events"] = atomic_write_parquet(
        rebalances,
        parquet("rebalance_events"),
        sort_by=["smallcase_id", "rebalance_date"],
    )

    # --- 5. Derived tables (lightweight; optional skip) ---
    if not skip_derived:
        logger.info("building derived NAV / metrics / contribution…")
        nav = build_nav_series(
            smallcases=smallcases, constituents=constituents, prices=prices
        )
        metrics = build_metrics_snapshot(nav)
        contrib = build_contribution(
            smallcases=smallcases,
            constituents=constituents,
            prices=prices,
            nav=nav,
        )
        written["nav_series"] = atomic_write_parquet(
            nav, parquet("nav_series"), sort_by=["smallcase_id", "date"]
        )
        written["metrics_snapshot"] = atomic_write_parquet(
            metrics,
            parquet("metrics_snapshot"),
            sort_by=["smallcase_id", "as_of", "window"],
        )
        written["contribution"] = atomic_write_parquet(
            contrib,
            parquet("contribution"),
            sort_by=["smallcase_id", "period_start", "period_end", "symbol"],
        )
    else:
        logger.info("skip_derived=True — not writing nav/metrics/contribution")

    logger.info("pipeline complete: %d tables written", len(written))
    for name, path in written.items():
        logger.info("  %s → %s", name, path)
    # sanity: all CURATED_FILES keys we care about
    missing_expected = [
        k
        for k in (
            "instruments",
            "prices",
            "smallcases",
            "smallcase_constituents",
            "rebalance_events",
        )
        if k not in written
    ]
    if missing_expected:
        raise RuntimeError(f"missing expected writes: {missing_expected}")
    # ensure path constants stay in sync
    for k in written:
        if k not in CURATED_FILES:
            logger.warning("wrote table %r not in CURATED_FILES", k)

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="smallcase_finance.pipeline",
        description="Rebuild curated Parquet from data/raw (sample-aware).",
    )
    parser.add_argument(
        "--force-sample",
        action="store_true",
        help="Regenerate sample raw prices/instruments even if present",
    )
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="Never run the sample generator",
    )
    parser.add_argument(
        "--skip-derived",
        action="store_true",
        help="Only write source tables (skip NAV/metrics/contribution)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        run_pipeline(
            force_sample=args.force_sample,
            skip_sample=args.skip_sample,
            skip_derived=args.skip_derived,
            verbose=args.verbose,
        )
    except Exception as e:
        logger.error("pipeline failed: %s", e)
        if args.verbose:
            raise
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
