# ROADMAP — SIP Lab / Basket Backtest Engine

**Product:** SIP Lab / Basket Backtest Engine (evolution of smallcase-finance v0)  
**Vision:** Monthly SIP performance of custom stock/ETF baskets; **XIRR** primary; local and reproducible  
**Status:** Binding phases for this product version  
**Related:** [ADR 004](./decisions/004-sip-lab-prd-decisions.md), [ADR 005](./decisions/005-upstox-sole-market-data.md), [PRD](./product/prd-sip-lab.md), [Backlog P0–P2](./product/backlog-phase-0-2.md)

---

## Principles (locked)

| Principle | Rule |
|-----------|------|
| **Order of work** | Correct SIP engine → UI → Kite equity import → Coin last |
| **Historical data** | **Upstox API only** for equity/ETF OHLCV — no yfinance, bhavcopy, Fyers |
| **SIP day** | Fixed calendar day of month → **next trading day** if non-session |
| **Costs** | Zero costs MVP; optional toggle later (P3) |
| **Primary metric** | XIRR; golden fixtures tolerance **≤ 1e-4** |
| **Secrets** | Env only; public repo never gets tokens |
| **Coin / MF** | Not this version; after Phase 4 equity path |
| **Non-goals** | Live trading, F&O, multi-user social, paid multi-provider sprawl |

**Reuse v0:** FastAPI, Next.js shell, pipeline, `calc/` modules, Upstox client, sample smallcases.  
**Do not** treat weight-NAV rebalance backtest as SIP performance — dedicated SIP path.

---

## Phase 0 — Foundations (config, market data contract, cache, secrets)

**Goal:** Lock strategy/SIP configuration shapes, make Upstox the sole `MarketDataProvider` implementation, harden Parquet/raw cache, and document secrets/auth so later phases have a single honest data path.

### Work packages

| ID | Work package | Agent owner(s) | Notes |
|----|--------------|----------------|-------|
| **P0-WP1** | Strategy / SIP config schema (amount, day-of-month, start/end, basket id or constituents, allocation mode, currency INR) | `data-architect`, `backend` | Local JSON or Pydantic; version field; documented in data dictionary |
| **P0-WP2** | `MarketDataProvider` interface + **sole** Upstox impl; ban alternate vendors in code | `backend`, `data-engineer` | Extend `integrations/upstox/`; sample = demo-only, labeled |
| **P0-WP3** | Raw dated drops + curated Parquet cache path; instrument_key map for basket symbols | `data-engineer` | Immutable raw; pipeline → `data/curated/prices` |
| **P0-WP4** | Secrets / env contract + `.env.example` placeholders; auth runbook (portal token) | `backend` | `UPSTOX_ACCESS_TOKEN`, `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`; never commit secrets |
| **P0-WP5** | Data-source labeling (API + docs): sample vs Upstox; fail-soft warnings on missing keys | `backend`, `data-engineer` | Align ADR 005 |

### Acceptance criteria

- [ ] SIP strategy config can be loaded from a local file (or equivalent) with validated required fields.
- [ ] No product code path fetches historical OHLCV from any source other than Upstox (or labeled sample for demos).
- [ ] `UPSTOX_*` env vars documented; empty `.env.example`; README / [upstox.md](./integrations/upstox.md) match portal auth flow.
- [ ] Sync writes dated raw drop; pipeline refreshes curated Parquet; re-run is reproducible for same token window + range.
- [ ] Missing `instrument_key` / candles → explicit skip or warning, never silent third-party fill.
- [ ] ADRs 004/005 remain the policy source of truth; no conflicting “multi-provider” wording left in active product docs.

### Exit gate

Founder can set a portal access token, sync a basket’s symbols via Upstox, and see curated prices tagged as Upstox (or clearly labeled sample without token).

---

## Phase 1 — SIP engine + XIRR golden tests (equity/ETF only)

**Goal:** Correct monthly SIP simulation: cash → units → market value → cashflow series → **XIRR**, with CI golden fixtures.

