# Build Report — Smallcase Finance v0

**Date:** 2026-07-28  
**Status:** v0 Definition of Done **met** — local demo is shippable  
**Audience:** Human owner / next session  
**Sources of truth:** [README.md](../README.md), [PRODUCT.md](../PRODUCT.md), [docs/architecture/v0-plan.md](architecture/v0-plan.md)

This report only claims what exists in the repo and what verification confirmed.

---

## 1) What shipped

End-to-end **local-first** slice: sample/personal raw data → pipeline → Parquet under `data/curated/` → pure calc + FastAPI → Next.js dashboard.

### Data & pipeline

| Artifact | Location |
|----------|----------|
| Raw smallcase definitions | `data/raw/smallcases/digital-india.json`, `momentum-quality.json` |
| Sample / droppable prices | `data/raw/prices/{yyyy-mm-dd}_{source}/` (sample folder present) |
| Optional instruments | `data/raw/instruments/` |
| Curated Parquet SoT | `data/curated/{prices,instruments,smallcases,nav,metrics,rebalances}/` |
| Pipeline entrypoint | `python3 -m smallcase_finance.pipeline` (`make pipeline`) |

Pipeline stages: ingest instruments/prices/smallcases → quality checks → write curated → build derived **NAV**, **metrics snapshot**, and **contribution**. If raw prices are empty, a **synthetic OHLCV generator** (GBM-style, labeled `source=sample`) fills the gap so demos still work.

**Sample smallcases (2):**

| id | Theme | Methodology | Notes |
|----|--------|-------------|--------|
| `digital-india` | IT & digital services | `custom_weights` | v1 (2023) → v2 weights from 2024-01-02; quarterly rebalance rule |
| `momentum-quality` | Quality compounders | equal-weight style (5 names) | Second demo basket |

Sample price universe: **synthetic** multi-year daily series (≈2023-01-02 → 2025-12-31, ~14 symbols). Not real market data.

### Calc engine

Pure functions (no I/O) under `src/smallcase_finance/calc/`:

- `nav.py` — weighted daily returns → NAV series (`base_nav` default 100)
- `returns.py` — simple returns, portfolio return, per-symbol contribution
- `risk.py` — total return, CAGR, volatility, max drawdown, Sharpe, summary
- `weights.py` — normalize, drift
- `rebalance.py` — rebalance simulation + buy-and-hold comparison

### API (FastAPI)

Entrypoint: `smallcase_finance.main:app` (also re-exported via `smallcase_finance.api.main`).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Status, version, curated reachability |
| GET | `/smallcases` | List (+ optional `q` / `tag`) |
| GET | `/smallcases/{id}` | Detail |
| GET | `/smallcases/{id}/holdings` | Target composition as-of |
| GET | `/smallcases/{id}/nav` | NAV series or latest |
| GET | `/smallcases/{id}/performance` | NAV + daily returns |
| GET | `/smallcases/{id}/metrics` | Windowed metrics (`1M` … `ITD`) |
| GET | `/smallcases/{id}/attribution` | Basic contribution |
| POST | `/backtest` | Periodic rebalance vs buy-and-hold (no Parquet write) |

OpenAPI: `http://127.0.0.1:8000/docs`. Full cookbook: [docs/api.md](api.md).

### Web UI (Next.js App Router)

App: `apps/web/` — TypeScript, Tailwind, **Recharts**, dark-mode friendly shell.

| Route | Content |
|-------|---------|
| `/` | Dashboard: KPI cards, equity curve, period returns, contributors, sector breakdown |
| `/holdings` | Holdings table + weight bars |
| `/performance` | Performance / risk view |

Shared **smallcase switcher**, date-range chips, empty/error states. Client talks to API via `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`).

### Tests & docs

- **Tests:** `tests/test_metrics.py` (core calc), `tests/test_api_smoke.py` (health, list, metrics, etc.)
- **Docs:** README install+run; [data-dictionary](data-dictionary.md); [pipeline](data/pipeline.md); [how-to-add-data](data/how-to-add-data.md); [metrics definitions](analytics/metrics-definitions.md); ADRs under `docs/decisions/`
- **Make / demo:** `Makefile` + `scripts/run_demo.sh`

### Verification (this build)

| Check | Result |
|-------|--------|
| Pipeline | Passed |
| Metrics tests | Passed |
| API import | Passed |
| UI build | Passed |
| DoD items 1–7 (see §5) | All passed |

---

## 2) Exact commands — install, pipeline, API, UI

**Requirements:** Python ≥ 3.11, Node.js 18+, Make optional.

### One-shot demo

```bash
# from repo root: /Users/HP/Desktop/Projects/backtest-hero/smallcase-finance
make demo          # install Python + web deps → pipeline → tests → next steps
```

Then **two terminals**:

```bash
make api           # FastAPI  → http://127.0.0.1:8000  (OpenAPI: /docs)
make web           # Next.js  → http://localhost:3000
```

### Step by step (without Make)

```bash
# 1. Install
python3 -m pip install -e ".[dev]"
cd apps/web && npm install && cd ../..

# 2. Build curated data (auto-generates sample prices if raw prices missing)
python3 -m smallcase_finance.pipeline
# or: make pipeline

# 3. Tests
python3 -m pytest -q
# or: make test

# 4. API
python3 -m uvicorn smallcase_finance.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
# or: make api

# 5. UI (separate terminal)
cd apps/web && npm run dev
# or: make web
```

### Smoke the API

```bash
curl -s http://127.0.0.1:8000/health | jq
curl -s http://127.0.0.1:8000/smallcases | jq '.items[].id'
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?window=ITD' | jq '.metrics'
```

### Make targets

