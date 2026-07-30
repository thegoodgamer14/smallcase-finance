# PRD — Portfolio Decision v1 (Backend + Frontend)

**Product:** Backtest Hero / Smallcase Finance  
**Codename:** Portfolio Decision v1  
**Version:** 1.0  
**Date:** 2026-07-30  
**Status:** Proposed — implement next (supersedes near-term priority of pure “Phase 3 polish” for founder goal)  
**Owner:** Product Owner (founder)  
**Related:**  
- Vision / feedback north star: *“Given my current holdings and this candidate basket, should I put the next rupee here / rebalance?”*  
- Prior: [prd-sip-lab.md](./prd-sip-lab.md), [ROADMAP.md](../ROADMAP.md), [kite-connect.md](../integrations/kite-connect.md)  
- Binding data policy: [ADR 005](../decisions/005-upstox-sole-market-data.md) (Upstox sole OHLCV)  
- SIP engine: Phases 1–2 shipped (`POST /backtests/sip`, `/sip-lab`)

---

## 1. Problem statement

Today the app can:

- Show **demo / authored smallcase** NAV, metrics, and holdings (not the founder’s live book).
- Run a correct **SIP Lab** backtest (XIRR) over curated prices.
- Smoke-test **Kite** login + holdings via CLI / status endpoints.

It **cannot** yet answer the founder’s real job:

1. **What do I hold right now** (equity book on Kite)?  
2. **If I build or copy a basket of stocks**, what did it do historically (SIP and/or lump)?  
3. **Relative to a benchmark**, is it good enough to fund or rebalance into?  
4. **Are the numbers trustworthy** (sample vs Upstox, missing bars, stale token)?

Without (1) and (4), charts are research toys. Without (2)–(3), holdings are a static table.

---

## 2. Product goal (this slice)

Ship a **personal decision loop** end-to-end:

```text
Connect Kite (session) → Snapshot equity holdings → View portfolio
        ↓
Compose or select candidate basket → Ensure prices (Upstox/curated)
        ↓
Run decision backtest (SIP primary; lump optional) + benchmark
        ↓
See DQ banners + clear “invest / rebalance judgment” summary
```

**Success metric (founder):** Within one local session (after daily Kite + Upstox tokens), open the app and complete:

- See **my** equity holdings with values and weights.  
- Pick 3–15 symbols (from holdings or typed), set weights, run SIP backtest.  
- See XIRR + equity curve + **vs benchmark** + **data quality** state.  
- Export or screenshot is optional; **decision clarity** is mandatory.

---

## 3. Users & context

| Role | Context |
|------|---------|
| **Founder (sole user)** | Equities primarily on Zerodha **Kite**; may own Smallcase.com managers (positions still appear as stocks in Kite where applicable); **Coin MF deferred**. |
| **Environment** | Local-first; optional Vercel front for OAuth HTTPS; **public repo** — secrets only in env. |
| **Market** | India equity/ETF, INR. |

---

## 4. Scope — IN for v1 (implement now)

| # | Capability | Backend | Frontend |
|---|------------|---------|----------|
| **P1** | Kite equity holdings **sync + read** as portfolio of record | Yes | Yes — Portfolio page |
| **P2** | Portfolio view: value, weights, sectors (best-effort), last sync, connection status | Yes | Yes |
| **P3** | Candidate basket authoring (inline symbols + weights / equal-weight) | Extend strategy APIs | Decision Lab UI |
| **P4** | Price readiness: list symbols missing from curated; trigger or document Upstox sync for basket | Yes | Yes — warnings + CTA |
| **P5** | Decision backtest: **reuse SIP engine** for candidate basket (primary path) | Extend `POST /backtests/sip` if needed | Decision Lab + deep link SIP Lab |
| **P6** | **Benchmark SIP** (one ETF/index proxy via Upstox/curated, e.g. NIFTYBEES) | Yes | Yes — overlay + delta XIRR |
| **P7** | **Data quality pack**: sample vs Upstox, partial basket, missing bars, stale/missing tokens | Yes | Yes — banners, block “real” claims |
| **P8** | Optional: **weight gap** (current portfolio weights vs candidate target) — no orders | Yes | Yes — simple table |
| **P9** | Nav rename / IA: Portfolio + Decision Lab as primary; demote demo smallcase routes | Thin | Yes |

