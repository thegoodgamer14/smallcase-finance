# Backend Architecture (v0)

**Status:** v0.1–v0.3 implemented (curated Parquet + metrics + attribution + backtest; CORS for Next.js)  
**Owner:** Backend agent  
**Consumers:** Frontend, Data Analyst, notebooks  
**Related:**
- Curl cookbook: [api.md](../api.md)
- ADR: [002-backend-stack.md](../decisions/002-backend-stack.md)
- Data model: [data-model.md](./data-model.md), [ADR 001](../decisions/001-data-model.md), [data-dictionary.md](../data-dictionary.md)
- Domain rows: `src/smallcase_finance/schemas/models.py` (re-exported via `models/entities.py`; not API DTOs)
- API DTOs: `src/smallcase_finance/schemas/{smallcase,holdings,performance,metrics,nav,attribution,backtest,common}.py`

---

## 1. Goals

- Serve smallcase composition, holdings, NAV, performance series, and risk metrics over a thin HTTP API.
- Keep **financial math pure** so notebooks and unit tests can import the same functions the API uses.
- Read **curated local data** (`data/curated/`) — no live broker, no production auth.
- Stay local-first and reproducible; one process, one data root.

### Non-goals (v0)

- Multi-user auth, sessions, multi-tenancy
- Live trading / order placement
- Full broker integration
- Write-heavy CRUD for portfolios (definitions may be static files initially)
- Microservice split

---

## 2. High-level layout

```
┌─────────────┐     HTTP/JSON      ┌──────────────────────────────────────┐
│  Frontend   │ ─────────────────► │  FastAPI (api/)                      │
│  (Next.js)  │ ◄───────────────── │  routers → services → data_access    │
└─────────────┘                    │                 │                    │
                                   │                 ▼                    │
┌─────────────┐     import         │  calc/  (pure functions)             │
│  Notebooks  │ ─────────────────► │  weights, returns, NAV, risk, etc.   │
│  / tests    │                    └──────────────────────────────────────┘
└─────────────┘                                      │
                                                     ▼
                                   ┌──────────────────────────────────────┐
                                   │  data/curated/  (Parquet + metadata) │
                                   │  DuckDB (in-process query engine)    │
                                   └──────────────────────────────────────┘
```

**Dependency direction (strict):**

```
api  →  services  →  data_access  →  curated files / DuckDB
              ↘         ↗
                calc   (no I/O, no FastAPI, no DuckDB)
schemas  ← used by api + services (request/response DTOs)
```

- `calc/` must never import `api`, `services`, or `data_access`.
- `data_access/` may use DuckDB / Polars / paths; returns plain Python / DataFrames / domain dicts.
- `services/` orchestrate: load data → call calc → map to response schemas.
- `api/` is thin: validate params, call service, map HTTP status codes.

---

## 3. Package map

Installable package root: `src/smallcase_finance/`

| Module | Role | I/O? |
|--------|------|------|
| `api/` | FastAPI app factory, routers, dependency wiring | HTTP only |
| `schemas/` | Pydantic v2 request/response models (API contracts) | No |
| `services/` | Use-case orchestration | Via data_access |
| `calc/` | Pure financial functions | **No** |
| `data_access/` | Read curated Parquet via DuckDB/Polars | Yes (local FS) |
| `models/` | Internal domain types (optional; may mirror schemas lightly) | No |

### Suggested files (skeleton now; flesh out later)

```
src/smallcase_finance/
  __init__.py
  main.py                 # app entry: create_app()
  config.py               # DATA_CURATED_ROOT, currency default, etc.
  api/
    __init__.py
    deps.py               # get_store / get_duckdb connection
    routes/
      health.py
      smallcases.py
      backtest.py         # optional
  schemas/
    common.py             # ErrorResponse, Money, DateRange
    smallcase.py
    holdings.py
    performance.py
    metrics.py
    nav.py
    backtest.py
  services/
    smallcase_service.py
    performance_service.py
    metrics_service.py
    backtest_service.py
  calc/
    weights.py
    returns.py
    nav.py
    risk.py               # vol, max DD, Sharpe, CAGR helpers
    rebalance.py          # rebalance simulation pure logic
  data_access/
    paths.py              # resolve curated paths
    duck.py               # connection helper
    smallcases.py         # list/get definitions
    holdings.py
    prices.py
    performance.py        # precomputed series if present
```

