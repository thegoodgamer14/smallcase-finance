# Smallcase Finance

Local-first toolkit for **Smallcase-style thematic portfolios** and the emerging **SIP Lab** engine: define a basket of stocks and target weights, rebuild NAV and risk metrics from daily prices, and explore results in a simple web dashboard.

Designed for personal use with **sample data out of the box** or **real multi-year history from Upstox**. No cloud multi-tenant auth, no live trading.

**Roadmap (SIP Lab phases & exit gates):** [docs/ROADMAP.md](docs/ROADMAP.md)

| Layer | Choice |
|-------|--------|
| Pipeline + calc + API | Python 3.11+ · Polars · DuckDB · FastAPI |
| UI | Next.js (App Router) · TypeScript · Tailwind · Recharts |
| Storage | Parquet under `data/curated/` (raw drops in `data/raw/`) |

---

## What this is

1. **Author** smallcase definitions (JSON): constituents, target weights, methodology, rebalance notes.
2. **Ingest** daily prices (and optional instrument master) from dated folders under `data/raw/`.
3. **Pipeline** validates, writes curated Parquet, and builds derived **NAV**, **metrics**, and **contribution**.
4. **API** serves smallcases, holdings, NAV/performance series, metrics, attribution, and a simple rebalance backtest.
5. **Web UI** shows dashboard KPIs + equity curve, holdings, performance/risk, with a **smallcase switcher**.

Sample smallcases shipped after the pipeline:

| id | Theme | Methodology |
|----|--------|-------------|
| `digital-india` | IT & digital services | Custom weights, two versions (2023 → 2024 refresh) |
| `momentum-quality` | Quality compounders | Equal weight (5 names) |

Sample prices are **synthetic** (GBM-style, 2023-01-02 → 2025-12-31, 14 symbols). Not real market data.

---

## Quickstart

**Requirements:** Python ≥ 3.11, Node.js 18+ (for the UI), Make optional.

### One-shot demo

```bash
# from repo root
make demo          # install Python + web deps → pipeline → tests → next steps
```

Then in **two terminals**:

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