---

## 5. Scope — OUT for v1 (explicit)

| Out | Rationale |
|-----|-----------|
| Coin / mutual fund import or MF NAV | Deferred; equity decision tool first |
| Smallcase.com scrape / manager API | Positions via Kite if held; baskets authored in-app |
| Live trading, order tickets, GTT | Non-goal forever for this product line |
| F&O, commodity, currency | Out of model |
| Multi-user auth, SaaS | Personal only |
| yfinance / bhavcopy / multi-vendor prices | ADR 005 |
| Full cost model (STT, brokerage matrix) | Phase later; zero costs remain default |
| Multi-strategy tournament / strategy library productization | Nice-to-have later |
| Perfect sector taxonomy / corporate actions engine | Best-effort only |
| Treating sample prices as production decisions | Must be blocked or labeled harshly |
| Live “always on” broker sync | Snapshot + explicit Refresh |
| Replacing SIP Lab with a second engine | **Reuse** SIP service |

---

## 6. Principles (binding)

1. **Holdings truth before pretty analytics.** No portfolio page without real snapshot path.  
2. **Kite = book; Upstox = history.** Never use Kite for multi-year OHLCV.  
3. **SIP/XIRR is the primary invest decision metric** when funding is monthly; lump/NAV is secondary for theme quality.  
4. **One decision surface** must not silently mix sample and live data.  
5. **CLI + API first for sync; UI for view and decide.** Token exchange may remain semi-manual.  
6. **Small diffs, reuse existing modules** (`integrations/kite`, `SipService`, pipeline, AppShell).  
7. **Public repo:** never log tokens; never commit holdings dumps with PII if avoidable (local `data/` gitignored paths preferred).

---

## 7. User stories

### US-1 — Connect & refresh book

**As** the founder, **I want** to refresh my Kite equity holdings into the app, **so that** I see my real book, not demo smallcases.

**Acceptance:**

- Status shows whether Kite app + session are configured.  
- “Refresh holdings” succeeds when `KITE_ACCESS_TOKEN` valid → new snapshot timestamp.  
- On 403/token expiry, UI shows clear re-login steps (link to existing kite login flow).  
- Holdings table shows symbol, qty, avg price, LTP (if API returns), value, weight %, product (CNC etc.).

### US-2 — Trust the portfolio number

**As** the founder, **I want** to know when the book is stale, **so that** I don’t rebalance on yesterday’s accident.

**Acceptance:**

- UI shows `as_of` / `synced_at` and age (e.g. “2h ago”).  
- If no snapshot exists, empty state with CTA to connect/refresh — not sample smallcase data disguised as “My portfolio”.

### US-3 — Build a candidate basket

**As** the founder, **I want** to select stocks (from my holdings or free type) and weights, **so that** I can test a potential smallcase before buying.

**Acceptance:**

- Add/remove symbols; equal-weight or custom weights; validate sum ≈ 1.  
- Persist as ephemeral run config (session) and optionally save as strategy YAML/JSON under `config/strategies/` or `data/raw/strategies/` (see §10).  
- Symbols normalized uppercase, no exchange suffix.

### US-4 — Run decision backtest

**As** the founder, **I want** to run a monthly SIP on that basket over N years, **so that** I see XIRR and path under realistic funding.

**Acceptance:**

- Uses existing SIP engine semantics (day-of-month → next session; zero costs default).  
- Response includes XIRR, total invested, final MV, max DD, cashflows summary, `data_source`.  
- If prices incomplete, run may be partial **with warnings** or hard-fail in strict mode (config).

### US-5 — Compare to benchmark

**As** the founder, **I want** the same SIP into a benchmark ETF, **so that** I know if the basket beat “just buy the index”.

**Acceptance:**

- Default benchmark symbol configurable (default `NIFTYBEES` or documented equivalent present in instruments/prices).  
- Same SIP amount, day, date range as candidate.  
- UI shows candidate XIRR, benchmark XIRR, delta, and optional dual MV chart (normalized).

