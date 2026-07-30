# ADR 007 — Portfolio Decision v1

**Status:** Accepted  
**Date:** 2026-07-30  
**Related:** [PRD](../product/prd-portfolio-decision-v1.md), [ADR 005](./005-upstox-sole-market-data.md)

## Context

SIP Lab answers “how would a monthly SIP into this basket have performed?” The founder also needs “what do I hold on Kite?” and “should I fund this basket vs a benchmark?”

## Decision

1. **Portfolio of record** = read-only **Kite equity** holdings snapshots under `data/curated/portfolio/` (raw under `data/raw/holdings/kite/`).
2. **Historical OHLCV** remains **Upstox-only** (ADR 005). Kite is never a candle source.
3. **Decision Lab** orchestrates existing **SIP engine** (`SipService`) for the candidate basket + optional single-name **benchmark SIP**, plus **weight gap** vs the latest portfolio snapshot and **data-quality** warnings.
4. Coin / MF, live trading, and multi-vendor prices stay out of scope.

## Consequences

- New APIs: `/portfolio/*`, `/decisions/*`.
- UI primary nav: Portfolio, Decision Lab; theme dashboard demoted.
- Personal holdings paths gitignored.