---

## 4. Data access strategy

### Source of truth

- **Curated analytics tables** under `data/curated/` (Parquet preferred).
- Schema ownership: **Data Architect**; ingestion: **Data Engineer**.
- Backend treats curated files as **read-only** in v0.

### Curated entities (aligned with Data Architect)

| Entity | Kind | Path under `data/curated/` | Grain |
|--------|------|----------------------------|-------|
| `instruments` | source | `instruments/instruments.parquet` | `symbol` |
| `prices` | source | `prices/prices.parquet` | `(symbol, date)` |
| `smallcases` | source | `smallcases/smallcases.parquet` | `smallcase_id` |
| `smallcase_constituents` | source (versioned) | `smallcases/smallcase_constituents.parquet` | `(smallcase_id, symbol, effective_from)` |
| `rebalance_events` | source | `rebalances/rebalance_events.parquet` | `(smallcase_id, rebalance_date)` |
| `holdings_snapshots` | optional | `holdings/holdings_snapshots.parquet` | `(smallcase_id, as_of, symbol)` |
| `nav_series` | derived | `nav/nav_series.parquet` | `(smallcase_id, date)` |
| `metrics_snapshot` | derived | `metrics/metrics_snapshot.parquet` | `(smallcase_id, as_of, window)` |
| `contribution` | derived | `metrics/contribution.parquet` | period × symbol |

If derived NAV/metrics are missing, services compute them on the fly via `calc/` + prices + constituents (same rebuild rules as the data model).

### Read path

1. Resolve `DATA_CURATED_ROOT` (default: repo `data/curated/`).
2. Open DuckDB in-process (no server).
3. `SELECT … FROM read_parquet('…')` or register views once at startup.
4. Return rows as list[dict] / Polars DataFrame; services convert to Pydantic.

### Assumptions (document & surface in API metadata where useful)

| Assumption | v0 default |
|------------|------------|
| Currency | INR (`smallcases.currency` / `prices.currency`) |
| Symbols | Uppercase, **no** exchange suffix (`RELIANCE` not `RELIANCE.NS`); exchange on `instruments` |
| Price field | Prefer `close` if pipeline stores adjusted there; else `adj_close` when documented |
| Corporate actions | Only via curated adjusted prices; backend does not adjust raw |
| Weights | Fractions in `[0, 1]`; version sums to 1.0 ± 1e-6; historical via `effective_from` |
| NAV base | `smallcases.base_nav` (default `100.0`) |
| Data freshness | Last curated drop; expose `as_of` / `computed_at` when available |
| Calendar | Non-trading days absent from `prices` (no holiday engine) |
| Missing prices | Align with data-model rebuild rule: exclude symbol that day, renormalize remaining weights; log gaps |

---

## 5. Pure calculation layer (`calc/`)

These functions are the shared brain for API, notebooks, and tests.

### Design rules

- Inputs/outputs: primitives, `datetime.date`, `Decimal` or `float` (prefer `float` for series speed; document precision), dicts, pandas/polars Series/DataFrames.
- No filesystem, no network, no env reads.
- Explicit about annualization (e.g. 252 trading days) and risk-free rate source when used.
- Unit-testable with synthetic series.

### Planned pure functions (contracts, not full impl yet)

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `normalize_weights(weights)` | mapping ticker→weight | normalized mapping (sum=1) | Raise if empty / all zero |
| `portfolio_returns(asset_returns, weights)` | returns matrix + weights | series of portfolio returns | Weights may be static or time-varying |
| `nav_from_returns(returns, start_nav=100.0)` | return series | NAV series | Cumulative product |
| `cagr(nav_or_returns, periods_per_year=252)` | series + dates | float | Document day-count |
| `volatility(returns, periods_per_year=252)` | return series | annualized vol | |
| `max_drawdown(nav)` | NAV series | float (negative or absolute — pick one & document) | |
| `sharpe(returns, rf=0.0, periods_per_year=252)` | returns | float | rf annualized or per-period — document |
| `rebalance_weights(target, current, threshold?)` | weight maps | trade list / new weights | Pure suggestion logic |
| `contribution(returns, weights)` | … | per-ticker contribution | Optional v0.1 |