### US-6 — Rebalance hint (lite)

**As** the founder, **I want** to see weight differences between my book and the candidate target, **so that** I know what I’d need to buy/sell later on Kite (manually).

**Acceptance:**

- Table: symbol | portfolio weight | target weight | delta weight | approx ₹ delta (optional if MV known).  
- Explicit copy: “Not an order. Execute manually on Kite.”

### US-7 — Honest data quality

**As** the founder, **I want** to be blocked from treating sample data as a real decision, **so that** I don’t fool myself.

**Acceptance:**

- `data_source=sample` → red/amber banner: “Demo prices — not for live capital decisions.”  
- Missing symbols listed; coverage % shown.  
- Optional env `STRICT_MARKET_DATA=1`: refuse SIP decision report unless `data_source=upstox` (or equivalent) and coverage ≥ threshold.

---

## 8. Information architecture (frontend)

### 8.1 Navigation (AppShell)

| Route | Label | Role |
|-------|-------|------|
| `/portfolio` | **Portfolio** | Live Kite equity book (default home after v1) |
| `/decide` | **Decision Lab** | Basket compose + SIP + benchmark + gap |
| `/sip-lab` | SIP Lab | Existing advanced SIP form (keep; link from Decide) |
| `/` | Themes (demo) | Existing smallcase dashboard — relabel “Theme demo” or keep secondary |
| `/holdings` | Theme holdings | Existing smallcase target weights — **not** live book |
| `/performance` | Theme performance | Existing |

**Recommended default landing:** `/portfolio` if snapshot exists, else `/portfolio` empty state (not demo dashboard).  
Optional: env or UI toggle `NEXT_PUBLIC_DEFAULT_HOME=portfolio|dashboard`.

### 8.2 Page specs

#### A. `/portfolio` — Portfolio

**Layout:**

1. **Connection strip**  
   - Kite: connected / needs login / missing API key  
   - Last sync timestamp  
   - Button: **Refresh holdings**  
   - Link: how to login (docs snippet or modal)

2. **KPI row**  
   - Total equity value (Σ qty × LTP or last_price)  
   - Position count  
   - Day P&amp;L if available from Kite fields (optional; null-safe)  
   - Cash **not** required in v1

3. **Holdings table** (sortable)  
   - Symbol, exchange, qty, avg, LTP, value, weight %, product, ISIN (optional column)

4. **Allocation**  
   - Weight bars or simple pie (top N + Other)  
   - Sector breakdown **if** sector join available from instruments; else hide with “sector unavailable”

5. **Actions**  
   - “Use selected as basket” → navigate to `/decide` with query or session state  
   - “Sync prices for held symbols” → calls backend to queue/trigger Upstox sync for symbols (or show CLI command if API cannot long-run)

**Empty / error states:** mirror existing `EmptyState` / `ErrorBanner` patterns.

#### B. `/decide` — Decision Lab

**Layout (single scroll page):**

1. **Basket builder**  
   - Multi-select from portfolio symbols + free-text add  
   - Weight mode: Equal | Custom  
   - Custom: editable % that normalize or must sum to 100%  
   - SIP params: amount, day-of-month, start, end (defaults: amount 10000, day 1, start = end−3y or price history start)

2. **Benchmark**  
   - Symbol default `NIFTYBEES`; editable  
   - Toggle: include benchmark SIP (default on)

3. **Run**  
   - Primary CTA: **Run decision backtest**  
   - Loading + cancel not required (short runs)

4. **Results**  
   - XIRR (primary), invested, final value, max DD  
   - Benchmark XIRR + delta  
   - Chart: portfolio MV vs benchmark MV (or growth of ₹1)  
   - DQ panel: source, coverage, missing symbols, warnings[]  
   - Export JSON/CSV reuse SIP Lab export patterns

5. **Weight gap** (if portfolio snapshot exists)  
   - Delta table as US-6

6. **Footer links**  
   - Open same config in SIP Lab (advanced)  
   - Link to price sync docs if coverage low

