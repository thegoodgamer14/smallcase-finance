# ADR 003 — Upstox as optional live price source

**Status:** Accepted (v0.1)  
**Date:** 2026-07-28

## Context

Users want real multi-year equity history for local smallcase backtests. Smallcase.com does not expose user-created baskets via a public personal API. Upstox provides historical candle APIs suitable for daily OHLCV.

## Decision

1. **Optional integration** behind env credentials (`UPSTOX_ACCESS_TOKEN` primary Bearer; `UPSTOX_API_KEY` / `UPSTOX_API_SECRET` for OAuth).
2. Sync writes **raw drops** under `data/raw/prices/{yyyy-mm-dd}_upstox/`; the existing pipeline remains the path to curated Parquet.
3. **Custom lookback** is first-class: `--years N` or `--from` / `--to` (inclusive).
4. **Sample synthetic data stays** the default when credentials are missing (clear warnings; no hard failure for demos).
5. **No secrets in git**; HTTP sync endpoint disabled unless `UPSTOX_SYNC_ENABLED=1`.
6. Smallcase definitions remain **local JSON**; Upstox supplies prices only.

## Consequences

- Live runs require a valid Upstox access token and instrument_key map coverage.
- Missing symbols are skipped with warnings (weights renormalize in NAV construction).
- Future one-click OAuth is out of scope for this slice; CLI/Make is the supported path.