**Import example for Data Analyst / notebooks:**

```python
from smallcase_finance.calc.risk import cagr, max_drawdown, volatility, sharpe
from smallcase_finance.calc.nav import nav_from_returns
```

---

## 6. API surface (v0 contracts)

Base URL (local): `http://127.0.0.1:8000`  
Content-Type: `application/json`  
Errors: `{ "detail": "..." }` (FastAPI default) or structured `ErrorResponse` later.

### 6.1 `GET /health`

**Purpose:** Liveness + basic data-root check.

**Response 200**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "data_curated_root": "data/curated",
  "data_reachable": true
}
```

---

### 6.2 `GET /smallcases`

**Purpose:** List available smallcases for the UI picker.

**Query (optional):** `tag`, `q` (search name)

**Response 200**

```json
{
  "items": [
    {
      "id": "india-momentum",
      "name": "India Momentum",
      "description": "…",
      "theme": "momentum",
      "currency": "INR",
      "methodology": "equal_weight",
      "rebalance_rule": "quarterly",
      "inception_date": "2020-01-01",
      "as_of": "2026-03-31",
      "constituent_count": 15
    }
  ]
}
```

Path param `{id}` = `smallcase_id` (slug).

---

### 6.3 `GET /smallcases/{id}`

**Purpose:** Smallcase detail + methodology summary.

**Response 200**

```json
{
  "id": "india-momentum",
  "name": "India Momentum",
  "description": "…",
  "theme": "momentum",
  "currency": "INR",
  "methodology": "equal_weight",
  "rebalance_rule": "quarterly",
  "base_nav": 100.0,
  "inception_date": "2020-01-01",
  "benchmark_id": null,
  "notes": null
}
```

Maps from curated `smallcases` (+ optional instrument joins). **404** if unknown id.

---

### 6.4 `GET /smallcases/{id}/holdings`

**Purpose:** Target composition as of a date (active constituent version).

**Query:** `as_of` (ISO date, optional — default latest available version)

**Response 200**

```json
{
  "smallcase_id": "india-momentum",
  "as_of": "2026-03-31",
  "effective_from": "2026-01-01",
  "methodology": "equal_weight",
  "holdings": [
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries",
      "weight": 0.0667,
      "sector": "Energy"
    }
  ],
  "weight_sum": 1.0
}
```

**Resolution:** constituents where `effective_from <= as_of` and (`effective_to` is null or `>= as_of`); pick the latest version set. Prefer target weights from `smallcase_constituents`; optional `source=holdings_snapshots` later.

**Notes for Frontend:** weights are fractions in `[0, 1]`, not percent. Sum ≈ 1.0 (±1e-6). Field is `symbol`, not `ticker`.

---

### 6.5 `GET /smallcases/{id}/performance`

**Purpose:** Time series for charts (NAV and/or cumulative return).

**Query:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start` | date | inception / first available | Inclusive |
| `end` | date | latest | Inclusive |
| `benchmark` | bool | false | Include benchmark series if configured |
| `freq` | `D`\|`W`\|`M` | `D` | Optional downsampling |

**Response 200**

```json
{
  "smallcase_id": "india-momentum",
  "currency": "INR",
  "start": "2020-01-01",
  "end": "2026-03-31",
  "series": [
    { "date": "2020-01-01", "nav": 100.0, "daily_return": null },
    { "date": "2020-01-02", "nav": 100.4, "daily_return": 0.004 }
  ],
  "benchmark_series": null
}
```

**Source priority:** curated `nav_series` if present for the window; else compute via `calc/` from constituents × prices. `nav` uses `base_nav` at inception (not silently rebased unless query `rebase=true` is added later).

---

### 6.6 `GET /smallcases/{id}/metrics`

**Purpose:** Summary risk/return cards for dashboard.