#### C. Shell / global

- DataSourceBanner: extend to show **portfolio snapshot age** and **Kite session** when on `/portfolio` or `/decide`.  
- Product title in header: optional rename **Backtest Hero** (copy only; not required for AC).

---

## 9. Backend architecture

### 9.1 Modules to add / extend

| Module | Path (proposed) | Responsibility |
|--------|-----------------|----------------|
| Kite holdings sync | `integrations/kite/` + `pipeline` or `services/portfolio_service.py` | Fetch holdings → normalize → write raw drop + curated snapshot |
| Portfolio read | `data_access/portfolio.py` | Read latest curated snapshot |
| Portfolio API | `api/routes/portfolio.py` | REST for status, refresh, latest holdings |
| Decision backtest | `services/decision_service.py` | Orchestrate candidate SIP + benchmark SIP + DQ + optional gap |
| Decision API | `api/routes/decision.py` | `POST /decisions/run` |
| DQ helpers | `services/dq.py` or inside decision | Coverage, sample flag, warnings |
| Schemas | `schemas/portfolio.py`, `schemas/decision.py` | Pydantic DTOs |

Reuse:

- `KiteClient.holdings()`  
- `SipService` / `POST /backtests/sip` internals  
- `MarketDataProvider` / Upstox sync  
- Strategy models for inline basket

### 9.2 Data model (curated)

#### `portfolio_holdings_snapshots` (logical table)

**Path:** `data/curated/portfolio/holdings_snapshot.parquet`  
**(Optional archive):** `data/raw/holdings/kite/YYYY-MM-DD_HHMMSS/holdings.json`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `snapshot_id` | string | yes | UUID or `kite_{utc_ts}` |
| `synced_at` | timestamp UTC | yes | When fetched |
| `source` | string | yes | `kite` |
| `symbol` | string | yes | Uppercase ticker |
| `exchange` | string | yes | e.g. NSE, BSE |
| `quantity` | float | yes | |
| `average_price` | float | no | |
| `last_price` | float | no | From Kite payload |
| `pnl` | float | no | |
| `product` | string | no | CNC / etc. |
| `isin` | string | no | |
| `instrument_token` | int | no | |
| `value` | float | no | qty × last_price if both present |
| `weight` | float | no | value / total_value |

**Grain:** one row per (snapshot_id, symbol, exchange, product) — document uniqueness.  
**Latest read:** max(`synced_at`) snapshot_id, then all rows for that id.

**Gitignore:** ensure `data/raw/holdings/` and optionally curated portfolio snapshots are not committed if they contain personal positions (recommend gitignore personal holdings; sample fixture for tests only).

#### Instruments join (optional)

Join `symbol` → `instruments.sector` for sector breakdown when present.

### 9.3 API contracts

Base URL remains local FastAPI. All new routes under OpenAPI tags `portfolio`, `decisions`.

#### 9.3.1 `GET /portfolio/status`

**Response:**

```json
{
  "kite_app_configured": true,
  "kite_session_configured": true,
  "login_url": "https://kite.zerodha.com/connect/login?...",
  "has_snapshot": true,
  "latest_synced_at": "2026-07-30T10:15:00Z",
  "position_count": 12,
  "total_value": 1534210.5,
  "currency": "INR",
  "message": "OK"
}
```

No secrets. Mirrors spirit of `GET /integrations/kite/status` but portfolio-oriented; may wrap the same helpers.

#### 9.3.2 `POST /portfolio/refresh`

**Behavior:**

1. Require Kite session; else **401/503** with structured error code `KITE_SESSION_MISSING` or `KITE_AUTH_FAILED`.  
2. Call Kite holdings API.  
3. Write raw JSON drop under `data/raw/holdings/kite/...`.  
4. Normalize → append/replace curated snapshot parquet (v1: **replace file with latest only** is OK if archive is in raw).  
5. Return latest portfolio payload (same shape as GET latest).

**Response:** `PortfolioResponse` (below).

**Idempotency:** each call creates a new snapshot_id; latest is max synced_at.

#### 9.3.3 `GET /portfolio/holdings/latest`

