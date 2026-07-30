# PRODUCT.md — SIP Lab / Basket Backtest Engine

**Product name:** Backtest Hero (SIP Lab + Portfolio Decision)  
**Repo / package history:** `smallcase-finance` v0 → SIP Lab → Portfolio Decision v1  
**Status:** v0 + SIP Lab P1–2 **shipped**; **Portfolio Decision v1 shipped** (Kite book + Decision Lab); Coin still deferred  
**Binding decisions:** [ADR 004](docs/decisions/004-sip-lab-prd-decisions.md) · [ADR 005](docs/decisions/005-upstox-sole-market-data.md) · [ADR 007](docs/decisions/007-portfolio-decision-v1.md)  
**Phased plan:** [docs/ROADMAP.md](docs/ROADMAP.md)  
**PRD:** [docs/product/prd-portfolio-decision-v1.md](docs/product/prd-portfolio-decision-v1.md)  
**Ship writeup:** [docs/build-report-portfolio-decision-v1.md](docs/build-report-portfolio-decision-v1.md)  
**Upstox connect:** [docs/integrations/upstox.md](docs/integrations/upstox.md) §0 founder daily path

---

## Vision

Personal, local-first tool to measure **monthly SIP performance** of custom **stock/ETF baskets** (smallcase-style compositions the founder authors).

| Pillar | Meaning |
|--------|---------|
| **SIP-first** | Cash → units on schedule → market value → **XIRR** as the primary success metric |
| **Baskets** | Local smallcase definitions (JSON); weights / equal-weight; versioned constituents |
| **Reproducible** | One command path from prices → curated Parquet → calc → API/UI; fixtures gate correctness |
| **Real history** | Multi-year equity/ETF **OHLCV from Upstox only** (not alternate vendors) |
| **Honest demos** | Sample/synthetic prices allowed **without a token**, labeled demo — never as live market SIP |

**Not this product (yet / ever in this version):** live trading, F&O, multi-user social, paid multi-provider market-data sprawl, Coin/MF import engines.

---

## Current goal — Portfolio Decision v1 (shipped)

**Shipped:** Kite equity **portfolio of record** (`/portfolio`, `/portfolio/*` APIs), **Decision Lab** (`/decide`, `POST /decisions/run`) = candidate SIP + benchmark SIP + DQ + weight gap; reuses SIP engine. Writeup: [build-report-portfolio-decision-v1.md](docs/build-report-portfolio-decision-v1.md).

**Also shipped earlier:** SIP engine + `/sip-lab`, theme demo dashboard, Upstox prices.

**Next:** deeper Phase 3 polish (multi-strategy compare, costs), Coin/MF display later.

Still true:

1. Strategy config (amount, fixed calendar day-of-month, start/end, allocation).
2. **SIP day rule:** fixed calendar day → **next trading day** if session missing.
3. Units ledger + contribution cashflows; terminal/exit cashflow for XIRR.
4. **XIRR primary**; golden fixtures within absolute tolerance **`1e-4`**.
5. **Zero costs** MVP (brokerage/STT/slippage optional later, behind config).
6. Prices for real runs: **Upstox API only** via existing `src/smallcase_finance/integrations/upstox/`.

**Do not** treat v0 weight-NAV rebalance/`POST /backtest` as SIP performance — use **`POST /backtests/sip`** only.

---

## Phases (summary)

Full detail, exit criteria, and ordering: **[docs/ROADMAP.md](docs/ROADMAP.md)**. Locked implementation order ([ADR 004](docs/decisions/004-sip-lab-prd-decisions.md)):

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Foundations: strategy config, Upstox-only provider, cache, secrets | **Shipped** (with v0 + SIP scaffolds) |
| **0 / v0** | smallcase-finance v0 — NAV/metrics demo, pipeline, API, UI | **Shipped** (see checklist below) |
| **1** | **Correct SIP engine** + XIRR fixtures + Upstox-only history path | **Shipped** — [build-report-sip-lab-ui.md](docs/build-report-sip-lab-ui.md) |
| **2** | SIP Lab **API + UI** (run config, cashflows, XIRR, demo labels, export) | **Shipped** — `/sip-lab`, `POST /backtests/sip` |
| **3** | Benchmark, compare, optional costs, DQ warnings, strict Upstox mode | **Next / active** |
| **4** | **Kite equity import** + live portfolio vs SIP backtest compare | Later — [kite-connect.md](docs/integrations/kite-connect.md) only |
| **5** | **Coin / mutual funds** (import + MF NAV) | **Last** — not this version |

Order of work: **SIP engine → UI → (now) hardening → Kite equity import → Coin last.**

---

## Binding product rules (ADR 004 / 005)

### Historical data — Upstox only