**Query:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start` / `end` | date | ITD | Custom window |
| `window` | enum | `ITD` | `1M`\|`3M`\|`6M`\|`1Y`\|`YTD`\|`ITD`\|`custom` (matches `metrics_snapshot.window`) |

**Response 200**

```json
{
  "smallcase_id": "india-momentum",
  "start": "2020-01-01",
  "end": "2026-03-31",
  "window": "ITD",
  "currency": "INR",
  "metrics": {
    "cagr": 0.142,
    "volatility": 0.18,
    "max_drawdown": -0.27,
    "sharpe": 0.65,
    "total_return": 1.21,
    "n_observations": 1540
  },
  "assumptions": {
    "periods_per_year": 252,
    "risk_free_rate": 0.0,
    "return_type": "simple",
    "price_field": "close"
  }
}
```

**Source priority:** `metrics_snapshot` for matching window if fresh; else compute from NAV series via `calc.risk`.

**Conventions (binding for Frontend + Analyst):**

- Ratios (`cagr`, `volatility`, `sharpe`, `total_return`) are **decimals**, not percent (`0.142` = 14.2%).
- `max_drawdown` is **negative** (e.g. `-0.27` = −27%).
- `assumptions` must always be present so charts/tooltips stay honest.

---

### 6.7 `GET /smallcases/{id}/nav`

**Purpose:** Lightweight NAV series (or latest point) for headers / sparklines.

**Query:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start` / `end` | date | full range | Optional window |
| `latest_only` | bool | false | If true, return single latest point |

**Response 200** (`latest_only=false`)

```json
{
  "smallcase_id": "india-momentum",
  "currency": "INR",
  "series": [
    { "date": "2020-01-01", "nav": 100.0 },
    { "date": "2026-03-31", "nav": 221.0 }
  ]
}
```

**Response 200** (`latest_only=true`)

```json
{
  "smallcase_id": "india-momentum",
  "currency": "INR",
  "as_of": "2026-03-31",
  "nav": 221.0
}
```

---

### 6.8 `GET /smallcases/{id}/attribution`

**Purpose:** Simple per-symbol contribution for dashboard “top contributors”.

**Query:** `period_start`, `period_end` (optional exact match on curated rows; default = widest available period)

**Response 200**

```json
{
  "smallcase_id": "india-momentum",
  "period_start": "2020-01-01",
  "period_end": "2026-03-31",
  "items": [
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries",
      "avg_weight": 0.07,
      "weight_start": 0.067,
      "weight_end": 0.072,
      "symbol_return": 0.45,
      "contribution": 0.0315
    }
  ],
  "residual": null,
  "portfolio_return": 0.21,
  "notes": "Simple single-period contribution …"
}
```

**Source:** curated `metrics/contribution.parquet`. Empty `items` if table missing (UI degrades).

---

### 6.9 Optional: backtest / rebalance simulation

**Preferred for v0.1+:** `POST /backtest` (body can grow).

**`POST /backtest`** (recommended shape)

```json
{
  "smallcase_id": "india-momentum",
  "start": "2021-01-01",
  "end": "2025-12-31",
  "rebalance_rule": "quarterly",
  "methodology": "equal_weight",
  "initial_nav": 100.0,
  "threshold": null
}
```

**Response 200**

```json
{
  "smallcase_id": "india-momentum",
  "params": { "rebalance_rule": "quarterly", "methodology": "equal_weight" },
  "metrics": { "cagr": 0.11, "max_drawdown": -0.22, "volatility": 0.17, "sharpe": 0.5 },
  "nav_series": [{ "date": "2021-01-01", "nav": 100.0 }],
  "rebalance_events": [
    { "date": "2021-04-01", "turnover": 0.18 }
  ]
}
```

Idempotent for same body; pure simulation over curated prices (no side effects). Does not write curated Parquet.

---

## 7. Service layer responsibilities

| Service | Calls | Produces |
|---------|-------|----------|
| `SmallcaseService` | data_access smallcases + constituents | list/detail/holdings DTOs |
| `PerformanceService` | precomputed NAV or prices + calc | performance series |
| `MetricsService` | performance series + `calc.risk` | metrics DTO + assumptions |
| `NavService` | subset of performance / nav table | nav DTO |
| `BacktestService` | prices + constituents history + `calc.rebalance` | simulation result |

