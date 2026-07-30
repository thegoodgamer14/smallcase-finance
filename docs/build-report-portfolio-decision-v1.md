# Build report — Portfolio Decision v1

**Date:** 2026-07-30  
**PRD:** [prd-portfolio-decision-v1.md](./product/prd-portfolio-decision-v1.md)

## Shipped

### Backend

- Portfolio snapshot write/read (`data_access/portfolio.py`)
- `PortfolioService` + routes: `GET /portfolio/status`, `POST /portfolio/refresh`, `GET /portfolio/holdings/latest`, `GET /portfolio/symbols`
- `DecisionService` + routes: `GET /decisions/price-coverage`, `POST /decisions/run`
- Config: `DEFAULT_BENCHMARK_SYMBOL`, `STRICT_MARKET_DATA`, `PORTFOLIO_CURATED_PATH`
- Tests: `test_portfolio.py`, `test_decision.py`, API smoke extensions

### Frontend

- `/portfolio` — Kite connection, refresh, holdings table
- `/decide` — basket builder, SIP params, benchmark, results, weight gap, DQ banners
- AppShell nav: Portfolio / Decision Lab primary; theme pages labeled demo
- Product title: Backtest Hero
- ThemeToggle mount guard (reduces real theme hydration flicker)

### Docs / ops

- ADR 007
- PRD already at `docs/product/prd-portfolio-decision-v1.md`
- Workflow: `.grok/workflows/portfolio-decision-v1.rhai`
- Gitignore personal portfolio curated snapshots

## Hydration note

Console noise showing attributes like `bis_register` / `__processed_*` is almost always a **browser extension** mutating the DOM, not an app SSR bug. App-side theme icon mismatch after `localStorage` load is mitigated in `ThemeToggle`. Next.js “15.1.0 is outdated” is informational only.

## Not shipped (by design)

Coin, order placement, multi-vendor prices, full cost model.