| Rule | Detail |
|------|--------|
| **Sole source** | Equity/ETF historical OHLCV for SIP Lab and basket backtests comes **only** from the **Upstox API**. |
| **Forbidden this version** | **No** yfinance, **No** NSE bhavcopy, **No** Fyers (or other) fallbacks in product code paths. |
| **Code** | Extend [`src/smallcase_finance/integrations/upstox/`](src/smallcase_finance/integrations/upstox/) against official contracts. |
| **Pipeline** | Sync → immutable dated raw drops → curated Parquet; app reads curated only. |
| **Missing bars** | Skip/warn — never invent prices from another vendor. |
| **Demos** | Sample/synthetic prices when no token; UI/API/logs must label **demo / sample**, not real SIP performance. |

Contract & auth: [docs/integrations/upstox.md](docs/integrations/upstox.md) · policy ADR: [005](docs/decisions/005-upstox-sole-market-data.md).

**Env (never commit; repo is public):**

| Env var | Role |
|---------|------|
| `UPSTOX_ACCESS_TOKEN` | Primary Bearer token for historical candles (portal-generated OK for MVP) |
| `UPSTOX_API_KEY` | API Key / `client_id` (OAuth / app id) |
| `UPSTOX_API_SECRET` | API Secret / `client_secret` (token exchange only) |
| `UPSTOX_REDIRECT_URI` | OAuth redirect (must match developer app) |

Access tokens expire ~**3:30 AM IST** the following day (per Upstox); re-generate or re-OAuth as needed. Prefer daytime syncs. See Upstox developer portal flow in [upstox.md](docs/integrations/upstox.md).

### SIP engine defaults

| Rule | Detail |
|------|--------|
| **Day rule** | Fixed calendar day-of-month → **next trading day** if non-session |
| **Costs** | **Zero** brokerage/STT/slippage/expense drag (MVP) |
| **Primary metric** | **XIRR** on contribution + terminal cashflows |
| **Fixture tolerance** | Absolute **`1e-4`** on golden XIRR tests |
| **Secondary metrics** | NAV path, CAGR, vol, max DD remain available; do not replace XIRR for SIP success |

### Where the founder’s money lives (product map)

| Venue | What it holds | Role in SIP Lab today |
|-------|----------------|------------------------|
| **Kite** | Live equities | Future Phase 4 import only — **no Kite backend this sprint**; **not** used for OHLCV |
| **Coin** | Live mutual funds | Deferred (after Kite equity); **not** for OHLCV |
| **This app** | Authored baskets + SIP backtests | Primary surface now (`/sip-lab`) |
| **Upstox** | — | **Historical prices only** (API) |

Kite does **not** provide a simple “copy access token from developer portal” like Upstox Generate; session tokens require a login/request_token flow when we implement import later.

### Deferred / out of band

| Item | Policy |
|------|--------|
| **Coin / MF** | **Deferred.** No Coin import APIs, MF holdings endpoints, or MF NAV engine this version. |
| **Kite** | Phase 4 roadmap only — equity book import + live-vs-SIP compare; **not** a price source; **no backend work until a dedicated Kite plan**. Spec: [kite-connect.md](docs/integrations/kite-connect.md). |
| **Hosting** | Local-first; free-tier hosting optional later; personal-use security (secrets in `.env`, no multi-tenant auth). |
| **Repo** | Remains **public**. Secrets only in env / gitignored `.env`. `.env.example` = empty placeholders. |

### Explicit non-goals (this version)

- Live trading, order placement, F&O  
- Paid multi-provider market-data sprawl  
- Multi-user / social product  
- Treating weight-NAV rebalance backtest as SIP performance  
- Presenting sample/synthetic prices as real SIP results  
- Coin / mutual-fund product surface  

---

## v0 shipped checklist (preserved)

Local-first end-to-end slice: sample/curated data → calc engine → FastAPI → Next.js dashboard.

**Status:** Definition of Done met (2026-07-28). Full writeup: [docs/build-report.md](docs/build-report.md).  
Track against [docs/architecture/v0-plan.md](docs/architecture/v0-plan.md).

### Definition of Done (status)

- [x] **Data model** locked (ADRs + [data dictionary](docs/data-dictionary.md))
- [x] **Sample data + pipeline** — empty raw OK: generate sample OHLCV + 2 smallcases → `data/curated/`; entrypoint `python -m smallcase_finance.pipeline` / `make pipeline`
- [x] **Calc engine + tests** — NAV, returns, CAGR, vol, max DD, Sharpe, attribution, rebalance in `src/smallcase_finance/calc/`; pytest in `tests/`
- [x] **API** — FastAPI read path over curated (+ on-the-fly metrics/backtest): health, smallcases, holdings, NAV, performance, metrics, attribution, `POST /backtest`
- [x] **UI** — Dashboard, holdings, performance/risk, smallcase switcher (`apps/web`, routes `/`, `/holdings`, `/performance`)
- [x] **Docs** — install+run README; data dictionary; pipeline; [how to add personal data](docs/data/how-to-add-data.md); metrics definitions; [build report](docs/build-report.md)
- [x] **Tests** — lightweight unit tests for core calc + API smoke
- [x] **Upstox price ingest (v0.1)** — CLI + env token + custom lookback (`--years` / `--from`/`--to`) + sample fallback; UI custom timeline + data-source banner