**Response `PortfolioResponse`:**

```json
{
  "snapshot_id": "kite_20260730T101500Z",
  "synced_at": "2026-07-30T10:15:00Z",
  "source": "kite",
  "currency": "INR",
  "total_value": 1534210.5,
  "position_count": 12,
  "holdings": [
    {
      "symbol": "INFY",
      "exchange": "NSE",
      "quantity": 10,
      "average_price": 1450.0,
      "last_price": 1520.0,
      "value": 15200.0,
      "weight": 0.0099,
      "pnl": 700.0,
      "product": "CNC",
      "isin": "INE009A01021",
      "sector": null
    }
  ],
  "warnings": []
}
```

**404** if no snapshot: `{ "detail": "No portfolio snapshot. POST /portfolio/refresh first." }`

#### 9.3.4 `GET /portfolio/symbols`

Convenience list of held symbols for Decision Lab multiselect.

```json
{ "symbols": ["INFY", "TCS", ...], "synced_at": "..." }
```

#### 9.3.5 `POST /decisions/run`

**Request:**

```json
{
  "basket": {
    "mode": "custom_weights",
    "constituents": [
      { "symbol": "INFY", "target_weight": 0.25 },
      { "symbol": "TCS", "target_weight": 0.25 },
      { "symbol": "RELIANCE", "target_weight": 0.25 },
      { "symbol": "HDFCBANK", "target_weight": 0.25 }
    ]
  },
  "sip": {
    "amount": 10000,
    "day_of_month": 1,
    "start_date": "2023-01-01",
    "end_date": null
  },
  "benchmark_symbol": "NIFTYBEES",
  "include_benchmark": true,
  "include_weight_gap": true,
  "strict_market_data": false
}
```

**Validation:**

- ≥1 constituent; weights sum ∈ [1±1e-6] if custom; equal mode computes 1/n.  
- Symbols uppercase.  
- SIP amount &gt; 0; day_of_month in documented range (1–28).  
- Reject empty basket.

**Behavior:**

1. Build `StrategyConfig`-compatible inline basket + SIP.  
2. Resolve price coverage for basket (+ benchmark).  
3. If `strict_market_data` and (sample source or coverage &lt; 1.0 for required symbols): **422** with codes + missing list.  
4. Else run `SipService` for candidate; if benchmark, run second SIP single-name basket weight 1.0.  
5. If `include_weight_gap` and latest portfolio exists: compute gap table (symbols union of book ∩ target; missing targets weight 0 in book).  
6. Assemble warnings.

**Response (sketch):**

```json
{
  "run_id": "dec_...",
  "data_source": "upstox",
  "coverage": {
    "basket_symbols": 4,
    "basket_with_prices": 4,
    "benchmark_ok": true,
    "missing_symbols": [],
    "price_start": "2023-01-02",
    "price_end": "2026-07-29"
  },
  "warnings": [],
  "candidate": {
    "xirr": 0.142,
    "total_invested": 360000,
    "final_value": 410000,
    "max_drawdown": -0.18,
    "series": [ { "date": "2023-01-02", "market_value": 10000, "invested_cum": 10000 } ],
    "cashflows_summary": { "n_contributions": 36 }
  },
  "benchmark": {
    "symbol": "NIFTYBEES",
    "xirr": 0.121,
    "final_value": 395000,
    "series": []
  },
  "delta_xirr": 0.021,
  "weight_gap": [
    {
      "symbol": "INFY",
      "portfolio_weight": 0.05,
      "target_weight": 0.25,
      "delta_weight": 0.20,
      "approx_value_delta": 300000
    }
  ],
  "disclaimer": "Zero transaction costs. Not investment advice. Execute trades manually."
}
```

Series may be downsampled for UI (e.g. monthly) — document max points or full daily with client thin.

#### 9.3.6 `GET /decisions/price-coverage?symbols=INFY,TCS`

Lightweight preflight for UI before run.

```json
{
  "data_source": "upstox",
  "symbols": [
    { "symbol": "INFY", "has_prices": true, "start": "2020-01-01", "end": "2026-07-29" },
    { "symbol": "FOO", "has_prices": false, "start": null, "end": null }
  ]
}
```

