# v0 Plan — Smallcase Finance

**Status:** v0 DoD met (local demo shippable)  
**Owner:** Product Owner  
**Date:** 2026-07-28  
**Audience:** All agents + human  
**Binding ADRs:** [001 data model](../decisions/001-data-model.md), [002 backend stack](../decisions/002-backend-stack.md)  
**Detail specs:** [data-model](./data-model.md), [backend](./backend.md), [ui](./ui.md), [data-dictionary](../data-dictionary.md)  
**Onboarding:** [README](../../README.md), [how-to-add-data](../data/how-to-add-data.md), [PRODUCT.md](../../PRODUCT.md)

---

## 1. Chosen stack (and why)

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + Recharts** (or Tremor) | Fast local UI; typed contracts; finance-friendly charts without heavy design system |
| Backend | **Python + FastAPI** | Same language as calc/notebooks; thin HTTP over pure `calc/`; Pydantic v2 for API DTOs |
| Data / analytics | **Polars or Pandas + DuckDB + Parquet** under `data/curated/` | Columnar, typed, zero DB ops; DuckDB scans Parquet in-process; pipelines idempotent |
| Layout | `data/raw`, `data/curated`, `src/`, `notebooks/`, `docs/` | Clear raw vs curated; installable package at `src/smallcase_finance/` |
| Market | **INR / Indian equities friendly**; generic tickers as opaque strings | Personal use case; no FX engine in v0 |
| Runtime | **Local-first**, reproducible | Clone → install → drop/generate data → pipeline → API → UI |

**Explicitly not for v0:** Postgres as primary store, Node backend, cloud warehouse, production auth.

---

## 2. Build order

Execute in sequence. Later steps may assume earlier artifacts exist.

| # | Phase | Goal | Primary owner | Exit criteria |
|---|--------|------|---------------|---------------|
| **1** | **Data model** | Lock entities, grains, paths, dictionary | Data Architect *(done in ADRs + dictionary)* | `instruments`, `prices`, versioned `smallcase_constituents`, derived `nav` / `metrics` / `contribution` documented |
| **2** | **Sample data + pipeline** | Fill empty `data/raw/` → curated Parquet | Data Engineer | Documented command: raw drop (or generator) → validate → write `data/curated/**/*.parquet`; rebuild derived tables |
| **3** | **Calc engine + tests** | Pure NAV, returns, risk, rebalance in `calc/` | Backend / Analyst | Unit tests for CAGR, vol, max DD, Sharpe, weight normalize, rebalance simulation; no I/O in `calc/` |
| **4** | **API** | Read-only FastAPI over curated (+ on-the-fly calc) | Backend | Health + list/get smallcases, holdings, NAV series, metrics, basic backtest endpoint |
| **5** | **UI** | Dashboard, holdings, performance, smallcase switcher | Frontend | Routes `/`, `/holdings`, `/performance`; switcher + date range; charts from API |
| **6** | **Docs** | Install, run, personal data, decisions | PO + all | README install+run; dictionary current; how to add personal data; this plan + ADRs linked |

**Parallelism allowed after phase 1:** sample-data generator and `calc/` tests can proceed in parallel; API needs curated schema + calc; UI needs API contracts (mock OK early, real data before DoD).

---

## 3. Out of scope (v0)

- Production auth, sessions, multi-user / multi-tenancy  
- Live trading, order placement, broker order routing  
- Full broker integration / continuous portfolio sync  
- Multi-currency FX tables and conversion engine  
- Full corporate-actions engine (beyond optional `adj_close` in prices)  
- Brinson / multi-level performance attribution  
- Benchmark universe service (optional single benchmark later if easy)  
- Postgres / always-on DB server as analytics SoT  
- Mobile-first design; deep rebalance/compare/settings pages  
- Microservice split, cloud deploy, CI production gates  

---

## 4. Open risks and assumptions

### Assumptions

| # | Assumption |
|---|------------|
| A1 | **`data/raw/` may be empty.** v0 ships a **sample OHLCV generator** (or static sample drop) plus **1–2 defined smallcases** (constituents + target weights + methodology text). |
| A2 | Symbols are uppercase strings (e.g. `RELIANCE`, `TCS`); one primary listing per symbol for prices grain `(symbol, date)`. |
| A3 | Currency default **INR**; stored on smallcase/price rows for future flexibility but no FX math. |
| A4 | NAV uses target weights + daily closes; missing price → exclude symbol that day and **renormalize** remaining weights (log gaps). |
| A5 | Weights are fractions summing to 1.0 ± 1e-6 per constituent version; versioned by `effective_from`. |
| A6 | NAV base = `100.0` unless overridden; risk-free rate for Sharpe is a documented constant (e.g. 0.06 annual). |
| A7 | Curated Parquet is **read-only** for the API; writes only via pipeline. |
| A8 | One-command or clearly documented install+run is sufficient (no installer packaging). |

### Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | No personal market data available | Generate synthetic multi-year OHLCV for a small NSE-like universe; label `source=sample` |
| R2 | Schema drift between pipeline, `calc`, API, UI | Single dictionary + ADR 001; reject invalid Parquet in pipeline |
| R3 | Calc diverges between notebook and API | Shared pure `calc/`; tests as contract |
| R4 | Precomputed NAV missing | Services recompute on the fly from prices + constituents |
| R5 | Scope creep into live data / auth | Non-goals list; PO rejects gold-plating |
| R6 | Sample data unrealistic enough to mislead | Document “sample only”; separate path for personal raw drops |

---

## 5. Definition of Done (v0 checklist)

- [x] **Pipeline:** Drop data into `data/raw/` (or run sample generator) → documented pipeline produces curated outputs under `data/curated/`
- [x] **Smallcase:** ≥1 sample smallcase with constituents, target weights, methodology, rebalance rule (`digital-india`, `momentum-quality`)
- [x] **Metrics:** NAV series, returns, CAGR, volatility, max drawdown, Sharpe, basic per-symbol attribution
- [x] **Backtest:** Simple rebalancing / backtest capability (`POST /backtest`, `calc/rebalance.py`)
- [x] **UI:** Local web app — dashboard (metrics + chart), holdings, performance/risk, **smallcase switcher**
- [x] **Docs:** Install+run documented; README current; data dictionary; how to add personal data
- [x] **Tests:** Lightweight unit tests for core calculation functions in `calc/` (+ API smoke)

v0 is shippable as a personal demo. Next increments (compare, real broker holdings, live prices) are **post-v0**.

---

## 6. Quick reference paths

```
data/raw/                         # immutable drops / sample seed
data/curated/                     # Parquet SoT (see data-dictionary)
src/smallcase_finance/
  calc/                           # pure math
  data_access/                    # DuckDB + paths
  services/  api/  schemas/       # FastAPI stack
notebooks/                        # ad-hoc analysis
docs/architecture/                # this plan + layer specs
docs/decisions/                   # ADRs
```

**Agent handoff after this plan:** Data Engineer (sample data + pipeline) ∥ Backend (`calc` + tests + API) → Frontend (UI against API) → docs polish.
