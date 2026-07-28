"""CLI: python -m smallcase_finance.integrations.upstox

Examples::

    # Default lookback (UPSTOX_DEFAULT_YEARS, usually 3)
    python -m smallcase_finance.integrations.upstox

    # Custom years
    python -m smallcase_finance.integrations.upstox --years 5

    # Custom inclusive date range
    python -m smallcase_finance.integrations.upstox --from 2020-01-01 --to 2025-12-31

    # Specific symbols + rebuild curated
    python -m smallcase_finance.integrations.upstox --symbols TCS,INFY --years 2 --pipeline
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m smallcase_finance.integrations.upstox",
        description=(
            "Fetch daily OHLCV from Upstox into data/raw/prices/{date}_upstox/. "
            "Without credentials, falls back to sample data."
        ),
    )
    p.add_argument(
        "--years",
        type=int,
        default=None,
        help="Lookback years ending at --to (or today). Ignored if --from is set alone with --to.",
    )
    p.add_argument(
        "--from",
        dest="from_date",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="Custom range start (inclusive)",
    )
    p.add_argument(
        "--to",
        dest="to_date",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="Custom range end (inclusive); default today",
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: union of raw smallcase constituents)",
    )
    p.add_argument(
        "--pipeline",
        action="store_true",
        help="Run raw→curated pipeline after a successful write",
    )
    p.add_argument(
        "--no-sample-fallback",
        action="store_true",
        help="Exit with error if credentials missing (do not use sample data)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print SyncResult as JSON",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    from smallcase_finance.integrations.upstox.sync import sync_prices

    try:
        result = sync_prices(
            symbols=symbols,
            years=args.years,
            from_date=args.from_date,
            to_date=args.to_date,
            run_pipeline_after=args.pipeline,
            allow_sample_fallback=not args.no_sample_fallback,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.message)
        if result.warnings:
            print("warnings:", file=sys.stderr)
            for w in result.warnings:
                print(f"  - {w}", file=sys.stderr)
        print(
            f"range: {result.from_date} → {result.to_date} | "
            f"fetched={len(result.fetched_symbols)} skipped={len(result.skipped_symbols)} "
            f"rows={result.row_count}"
        )

    if result.used_sample_fallback and args.no_sample_fallback:
        return 1
    if not result.used_sample_fallback and result.row_count == 0 and result.requested_symbols:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