#### 9.3.7 Extend existing (minimal)

| Endpoint | Change |
|----------|--------|
| `POST /backtests/sip` | Allow fully inline basket if not already; keep backward compatible |
| `GET /integrations/kite/status` | Unchanged; Portfolio status may compose it |
| Upstox sync | Optional `POST /integrations/upstox/sync` body `{ "symbols": [] }` if safe for long request; else keep Make/CLI and return 202 + message |

**Long-running sync:** Prefer CLI/Make for multi-year multi-symbol. API may:

- Sync **only missing symbols, last N years** with timeout, or  
- Return instructions: `make sync-upstox SYMBOLS=...`  

Document chosen approach in implementation; **v1 AC:** founder can get prices for a 10-name basket without reading source code (README section + UI message).

### 9.4 Error model

Use consistent JSON:

```json
{
  "error_code": "KITE_AUTH_FAILED",
  "message": "Kite rejected the session token.",
  "details": { "hint": "Run make kite-login ..." }
}
```

| Code | HTTP | Meaning |
|------|------|---------|
| `KITE_SESSION_MISSING` | 503 | No access token |
| `KITE_AUTH_FAILED` | 401 | Token invalid/expired |
| `KITE_UPSTREAM` | 502 | Kite 5xx / network |
| `NO_SNAPSHOT` | 404 | No holdings yet |
| `INVALID_BASKET` | 422 | Weights/symbols |
| `INSUFFICIENT_PRICES` | 422 | Strict mode / empty panel |
| `BENCHMARK_UNAVAILABLE` | 422 | Benchmark missing prices |
| `CURATED_UNAVAILABLE` | 503 | Pipeline not run |

### 9.5 Security & privacy

- Tokens only in env / memory during request; never in API responses.  
- Holdings endpoints are local-trust (no multi-user auth in v1) — same as current API.  
- If deploying API publicly, founder accepts risk; document “localhost only” recommendation.  
- Gitignore personal holdings paths; tests use fixture holdings only.

### 9.6 Config / env

| Variable | Default | Purpose |
|----------|---------|---------|
| `KITE_API_KEY` | — | Existing |
| `KITE_API_SECRET` | — | Existing |
| `KITE_ACCESS_TOKEN` | — | Existing |
| `KITE_REDIRECT_URI` | — | Existing |
| `DEFAULT_BENCHMARK_SYMBOL` | `NIFTYBEES` | Decision Lab default |
| `STRICT_MARKET_DATA` | `0` | Global strict default for decisions |
| `PORTFOLIO_CURATED_PATH` | `data/curated/portfolio/` | Override |
| Existing Upstox vars | — | Unchanged |

---

## 10. Frontend architecture

### 10.1 Tech constraints

- Next.js App Router, TypeScript, Tailwind, Recharts — match `apps/web`.  
- API client: extend `apps/web/src/lib/api.ts` + types in `types.ts`.  
- State: React context or page-local state; optional `sessionStorage` for draft basket.  
- Reuse: `MetricCard`, `ErrorBanner`, `EmptyState`, `DataSourceBanner`, chart primitives, SIP export helpers.

### 10.2 New files (proposed)

```text
apps/web/src/app/portfolio/page.tsx
apps/web/src/app/decide/page.tsx
apps/web/src/components/portfolio/ConnectionStrip.tsx
apps/web/src/components/portfolio/PortfolioTable.tsx
apps/web/src/components/portfolio/PortfolioKpis.tsx
apps/web/src/components/decide/BasketBuilder.tsx
apps/web/src/components/decide/DecisionResults.tsx
apps/web/src/components/decide/WeightGapTable.tsx
apps/web/src/components/decide/DqPanel.tsx
apps/web/src/lib/api.ts          # + portfolio + decision methods
apps/web/src/lib/types.ts        # + DTOs
apps/web/src/components/shell/AppShell.tsx  # nav items
```

### 10.3 UX copy (must ship)