### Work packages

| ID | Work package | Agent owner(s) | Notes |
|----|--------------|----------------|-------|
| **P1-WP1** | SIP calendar: fixed day-of-month → next trading day from price calendar | `backend`, `data-analyst` | Session = day with available bar for buy universe (or documented rule) |
| **P1-WP2** | Units ledger: allocate SIP amount by weights/mode; buy at documented price field (e.g. close); fractional units MVP OK unless later locked | `backend` | Zero costs default |
| **P1-WP3** | Cashflow series builder (contributions negative, terminal/exit positive) + XIRR | `data-analyst`, `backend` | Primary metric |
| **P1-WP4** | Golden fixtures (hand-checked or reference solver) tolerance **1e-4**; equity/ETF only | `data-analyst` | No MF/Coin paths |
| **P1-WP5** | Service layer entrypoint (pure-ish) for one SIP run given strategy + prices | `backend` | Distinct from v0 rebalance NAV path |

### Acceptance criteria

- [ ] Given a fixed fixture basket + price path, SIP contribution dates match calendar rule (incl. weekend/holiday → next session).
- [ ] Units and residual cash (if any) are deterministic and documented.
- [ ] XIRR on fixture cashflows matches reference within **≤ 1e-4**.
- [ ] Pytest suite fails if engine regresses XIRR or SIP day logic.
- [ ] No Coin/MF code; no Kite holdings import; costs remain zero.
- [ ] Sample prices may power demo fixtures only if labeled as synthetic; market-fidelity claims require Upstox-sourced fixtures or docs that say “synthetic”.

### Exit gate

`pytest` green on SIP + XIRR golden tests; one CLI or service call runs a full equity/ETF basket SIP over multi-year curated prices.

---

## Phase 2 — API + Next.js SIP UI + export

**Goal:** Expose SIP runs over FastAPI and a focused SIP Lab UI; export results for offline review.

### Work packages

| ID | Work package | Agent owner(s) | Notes |
|----|--------------|----------------|-------|
| **P2-WP1** | API: create/run SIP backtest, return XIRR, cashflows, units path, summary metrics; data-source flag | `backend` | Reuse FastAPI patterns; schemas in `schemas/` |
| **P2-WP2** | SIP Lab UI: strategy picker / form, date range, run, KPIs (XIRR primary), equity curve / contribution chart | `design`, `frontend` | Dark-mode friendly; reuse AppShell |
| **P2-WP3** | Export: CSV/JSON of cashflows + summary (and optional holdings path) | `backend`, `frontend` | Local download |
| **P2-WP4** | Wire data-source banner for sample vs Upstox on SIP results | `frontend` | No silent “real” label on sample |
| **P2-WP5** | API docs + minimal UX copy (SIP day rule, zero costs) | `backend`, `design` | Link metrics definitions |

### Acceptance criteria

- [ ] `POST` (or equivalent) SIP run returns XIRR + series consistent with Phase 1 engine.
- [ ] UI can select a basket/strategy, run SIP, show primary XIRR and supporting charts/tables.
- [ ] Export produces a file that matches on-screen cashflows/summary within rounding.
- [ ] Sample vs live source is visible in UI and API payload.
- [ ] No Kite/Coin features surface in this phase.

### Exit gate

Founder runs SIP Lab in browser against local API on real Upstox-curated data (or labeled sample) and downloads export.

---

## Phase 3 — Benchmark, compare, costs, data-quality warnings

**Goal:** Relative performance vs Upstox-sourced benchmark, multi-strategy compare, optional cost model, and explicit DQ warnings.

### Work packages