# 5. UI (separate terminal)
cd apps/web && npm run dev
```

### Smoke the API

```bash
curl -s http://127.0.0.1:8000/health | jq
curl -s http://127.0.0.1:8000/smallcases | jq '.items[].id'
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?window=ITD' | jq '.metrics'
```

- OpenAPI: http://127.0.0.1:8000/docs  
- Curl cookbook: [docs/api.md](docs/api.md)  
- Metrics formulas: [docs/analytics/metrics-definitions.md](docs/analytics/metrics-definitions.md)

### Make targets

| Target | What it does |
|--------|----------------|
| `make install` | `pip install -e ".[dev]"` + `npm install` in `apps/web` |
| `make data` / `make pipeline` | raw → `data/curated/*.parquet` (generates sample if raw prices empty) |
| `make test` | pytest (calc unit tests + API smoke) |
| `make api` | FastAPI on `127.0.0.1:8000` |
| `make web` | Next.js on `localhost:3000` |
| `make demo` | install → pipeline → test → print run instructions |
| `make sync-upstox` | Upstox historical prices → raw drop → pipeline (sample fallback if no token) |
| `make clean-curated` | delete curated Parquet only (raw kept) |

### Env overrides

| Variable | Default | Used by |
|----------|---------|---------|
| `DATA_CURATED_ROOT` | `<repo>/data/curated` | API / data access |
| `DEFAULT_RF` | `0.0` | Annual risk-free rate for Sharpe (e.g. `0.06`) |
| `PERIODS_PER_YEAR` | `252` | Annualization |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Next.js client |
| `UPSTOX_ACCESS_TOKEN` | _(empty)_ | **Bearer** for Upstox historical candles (sole live source) |
| `UPSTOX_API_KEY` | _(empty)_ | Upstox **API Key** / `client_id` (OAuth only) |
| `UPSTOX_API_SECRET` | _(empty)_ | Upstox **API Secret** / `client_secret` (OAuth only) |
| `UPSTOX_DEFAULT_YEARS` | `3` | Default lookback for `make sync-upstox` |

CORS allows the Next.js origin at `http://localhost:3000` and `http://127.0.0.1:3000`.  
Extra origins (e.g. Vercel): set `CORS_ORIGINS=https://your-app.vercel.app`.

### Deploy free on Vercel (HTTPS redirect for Upstox/Kite)

**Free-tier plan:** Next.js UI + OAuth callbacks on **Vercel Hobby**; FastAPI SIP engine stays **local** (Polars/DuckDB is not free-tier-safe as a heavy serverless function).

1. Push repo to GitHub.  
2. Vercel → import project → **Root Directory** `apps/web` → deploy on **Hobby**.  
3. Use production URLs as broker redirects:  
   `https://<project>.vercel.app/callback/upstox`  
   `https://<project>.vercel.app/callback/kite`  
4. Set `UPSTOX_API_KEY` / `UPSTOX_API_SECRET` / `UPSTOX_REDIRECT_URI` in Vercel env (never commit).  
5. Put `UPSTOX_ACCESS_TOKEN` in **local** `.env` and run `make sync-upstox` on your machine.

Full guide + cost rationale: **[docs/deploy/vercel.md](docs/deploy/vercel.md)**  
Optional public FastAPI demo (not required for OAuth): [docs/deploy/render.md](docs/deploy/render.md)

### Historical prices = Upstox only

**Binding policy:** equity/ETF OHLCV for real backtests comes **only** from the **Upstox API**.  
No yfinance, NSE bhavcopy, or Fyers in this product version. Sample/synthetic prices are for **demos without a token** only.

```bash
cp .env.example .env
# Developer Apps → Generate access token → set UPSTOX_ACCESS_TOKEN=... (never commit .env)

make sync-upstox              # default years → raw drop → pipeline
make sync-upstox YEARS=5      # custom lookback years
make sync-upstox FROM=2020-01-01 TO=2025-12-31   # custom timeline
```

| Step | What happens |
|------|----------------|
| 1. Credentials | Set `UPSTOX_ACCESS_TOKEN` (portal Bearer). Optional: `UPSTOX_API_KEY` / `UPSTOX_API_SECRET` for future OAuth. |
| 2. Sync | `make sync-upstox` writes `data/raw/prices/{date}_upstox/` and rebuilds curated Parquet |
| 3. Without token | Falls back to **sample** data and still rebuilds curated — labeled demo, not live market |

Status (boolean only, never the secret): `GET /integrations/upstox/status` → `{ "configured": true|false, … }`.  
Full auth + candle contract: [docs/integrations/upstox.md](docs/integrations/upstox.md).

**Custom evaluation windows in the UI:** use the sidebar **Custom timeline** (from/to dates) or preset chips (1M…SI). The API accepts `?start=&end=` on metrics and performance.

---

## Project structure

```
smallcase-finance/
├── apps/web/                 # Next.js UI (dashboard, holdings, performance)
├── data/
│   ├── raw/                  # Authored + dropped source data (immutable drops)
│   │   ├── smallcases/       # {id}.json definitions
│   │   ├── prices/           # {yyyy-mm-dd}_{source}/*.{csv,parquet}
│   │   └── instruments/      # optional master
│   └── curated/              # Pipeline Parquet (NAV, metrics, …) — app SoT
├── docs/
│   ├── ROADMAP.md            # SIP Lab phased plan (binding)
│   ├── data-dictionary.md    # Field-level schema
│   ├── data/                 # Pipeline, layout, how to add personal data
│   ├── analytics/            # Metric definitions
│   ├── api.md                # HTTP endpoints
│   └── decisions/            # ADRs
├── scripts/
│   ├── run_demo.sh           # Green path used by make demo
│   └── print_sample_metrics.py
├── src/smallcase_finance/    # Installable package
│   ├── calc/                 # Pure NAV / risk / rebalance (no I/O)
│   ├── market_data/          # MarketDataProvider + sole UpstoxProvider
│   ├── integrations/upstox/  # Upstox client + sync CLI
│   ├── pipeline/             # raw → curated
│   ├── api/ + services/      # FastAPI
│   └── data_access/          # Parquet / DuckDB reads
├── tests/                    # pytest
├── Makefile
├── PRODUCT.md                # Vision & status
└── AGENTS.md                 # Multi-agent working agreements
```

---

## How to add your own data

**Short path**

1. Drop price files under `data/raw/prices/{yyyy-mm-dd}_{source}/` (CSV or Parquet).  
   Required columns: `symbol`, `date`, `close`. Optional: OHLC, `volume`, `adj_close`.
2. Optionally drop instruments under `data/raw/instruments/{yyyy-mm-dd}_{source}/`.
3. Author or edit `data/raw/smallcases/{smallcase_id}.json` (weights must sum to **1.0** per version).
4. Run `make pipeline` (or `python3 -m smallcase_finance.pipeline`).
5. Restart the API if it was already running; the UI reloads smallcases via `GET /smallcases`.

**Full step-by-step (examples, aliases, troubleshooting):**  
→ [docs/data/how-to-add-data.md](docs/data/how-to-add-data.md)

**Also useful**

| Doc | Contents |
|-----|----------|
| [docs/data/pipeline.md](docs/data/pipeline.md) | Pipeline stages, flags, quality checks |
| [docs/data/file-layout.md](docs/data/file-layout.md) | Exact raw/curated paths |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Column names, types, PK/grain |
| [data/README.md](data/README.md) | Quick data tree |

Do not edit files under `data/curated/` by hand — they are rebuilt by the pipeline.

---

## How smallcases are defined

Each smallcase is a JSON file:

```
data/raw/smallcases/{smallcase_id}.json
```

Validated by `SmallcaseDefinitionFile` in `src/smallcase_finance/schemas/models.py`.

**Minimal shape**

```json
{
  "smallcase_id": "my-theme",
  "name": "My Theme",
  "theme": "optional label",
  "description": "optional blurb",
  "methodology": "custom_weights",
  "rebalance_rule": "manual",
  "base_nav": 100.0,
  "currency": "INR",
  "inception_date": "2023-01-02",
  "versions": [
    {
      "effective_from": "2023-01-02",
      "effective_to": null,
      "version_label": "v1",
      "constituents": [
        { "symbol": "TCS", "target_weight": 0.5 },
        { "symbol": "INFY", "target_weight": 0.5 }
      ]
    }
  ],
  "rebalance_events": []
}
```

| Field | Notes |
|-------|--------|
| `smallcase_id` | Lowercase slug; must match filename stem |
| `methodology` | Preferred: `equal_weight`, `market_cap_weight`, `custom_weights`, `factor_score` |
| `rebalance_rule` | Preferred: `none`, `monthly`, `quarterly`, `threshold_5pct`, `manual` |
| `versions[]` | Weight history; each version’s `target_weight`s must sum to 1.0 ± 1e-6 |
| `versions[].effective_from` | Inclusive start; lookup = latest version with `effective_from ≤ date` |
| `rebalance_events` | Optional audit trail of weight changes |

**Examples in repo:**  
[`data/raw/smallcases/digital-india.json`](data/raw/smallcases/digital-india.json),  
[`data/raw/smallcases/momentum-quality.json`](data/raw/smallcases/momentum-quality.json)

After editing JSON, re-run the pipeline so curated tables and NAV refresh.

**Backtest (API):** `POST /backtest` simulates periodic rebalance vs buy-and-hold over curated prices without writing Parquet. See [docs/api.md](docs/api.md).

---

## Metrics

Core metrics computed from the NAV series (also available via the API and UI):

| Metric | Meaning (v0) |
|--------|----------------|
| NAV | Index level from weighted daily returns (`base_nav` default 100) |
| Total return | `NAV_end / NAV_start − 1` |
| CAGR | Annualized return (252 trading-day year) |
| Volatility | Annualized stdev of daily returns × √252 |
| Max drawdown | Worst peak-to-trough (**negative** fraction) |
| Sharpe | `(CAGR − rf) / volatility` (default `rf = 0.0`) |
| Contribution | Simple `avg_weight × symbol_return` (not full Brinson) |

Full formulas, gap policy, and windows (`1M` … `ITD`):  
→ **[docs/analytics/metrics-definitions.md](docs/analytics/metrics-definitions.md)**

Schema for curated metric tables: [docs/data-dictionary.md](docs/data-dictionary.md).

---

## Non-goals / limitations (v0)

**Out of scope**

- Production auth, multi-user, multi-tenancy  
- Live trading, order placement, broker order routing  
- Continuous broker portfolio sync  
- Multi-currency FX conversion  
- Full corporate-actions engine (optional `adj_close` only)  
- Full Brinson / multi-level performance attribution  
- Postgres or cloud warehouse as source of truth  
- Mobile-first UI; deep compare/settings pages  

**Known limitations**

- Sample OHLCV is synthetic — for demos only  
- Missing prices: symbol dropped that day, remaining weights **renormalized**  
- No transaction costs, taxes, or cash drag in backtest  
- Default Sharpe risk-free rate is **0.0** (set `DEFAULT_RF=0.06` for a rough India-like cash yield)  
- Holdings UI uses **target** constituent weights (broker `holdings_snapshots` optional / unused by default)

Product status and open questions: [PRODUCT.md](PRODUCT.md).

---

## Docs map

| Doc | Purpose |
|-----|---------|
| [PRODUCT.md](PRODUCT.md) | Vision, stack, checklist, open questions |
| **[docs/ROADMAP.md](docs/ROADMAP.md)** | **SIP Lab phased plan (Phase 0–5), exit gates, ordering** |
| [docs/data/how-to-add-data.md](docs/data/how-to-add-data.md) | Personal data onboarding |
| [docs/data/pipeline.md](docs/data/pipeline.md) | Pipeline runbook |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Field dictionary |
| [docs/analytics/metrics-definitions.md](docs/analytics/metrics-definitions.md) | Metric math |
| [docs/api.md](docs/api.md) | HTTP API |
| [docs/architecture/v0-plan.md](docs/architecture/v0-plan.md) | v0 plan & DoD |
| [docs/decisions/](docs/decisions/) | ADRs |

---

## Grok Build / multi-agent

1. `cd` into this directory and run `grok` (or `grok build`).
2. Loads `AGENTS.md` (Product Owner) + `.grok/agents/*` specialists.

Update `PRODUCT.md` as vision and current goal evolve.