| Situation | Copy tone |
|-----------|-----------|
| No Kite token | “Connect Kite to load your equity book. Prices still come from Upstox.” |
| Sample data on decision run | “These results use demo prices. Do not use them to size real positions.” |
| Weight gap | “Suggested weight changes only — place orders yourself on Kite.” |
| Zero costs | “Backtest assumes zero brokerage, STT, and slippage.” |
| Theme demo vs portfolio | Holdings nav under themes: “Theme target weights (not your broker book).” |

### 10.4 Accessibility & polish (minimum)

- Tables keyboard-scrollable; buttons labeled.  
- Loading skeletons or spinners on refresh/run.  
- Mobile: stack KPIs; tables horizontal scroll — don’t block v1 on perfect mobile.

### 10.5 Frontend non-goals

- Redesign entire design system.  
- Real-time websocket prices.  
- Offline PWA.  
- Complex drag-and-drop weight editor (inputs enough).

---

## 11. SIP Lab relationship

| Concern | Decision |
|---------|----------|
| Engine | **Single** SIP engine; Decision Lab is an orchestration UX |
| SIP Lab page | **Keep** for power users / YAML strategies |
| Duplication | Decision Lab may call `POST /decisions/run` only; SIP Lab keeps `POST /backtests/sip` |
| Strategy files | Optional “Save basket as strategy” later; v1 may be run-only without persist |

---

## 12. Testing requirements

### Backend

| Area | Tests |
|------|-------|
| Normalize Kite payload → holdings rows | Unit, fixture JSON |
| Snapshot write/read latest | Unit with temp dir |
| `POST /portfolio/refresh` | Mock Kite transport (existing pattern in `test_kite.py`) |
| `POST /decisions/run` | Golden: 2-symbol basket + synthetic prices → XIRR finite; benchmark path |
| Weight gap math | Unit |
| DQ: missing symbol | Assert warning or 422 in strict |
| API smoke | Extend `test_api_smoke.py` for new routes (mock or sample data) |

### Frontend

| Area | Tests |
|------|-------|
| Manual E2E | Document in PR: refresh → table → decide → run |
| Optional | Light component tests not required if timeboxed; prefer Playwright later |

### Fixtures

- `tests/fixtures/kite_holdings_sample.json`  
- Do not use founder’s real holdings in CI.

---

## 13. Documentation deliverables (same PR train)

1. This PRD (source of truth for scope).  
2. Short ADR: **007 — Portfolio of record = Kite equity snapshots; decisions orchestrate SIP + benchmark**.  
3. Update [PRODUCT.md](../../PRODUCT.md) current goal → Portfolio Decision v1.  
4. Update [ROADMAP.md](../ROADMAP.md): insert **Phase 4a Portfolio + Decision** before/alongside P3; Coin remains later.  
5. [api.md](../api.md): new endpoints.  
6. [kite-connect.md](../integrations/kite-connect.md): refresh holdings via API/UI.  
7. README: “Daily path” — kite login → portfolio refresh → upstox sync symbols → decide.

---

## 14. Implementation plan (work packages)

Suggested order; each package is a reviewable PR where possible.

| ID | Work package | Owner agent | Depends | Size |
|----|--------------|-------------|---------|------|
| **PD-0** | ADR 007 + PRODUCT/ROADMAP pointer + gitignore holdings paths | PO | — | S |
| **PD-1** | Data model + portfolio write/read (Parquet) + unit tests | data-architect + data-engineer | PD-0 | M |
| **PD-2** | Portfolio service + `GET/POST` portfolio APIs + kite mock tests | backend | PD-1 | M |
| **PD-3** | Decision service: SIP + benchmark + coverage + weight gap | backend + data-analyst | PD-1, SIP exists | L |
| **PD-4** | `POST /decisions/run` + `GET price-coverage` + OpenAPI/docs | backend | PD-3 | M |
| **PD-5** | Portfolio UI page + shell nav + API client | frontend + design (light) | PD-2 | M |
| **PD-6** | Decision Lab UI + results + DQ + gap | frontend | PD-4, PD-5 | L |
| **PD-7** | Price readiness UX (coverage + sync instructions/API) | backend + frontend | PD-4 | M |
| **PD-8** | Strict mode + banners + e2e founder script in docs | backend + frontend + PO | PD-6 | S |
| **PD-9** | Optional: default home `/portfolio`; rename copy Backtest Hero | frontend | PD-5 | S |