| ID | Work package | Agent owner(s) | Notes |
|----|--------------|----------------|-------|
| **P3-WP1** | Benchmark series via **Upstox only** (index ETF or chosen symbol); SIP-into-benchmark compare | `data-engineer`, `backend`, `data-analyst` | Same provider rules as baskets |
| **P3-WP2** | Strategy vs strategy compare (side-by-side XIRR, drawdown, contribution) | `backend`, `frontend`, `data-analyst` | |
| **P3-WP3** | Cost model toggle (brokerage/slippage simplified); default remains **zero**; fixtures versioned if costs on | `backend`, `data-analyst` | Must not break zero-cost goldens |
| **P3-WP4** | Data-quality warnings: missing bars, partial basket, short history, stale token / sample mode | `data-engineer`, `frontend` | Surfaced in API + UI |
| **P3-WP5** | Optional strict mode: refuse “real” SIP report without Upstox | `backend` | Config flag |

### Acceptance criteria

- [ ] Benchmark prices come only from Upstox path (or labeled sample demo).
- [ ] User can compare at least two strategies (or strategy vs benchmark) on XIRR and key risk metrics.
- [ ] Cost toggle off reproduces Phase 1 golden results; cost on is documented and optional.
- [ ] Partial data / sample mode produces visible DQ warnings, not silent success.
- [ ] Still no live trading, Coin/MF, or Kite import.

### Exit gate

Founder can judge basket SIP vs a benchmark and vs another strategy with clear DQ state and optional simple costs.

---

## Phase 4 — Kite equity holdings import + portfolio vs strategy

**Goal:** Read-only import of founder’s **equity** book from Kite; compare live portfolio vs SIP backtest of strategy. **Coin / MF still later** (not in this phase).

### Work packages

| ID | Work package | Agent owner(s) | Notes |
|----|--------------|----------------|-------|
| **P4-WP1** | ADR + thin Kite client (holdings only); env secrets; public-repo safe | `backend` | Spec: [kite-connect.md](./integrations/kite-connect.md) |
| **P4-WP2** | Raw holdings drop → curated `holdings_snapshots` | `data-engineer` | Equity only; no F&O product path |
| **P4-WP3** | Map Kite symbols → local instrument / basket keys | `data-architect`, `backend` | |
| **P4-WP4** | Compare API + UI: actual equity book vs SIP backtest of strategy | `backend`, `frontend`, `data-analyst` | Prices for backtest remain **Upstox** |
| **P4-WP5** | Explicit deferral of Coin / MF (docs + no endpoints) | PO | Coin last, separate phase if ever |

### Acceptance criteria

- [ ] Equity holdings import works with founder Kite app credentials via env.
- [ ] Compare view shows portfolio vs strategy SIP backtest without using Kite as OHLCV source.
- [ ] No order placement; no Coin/MF import or MF NAV engine.
- [ ] Secrets never committed; docs list `KITE_*` env placeholders only when wired.

### Exit gate

Founder imports equity holdings and sees a clear “actual vs strategy SIP” comparison. Coin remains out of scope.

---

## After Phase 4 (explicitly not scheduled here)

- Coin / mutual fund holdings import and MF NAV engine  
- Full OAuth UX for Upstox/Kite beyond CLI-first  
- Free-tier hosting, multi-user, social  
- Live trading, F&O, multi-broker market data  

---

## Agent ownership map (summary)

| Agent | Typical ownership on this roadmap |
|-------|-----------------------------------|
| **PO** (main session) | Scope, prioritization, ADR acceptance, phase exit |
| **data-architect** | Strategy schema, holdings snapshots model, symbol maps |
| **data-engineer** | Upstox sync, Parquet cache, pipeline, DQ, Kite raw drops |
| **backend** | Provider interface, SIP service, FastAPI, costs, Kite client |
| **data-analyst** | XIRR fixtures, metrics narrative, compare analytics |
| **design** | SIP Lab layout, export UX, compare screens |
| **frontend** | Next.js SIP Lab, charts, banners, export download |

---

## Suggested sequencing checklist

```
P0 foundations ──► P1 SIP engine + goldens ──► P2 API/UI/export
                                              ──► P3 bench/compare/costs/DQ
                                              ──► P4 Kite equity vs strategy
                                              ──► (later) Coin/MF
```

Prefer small diffs; start non-trivial work in Plan Mode; document architecture choices under `docs/decisions/`.