| Target | What it does |
|--------|----------------|
| `make install` | `pip install -e ".[dev]"` + `npm install` in `apps/web` |
| `make data` / `make pipeline` | raw → `data/curated/*.parquet` |
| `make test` | pytest |
| `make api` | FastAPI on `127.0.0.1:8000` |
| `make web` | Next.js on `localhost:3000` |
| `make demo` | install → pipeline → test → print run instructions |
| `make clean-curated` | delete curated Parquet only (raw kept) |

### Env overrides

| Variable | Default | Used by |
|----------|---------|---------|
| `DATA_CURATED_ROOT` | `<repo>/data/curated` | API / data access |
| `DEFAULT_RF` | `0.0` | Annual risk-free rate for Sharpe |
| `PERIODS_PER_YEAR` | `252` | Annualization |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Next.js client |

CORS allows `http://localhost:3000` and `http://127.0.0.1:3000`.

---

## 3) How to add personal data

**Short path**

1. Drop price files under `data/raw/prices/{yyyy-mm-dd}_{source}/` (CSV or Parquet).  
   Required columns: `symbol`, `date`, `close`. Optional: OHLC, `volume`, `adj_close`.
2. Optionally drop instruments under `data/raw/instruments/{yyyy-mm-dd}_{source}/`.
3. Author or edit `data/raw/smallcases/{smallcase_id}.json` (weights must sum to **1.0** per version).
4. Run `make pipeline` (or `python3 -m smallcase_finance.pipeline`).
5. Restart the API if it was already running; the UI reloads smallcases via `GET /smallcases`.

**Do not edit** files under `data/curated/` by hand — they are rebuilt by the pipeline.

**Full guide (examples, aliases, troubleshooting):**  
→ [docs/data/how-to-add-data.md](data/how-to-add-data.md)

| Doc | Contents |
|-----|----------|
| [docs/data/pipeline.md](data/pipeline.md) | Stages, flags, quality checks |
| [docs/data/file-layout.md](data/file-layout.md) | Exact raw/curated paths |
| [docs/data-dictionary.md](data-dictionary.md) | Column names, types, PK/grain |
| [data/README.md](../data/README.md) | Quick data tree |

**Minimal smallcase JSON** lives under `data/raw/smallcases/{id}.json` (schema: `SmallcaseDefinitionFile` in `src/smallcase_finance/schemas/models.py`). See README “How smallcases are defined” and the two sample files.

---

## 4) Known limitations / next backlog

### Out of scope (v0 — intentionally not built)

- Production auth, multi-user, multi-tenancy  
- Live trading, order placement, broker order routing  
- Continuous broker portfolio sync  
- Multi-currency FX conversion  
- Full corporate-actions engine (optional `adj_close` only)  
- Full Brinson / multi-level performance attribution  
- Postgres or cloud warehouse as source of truth  
- Mobile-first UI; deep compare / settings pages  

### Known limitations (current behavior)

- Sample OHLCV is **synthetic** — demos only  
- Missing prices: symbol dropped that day; remaining weights **renormalized**  
- No transaction costs, taxes, or cash drag in backtest  
- Default Sharpe risk-free rate is **0.0** (set `DEFAULT_RF=0.06` for a rough India-like cash yield)  
- Holdings UI uses **target** constituent weights (`data/curated/holdings/` is empty; broker `holdings_snapshots` unused by default)  
- Contribution is simple `avg_weight × symbol_return`, not full attribution  
- Notebooks directory exists but has no polished analysis entrypoints yet  

### Suggested post-v0 backlog (from PRODUCT open questions + non-goals)

1. **Real personal price drop** — replace synthetic series; validate pipeline on real NSE-like exports  
2. **Optional broker holdings snapshots** — actual vs target weight views  
3. **Default benchmark series** — relative performance / excess return  
4. **Notebook entrypoints** — ad-hoc analysis beyond the UI  
5. **Transaction costs / cash drag** in backtest  
6. **Compare smallcases** UI (side-by-side metrics/curves)  
7. **Richer attribution** if needed later (still not full Brinson unless explicitly scoped)

---

## 5) Honest Definition of Done status

Tracked against [docs/architecture/v0-plan.md](architecture/v0-plan.md) §5 and verification notes for this build.

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Drop data into `data/raw/` (or sample generator) → documented pipeline → curated outputs | **Met** |
| 2 | ≥1 sample smallcase (constituents + target weights + methodology) — actually **2** | **Met** |
| 3 | Core metrics: NAV, returns, CAGR, volatility, max drawdown, Sharpe, basic attribution | **Met** |
| 4 | Simple rebalancing / backtest (`POST /backtest`, `calc/rebalance.py`) | **Met** |
| 5 | Local web UI: dashboard, holdings, performance/risk, smallcase switcher | **Met** |
| 6 | Documented install+run; README; data dictionary; how to add personal data | **Met** |
| 7 | Lightweight tests for core calculation functions (+ API smoke) | **Met** |

**Verdict:** v0 is **shippable as a personal local demo**. All verification checks passed; no failed items reported for this build.

What “shippable” means here: clone/open repo → `make demo` → `make api` + `make web` → explore sample smallcases with correct metrics and UI. It does **not** mean production readiness, live market data, or broker integration.

---

## Quick links

| Doc | Purpose |
|-----|---------|
| [README.md](../README.md) | Install, structure, metrics overview |
| [PRODUCT.md](../PRODUCT.md) | Vision, stack, checklist, open questions |
| [docs/architecture/v0-plan.md](architecture/v0-plan.md) | Plan & DoD |
| [docs/api.md](api.md) | HTTP endpoints |
| [docs/data/how-to-add-data.md](data/how-to-add-data.md) | Personal data onboarding |
| [docs/analytics/metrics-definitions.md](analytics/metrics-definitions.md) | Metric formulas |