**Parallelism:** PD-1/2 ‖ design wireframe for PD-5/6; PD-3 after PD-1; PD-5 after PD-2; PD-6 after PD-4.

---

## 15. Definition of Done (v1 exit gate)

- [ ] Founder with valid Kite token can **Refresh** and see real holdings in `/portfolio`.  
- [ ] Token failure produces actionable UI, not a blank crash.  
- [ ] `/decide` runs SIP on custom basket and shows **XIRR** + path.  
- [ ] Benchmark SIP appears with **delta XIRR** when prices exist.  
- [ ] Sample/demo data cannot be mistaken for live (banner; strict optional).  
- [ ] Missing price symbols listed before or after run.  
- [ ] Weight gap table works when snapshot + basket present.  
- [ ] Pytest green including new portfolio/decision tests.  
- [ ] `docs/api.md` + PRODUCT current goal updated.  
- [ ] No Coin, no trading, no alternate price vendors introduced.

---

## 16. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Kite token daily expiry | Clear status + login URL; don’t block UI on auto-refresh fantasy |
| Upstox token + rate limits | Cache curated; sync only basket symbols; document daytime sync |
| Symbol mismatch NSE/BSE / ISIN | Prefer NSE; map via instruments; warn on ambiguity |
| Benchmark ETF corporate actions | Document limitation; use close series as-is |
| Dual “Holdings” confusion | Rename nav: Portfolio vs Theme holdings |
| Scope creep into Phase 3 full compare suite | Benchmark = single symbol only in v1 |
| Personal data in git | Gitignore + fixture-only tests |
| Long API sync timeouts | CLI fallback with copy-paste command in UI |

---

## 17. Future (explicitly after v1)

1. Coin MF display-only allocation.  
2. Multi-strategy compare, cost toggle (roadmap P3 remainder).  
3. Save/load named decision baskets in UI.  
4. Book performance over time (holdings history series).  
5. Corporate action adjustments.  
6. Hosted multi-device with encrypted token store (only if still personal and careful).

---

## 18. Open decisions (locked for implementers unless founder overrides)

| Topic | Decision for v1 |
|-------|-----------------|
| Primary backtest path | **SIP/XIRR** |
| Lump-sum NAV path | **Not** on Decision Lab primary CTA (use Theme demo / existing backtest if needed) |
| Benchmark default | `NIFTYBEES` via `DEFAULT_BENCHMARK_SYMBOL` |
| Snapshot storage | Latest curated parquet + raw dated JSON archive |
| Persist baskets | **Optional later**; v1 run from form state |
| Coin | **Out** |
| Default home | `/portfolio` |
| Strict mode default | **Off** (`STRICT_MARKET_DATA=0`); UI still warns on sample |

---

## 19. Acceptance checklist (QA script)

1. `make api` + `make web` with sample data only → Portfolio empty state OK; Decide run shows **demo** warning.  
2. Configure Kite → login → `POST /portfolio/refresh` → table non-empty.  
3. Pick 5 holdings → equal weight → SIP 10k day 1 last 3y → XIRR number renders.  
4. Benchmark on → delta shown.  
5. Remove prices for one symbol (or unknown ticker) → missing list / warning.  
6. `STRICT_MARKET_DATA=1` + sample → run rejected or clearly blocked.  
7. Weight gap shows non-zero deltas for underweight names.  
8. No secrets in network tab responses.

---

## 20. Summary for agents

**Backend:** Portfolio snapshot pipeline + APIs; Decision orchestration over existing SIP + benchmark + DQ + weight gap.  
**Frontend:** `/portfolio` + `/decide` as primary product; honest banners; reuse SIP Lab visuals where possible.  
**Do not:** Coin, trading, multi-vendor data, gold-plate themes dashboard.

---

*End of PRD — Portfolio Decision v1*
