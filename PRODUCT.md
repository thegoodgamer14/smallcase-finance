# PRODUCT.md — Current Vision & Status

## Vision
Personal tool to define, test, and analyze Smallcase-style thematic portfolios using real or sample data. Focus on composition logic, performance measurement, risk, and simple rebalancing rules.

## Current Goal — v0 **shipped** (local demo)

Local-first end-to-end slice: sample/curated data → calc engine → FastAPI → Next.js dashboard.

**Status:** Definition of Done met (2026-07-28). Full writeup: [docs/build-report.md](docs/build-report.md).  
Track checklist against [docs/architecture/v0-plan.md](docs/architecture/v0-plan.md).

### Definition of Done (status)

- [x] **Data model** locked (ADRs + [data dictionary](docs/data-dictionary.md))
- [x] **Sample data + pipeline** — empty raw OK: generate sample OHLCV + 2 smallcases → `data/curated/`; entrypoint `python -m smallcase_finance.pipeline` / `make pipeline`
- [x] **Calc engine + tests** — NAV, returns, CAGR, vol, max DD, Sharpe, attribution, rebalance in `src/smallcase_finance/calc/`; pytest in `tests/`
- [x] **API** — FastAPI read path over curated (+ on-the-fly metrics/backtest): health, smallcases, holdings, NAV, performance, metrics, attribution, `POST /backtest`
- [x] **UI** — Dashboard, holdings, performance/risk, smallcase switcher (`apps/web`, routes `/`, `/holdings`, `/performance`)
- [x] **Docs** — install+run README; data dictionary; pipeline; [how to add personal data](docs/data/how-to-add-data.md); metrics definitions; [build report](docs/build-report.md)
- [x] **Tests** — lightweight unit tests for core calc + API smoke

### Sample smallcases
| id | Notes |
|----|--------|
| `digital-india` | IT/digital basket; custom weights; v1→v2 on 2024-01-02 |
| `momentum-quality` | Equal-weight quality names |

## Stack (binding for v0)
- Frontend: Next.js (App Router) + TypeScript + Tailwind + **Recharts**
- Backend: Python + FastAPI
- Data: Polars/Pandas + DuckDB + Parquet under `data/curated/`
- Layout: `data/raw`, `data/curated`, `src/`, `notebooks/`, `docs/`

## Data Notes
Place raw files in `data/raw/`.  
Curated outputs go in `data/curated/`.  
Schema: [docs/data-dictionary.md](docs/data-dictionary.md).  
Personal onboarding: [docs/data/how-to-add-data.md](docs/data/how-to-add-data.md).  
If raw prices are empty, the sample generator writes synthetic OHLCV (label `source=sample`).

## Decisions (closed for v0)
- Currency / market: **INR / Indian equities friendly**; generic tickers supported
- Target surface: **minimal web UI** (not notebook-only), with notebooks for analysis
- Storage: **Parquet + DuckDB**, not Postgres (ADR 001, 002)
- Chart library: **Recharts** (chosen in `apps/web`)
- Default risk-free rate for Sharpe: **0.0** annual (`DEFAULT_RF` env; set `0.06` for India-like cash yield)

## Out of scope (v0)
Production auth, multi-user, live trading, full broker integration, FX engine, full Brinson attribution, transaction costs.

## Next / in progress
- [x] **Upstox price ingest (v0.1)** — CLI + env token + custom lookback (`--years` / `--from`/`--to`) + sample fallback; UI custom timeline + data-source banner
- [ ] Provide live `UPSTOX_ACCESS_TOKEN` when ready for real bars (optional)
- [ ] Optional broker `holdings_snapshots` path for “actual vs target” views
- [ ] Single default benchmark series for relative performance (post-v0)
- [ ] Notebooks entrypoints for ad-hoc analysis beyond the UI
- [ ] Future one-click Upstox OAuth (not this slice — CLI first)

## Green path (reminder)
```bash
make demo    # install + pipeline + tests
make api     # :8000
make web     # :3000
```

Update this file as goals complete or priorities shift.