Services own **business rules** (e.g. “if nav_series missing, recompute from weights × prices”). Routers do not.

---

## 8. Error model

| HTTP | When |
|------|------|
| 404 | Unknown `smallcase_id` |
| 400 | Invalid date range (`start > end`), bad query enum |
| 422 | Pydantic validation errors |
| 503 | Curated data root missing / unreadable (`data_reachable: false` on health) |

Do not leak filesystem paths beyond the configured root name in production-facing messages (local v0 may include path on `/health` only).

---

## 9. Config

Environment / settings (pydantic-settings or simple module):

| Key | Default | Meaning |
|-----|---------|---------|
| `DATA_CURATED_ROOT` | `<repo>/data/curated` | Parquet root |
| `API_HOST` | `127.0.0.1` | Bind host |
| `API_PORT` | `8000` | Bind port |
| `DEFAULT_CURRENCY` | `INR` | Fallback currency |
| `PERIODS_PER_YEAR` | `252` | Annualization |
| `DEFAULT_RF` | `0.0` | Risk-free for Sharpe |

---

## 10. Collaboration contracts

### Frontend

- Consume only `/` JSON contracts above; do not parse Parquet directly.
- Treat metrics as decimals; format % in the UI.
- Use `/health` for “API up” indicator.
- Holdings weights are fractions.

### Data Analyst

- Prefer `from smallcase_finance.calc import …` for offline metrics so dashboard and notebooks match.
- If a metric definition changes, change it in `calc/` once; API picks it up via services.
- Curated schema changes should be coordinated via Data Architect; backend `data_access` adapters are the only place SQL/path strings live.

### Data Architect / Engineer

- Stable keys: `smallcase_id`, `symbol`, ISO `date` (see data dictionary).
- Prefer Parquet with consistent dtypes (dates as date, weights as float64).
- Derived `nav_series` / `metrics_snapshot` are a **cache**; backend may recompute if missing.
- Domain validation models live in `models/entities.py`; API DTOs stay in `schemas/`.

---

## 11. Implementation phases

| Phase | Deliverable |
|-------|-------------|
| **v0 design (this doc)** | Architecture + ADR + package skeleton |
| **v0.1** | `/health`, `/smallcases`, `/smallcases/{id}`, holdings; DuckDB → curated Parquet |
| **v0.2** | NAV + performance + metrics via `calc/` (read derived tables when present) |
| **v0.3** | Optional backtest endpoint; notebook examples importing `calc/` |

---

## 12. Run

```bash
# from repo root
pip install -e ".[dev]"          # or: make install
make pipeline                    # ensure data/curated has Parquet
make api                         # or the uvicorn line below

export DATA_CURATED_ROOT=data/curated   # optional; default is repo data/curated
uvicorn smallcase_finance.main:app --reload --app-dir src
# equivalent:
# uvicorn smallcase_finance.api.main:app --reload --app-dir src
```

OpenAPI: `http://127.0.0.1:8000/docs`

| Endpoint | Status |
|----------|--------|
| `GET /health` | live |
| `GET /smallcases` | live (curated) |
| `GET /smallcases/{id}` | live |
| `GET /smallcases/{id}/holdings` | live (target constituents) |
| `GET /smallcases/{id}/performance` | live (nav_series; no on-the-fly recompute yet) |
| `GET /smallcases/{id}/metrics` | live (snapshot or calc.risk from NAV) |
| `GET /smallcases/{id}/nav` | live |
| `GET /smallcases/{id}/attribution` | live (curated contribution; empty if missing) |
| `POST /backtest` | live (in-memory rebalance sim; no Parquet writes) |
| CORS | `localhost:3000` / `127.0.0.1:3000` |

---

## 13. Open items

1. **Benchmark series source** — `benchmark_id` reserved; no prices table for indices yet.
2. **Holdings endpoint mode** — v0 default = **target** constituents; optional drifted / broker snapshots later.
3. **Derived freshness** — when to trust `metrics_snapshot.computed_at` vs always recompute for custom windows.
4. **On-the-fly NAV** — when `nav_series` missing, recompute from constituents × prices via `calc/` (TODO in services).
5. **Series freq** — `freq=W|M` downsampling not implemented (daily only).