### Sample smallcases

| id | Notes |
|----|--------|
| `digital-india` | IT/digital basket; custom weights; v1→v2 on 2024-01-02 |
| `momentum-quality` | Equal-weight quality names |

### Stack (binding; reused by SIP Lab)

- Frontend: Next.js (App Router) + TypeScript + Tailwind + **Recharts**
- Backend: Python + FastAPI
- Data: Polars/Pandas + DuckDB + Parquet under `data/curated/`
- Layout: `data/raw`, `data/curated`, `src/`, `notebooks/`, `docs/`

### Data notes

Place raw files in `data/raw/`.  
Curated outputs go in `data/curated/`.  
Schema: [docs/data-dictionary.md](docs/data-dictionary.md).  
Personal onboarding: [docs/data/how-to-add-data.md](docs/data/how-to-add-data.md).  
If raw prices are empty / no Upstox token, the sample generator writes synthetic OHLCV (label `source=sample`) — **demo only**.

### Decisions closed in v0 (still true)

- Currency / market: **INR / Indian equities friendly**; generic tickers supported  
- Target surface: **minimal web UI** (not notebook-only), with notebooks for analysis  
- Storage: **Parquet + DuckDB**, not Postgres (ADR 001, 002)  
- Chart library: **Recharts** (`apps/web`)  
- Default risk-free rate for Sharpe: **0.0** annual (`DEFAULT_RF` env; set `0.06` for India-like cash yield)  
- Upstox as price source evolved: optional in ADR 003 → **sole** historical provider in **ADR 005** for SIP Lab  

### v0 out of scope (unchanged)

Production auth, multi-user, live trading, full broker integration, FX engine, full Brinson attribution, transaction costs.

---

## What reuses vs what is new

| Reuse from v0 | New for SIP Lab (Phases 1–2) |
|---------------|-----------------|
| Pipeline, curated Parquet, DuckDB reads | SIP schedule + next-session invest rule |
| Pure `calc/` patterns + tests layout | Units ledger + contribution cashflows + XIRR (≤ 1e-4 goldens) |
| FastAPI app shell + deps | `GET /strategies`, `POST /backtests/sip`, `SipService` |
| Next.js shell, theme, charts primitives | `/sip-lab` UI, export, data-source chip/banner |
| Upstox client + instruments + sync | Upstox-only policy (no vendor fallbacks); V3 daily preferred |
| Sample smallcases / basket JSON | Strategy schema + `config/strategies/*.yaml` |
| Weight-NAV / rebalance `POST /backtest` | Kept for composition analysis; **not** SIP performance |

---

## Compare (later — Phase 4)

**Idea:** live equity book vs SIP backtest of the same strategy.  
**Import path:** Kite Connect equity holdings (founder uses Kite for equities).  
**Not this workflow’s full implementation** — roadmap Phase 4 only; market data remains Upstox.  
See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/integrations/kite-connect.md](docs/integrations/kite-connect.md).

**Coin / MF:** planned after Kite; **do not** implement Coin APIs or MF NAV this version.

---

## Green path (reminder)

```bash
make demo    # install + pipeline + tests
make api     # :8000
make web     # :3000
```

Real multi-year prices: set Upstox env vars → `make sync-upstox` → `make api` + `make web` → open **/sip-lab**. Without a token, demo/sample path only (labeled — not live market SIP).

---

## Source-of-truth map

| Doc | Role |
|-----|------|
| **This file** | Product vision, binding rules, v0 checklist, phase index |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased delivery, exit criteria, sequencing |
| [ADR 004](docs/decisions/004-sip-lab-prd-decisions.md) | Founder-approved SIP Lab PRD decisions |
| [ADR 005](docs/decisions/005-upstox-sole-market-data.md) | Upstox sole historical market data |
| [docs/integrations/upstox.md](docs/integrations/upstox.md) | Auth, API contracts, sync operator notes |
| [docs/integrations/kite-connect.md](docs/integrations/kite-connect.md) | Phase 4 plan only (no runtime) |
| [docs/build-report.md](docs/build-report.md) | What v0 actually shipped |
| [docs/build-report-sip-lab-ui.md](docs/build-report-sip-lab-ui.md) | What SIP Lab Phases 1–2 shipped + how to run/read XIRR |
| [README.md](README.md) | Install and run |

Update this file when goals complete or priorities shift. Prefer ADRs + ROADMAP for detailed decisions and phase exits; keep PRODUCT as the short vision + status surface.
