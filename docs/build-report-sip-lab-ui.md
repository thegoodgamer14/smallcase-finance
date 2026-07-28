# Build Report — SIP Lab Engine + UI (Phases 1–2)

**Date:** 2026-07-28  
**Status:** Phase 1 (SIP engine + XIRR goldens) and Phase 2 (API + SIP Lab UI + export) **shipped**  
**Audience:** Founder / next session  
**Policy:** [ADR 004](./decisions/004-sip-lab-prd-decisions.md) · [ADR 005](./decisions/005-upstox-sole-market-data.md)  
**Architecture:** [sip-engine.md](./architecture/sip-engine.md) · XIRR: [sip-xirr.md](./analytics/sip-xirr.md)  
**v0 baseline (still shippable, not SIP):** [build-report.md](./build-report.md)

This report only claims what exists in the repo and what verification confirmed. It does **not** claim Phase 3 (benchmarks/costs/strict mode) or Phase 4 (Kite).

---

## 1) What shipped

### Phase 1 — Correct SIP engine + XIRR

Monthly **cash → units → market value → cashflow XIRR** path, distinct from v0 weight-NAV.

| Layer | Location | Role |
|-------|----------|------|
| SIP schedule | `src/smallcase_finance/calc/sip_schedule.py` | Fixed calendar day-of-month → **next trading day** from price session calendar |
| Units / MV sim | `src/smallcase_finance/calc/sip_sim.py` | Allocate SIP amount by weights; buy at **close**; fractional units; MV path |
| XIRR | `src/smallcase_finance/calc/xirr.py` | ACT/365.25; Newton then Brent; golden abs tol **≤ 1e-4** |
| Service | `src/smallcase_finance/services/sip_service.py` | Strategy + curated prices → cashflows, series, XIRR, secondary metrics |
| Strategy load | `src/smallcase_finance/strategies/` + `services/strategy_service.py` | File-backed YAML/JSON under `config/strategies/` |
| Schemas | `src/smallcase_finance/schemas/sip.py` | Request/response DTOs; `data_source` required for honesty |
| Example strategy | `config/strategies/example-sip-equity.yaml` | Inline 4-name equity basket; ₹5,000 on day 5 |
| Engine docs | `docs/architecture/sip-engine.md`, `docs/analytics/sip-xirr.md`, `docs/data-dictionary-sip.md` | Semantics, non-goals, cashflow signs |

**Engine rules (MVP, binding):**

- SIP day: fixed calendar day **1–28** → next session with prices if closed/missing  
- Costs: **zero** (full amount deploys at session close)  
- Primary metric: **XIRR** on contribution outflows + terminal MV inflow  
- Secondary: total invested, final value, absolute gain, max drawdown on MV path, SIP count  
- Prices: curated Parquet only (`data/curated/prices/`) — Upstox history or labeled sample  
- **Not SIP:** `POST /backtest` weight-NAV rebalance remains for composition demos only  

### Phase 2 — API + Next.js SIP Lab + export

| Surface | Location | Role |
|---------|----------|------|
| `GET /strategies` | `api/routes/strategies.py` | List file-backed strategies |
| `GET /strategies/{id}` | same | Full validated config |
| `POST /backtests/sip` | `api/routes/sip_backtest.py` | Run SIP; returns XIRR, cashflows, series, `data_source` |
| API cookbook | `docs/api.md` § SIP Lab | Curl examples, day rule, zero costs |
| SIP Lab page | `apps/web/src/app/sip-lab/page.tsx` | Configure → run → XIRR-primary results |
| SIP components | `apps/web/src/components/sip/` | Chip/banner, methodology, how-to-read, tables, export, dash callout |
| Client API | `apps/web/src/lib/api.ts` | `listStrategies`, `getStrategy`, `postSipBacktest` (**not** v0 `/backtest`) |
| Nav | `AppShell.tsx` | **SIP Lab** in desktop + mobile nav |
| Dashboard entry | `SipDashCallout` on `/` | Links to `/sip-lab`; explains index vs SIP |

**UI behavior (shipped):**

- Strategy picker (from API), amount, day-of-month, start/end (or “to latest”)  
- **XIRR** as hero KPI; invested / final value / absolute gain; max drawdown; SIP count  
- Portfolio value + cumulative invested chart; drawdown chart  
- Cashflow table (signed) + by-holding contribution tab  
- Export: full results **JSON** + cashflow **CSV** (client-side download)  
- **Data-source chip + banner** (demo/sample vs Upstox)  
- Methodology panel + “How to read these results”  
- Empty / loading / error states (API down, 400/404/503 mapped to plain language)  
- Assumptions footer after a successful run  

### Tests (SIP-related + suite)

| File | Coverage |
|------|----------|
| `tests/test_sip_xirr.py` | Schedule, simulation, XIRR goldens (independent reference solver; abs ≤ 1e-4) |
| `tests/test_sip_service.py` | Service entrypoint over fixtures / curated |
| `tests/test_sip_api.py` | Strategies list/detail; `POST /backtests/sip` happy + validation; no secrets in payloads |
| `tests/test_strategy_config.py` | Strategy load/validate |
| Full suite | **`pytest` — 125 passed** (verification) |

---

## 2) How to run

**Requirements:** Python ≥ 3.11, Node.js 18+, Make optional.

### Green path (demo / sample prices)

```bash
# from repo root
make demo          # install → pipeline → tests
# or step-by-step:
make install
make pipeline      # raw → data/curated/*.parquet (sample if no Upstox token)
make test          # expect green (125+ tests)
```

Two terminals:

```bash
make api           # FastAPI  → http://127.0.0.1:8000  (OpenAPI: /docs)
make web           # Next.js  → http://localhost:3000
```

Open **SIP Lab:**

```text
http://localhost:3000/sip-lab
```

Also reachable from AppShell **SIP Lab** nav and the Dashboard callout → Open SIP Lab.

### Smoke API without the UI

```bash
curl -s http://127.0.0.1:8000/strategies | jq '.items[].id'
curl -s -X POST http://127.0.0.1:8000/backtests/sip \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy_id": "example-sip-equity",
    "amount": 10000,
    "day_of_month": 5,
    "start": "2023-01-01",
    "end": "2023-12-31"
  }' | jq '{strategy_id, xirr, total_invested, final_value, data_source, n_sips, warnings}'
```

Without Upstox credentials, expect `data_source` of **`sample`** (or similar demo label) and a warning that results are not live market claims.

### Real multi-year prices (Upstox only)

```bash
cp .env.example .env
# set UPSTOX_ACCESS_TOKEN (and optional API key/secret for OAuth) — never commit .env

make sync-upstox              # or YEARS=5 / FROM=… TO=…
make api
make web
# open /sip-lab and re-run; data_source should reflect upstox when curated bars are Upstox-sourced
```

| Policy | Detail |
|--------|--------|
| Sole live OHLCV | **Upstox API** only (ADR 005) |
| Forbidden | yfinance, NSE bhavcopy, Fyers in product code paths |
| Without token | Sample/synthetic path — **demo only** |

---

## 3) How to read XIRR

Full methodology: [docs/analytics/sip-xirr.md](./analytics/sip-xirr.md).

### What XIRR answers

> If I had put this fixed amount into the basket every month on my SIP day (next session if closed), what **annualized return** did that cashflow path earn, given ending portfolio value?

It is **not** the same as the Dashboard’s weight-NAV / index-style return (`POST /backtest` / NAV series).

### Cashflow convention (binding)

| Event | Sign in cashflow table | Meaning |
|-------|------------------------|---------|
| Monthly SIP | **Negative** (−) | Cash you put in |
| Terminal / exit | **Positive** (+) | Market value of units at end (as if you exited) |

XIRR solves for rate \(r\) such that NPV of all cashflows is zero (day-count **ACT/365.25**).

### Reading the SIP Lab UI

1. **Start with XIRR** — annualized return on every contribution + ending value.  
2. **Total invested** — sum of SIPs (cash out). **Final value** — what units are worth. **Absolute gain** = final − invested (rupees, not annualized).  
3. **Portfolio value chart** — MV of units over time; dashed line = cumulative cash invested.  
4. **Cashflow table** — the exact legs XIRR uses (export CSV matches signs).  
5. **Max drawdown** — worst peak-to-trough on **market value** (path risk), not a substitute for XIRR.  
6. **Do not mix** SIP Lab XIRR with Dashboard index metrics.

If XIRR shows “—” / null: fewer than two usable cashflows or solver non-convergence (see `xirr_status` / API message).

Golden gate in tests: \(|r_{\mathrm{engine}} - r_{\mathrm{ref}}| \le 10^{-4}\).

---

## 4) Demo vs Upstox

| Mode | When | `data_source` (typical) | May claim real SIP performance? |
|------|------|-------------------------|----------------------------------|
| **Demo / sample** | No token, or curated bars from sample generator / `*_sample` drops | `sample`, `fixture`, sometimes `mixed` / `unknown` | **No** |
| **Upstox** | Token + `make sync-upstox` → curated prices tagged Upstox | `upstox` | Yes, with product caveats (zero costs, etc.) |

**UI honesty (shipped):**

- Pre-run strip: demo warning if Upstox not configured; “real history available” if configured  
- Post-run **DataSourceChip** + **SipDataSourceBanner** from API `data_source`  
- Methodology / footer: zero costs, SIP day rule, XIRR primary  
- Warnings list from API when present  

**API:** response always includes `data_source` and `assumptions` (costs zero, day rule, not v0 rebalance). Secrets never returned.

---

## 5) Limitations (honest)

| Limitation | Status |
|------------|--------|
| Zero transaction costs (no brokerage/STT/slippage) | By design MVP; optional costs = **Phase 3** |
| Equity/ETF baskets only | No Coin / mutual funds this version |
| No benchmark SIP compare | Phase 3 |
| No strategy-vs-strategy compare UI | Phase 3 |
| No strict “refuse real report without Upstox” mode | Phase 3 |
| No Kite equity import / live book vs SIP | Phase 4 |
| Session calendar = price calendar | No separate exchange holiday API |
| Fractional units | MVP true; residual cash ≈ 0 |
| Rebalance modes beyond `none` | Config field exists; heavy rebalance SIP paths not Phase 1–2 focus |
| Web needs local (or reachable) API | Default `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` |
| Sample prices are synthetic | Multi-year GBM-style sample is **not** market fidelity |

---

## 6) Verification notes

Checks recorded for this build (all **passed**; none failed):

| Check | Result |
|-------|--------|
| XIRR golden fixtures | passed |
| SIP service tests | passed |
| Strategies API | passed |
| `POST /backtests/sip` | passed |
| No secrets leak in API payloads | passed |
| Full pytest suite | **125 passed** |
| v0 `POST /backtest` is **not** SIP | confirmed (docs + separate route) |
| No yfinance / bhavcopy / Fyers product paths | confirmed (policy in code comments / market_data) |
| `npm run build` in `apps/web` | succeeds |
| `/sip-lab` page exists (statically generated in Next build) | yes |
| AppShell nav includes SIP Lab (desktop + mobile) | yes |
| Dashboard `SipDashCallout` → `/sip-lab` | yes |
| SIP component and API imports resolve | yes |
| XIRR-primary UI, methodology panel, data-source chip, empty/error/loading | present |

### Quick re-verify

```bash
make pipeline && make test
cd apps/web && npm run build
# then make api + make web; open /sip-lab; run example-sip-equity
```

---

## 7) Key paths (map)

```
config/strategies/example-sip-equity.yaml
src/smallcase_finance/calc/{sip_schedule,sip_sim,xirr}.py
src/smallcase_finance/services/sip_service.py
src/smallcase_finance/api/routes/{strategies,sip_backtest}.py
apps/web/src/app/sip-lab/page.tsx
apps/web/src/components/sip/*
tests/test_sip_{xirr,service,api}.py
docs/api.md  (SIP Lab section)
docs/architecture/sip-engine.md
docs/analytics/sip-xirr.md
```

---

## 8) What next (not claimed shipped)

Per [ROADMAP.md](./ROADMAP.md):

1. **Phase 3** — Benchmark via Upstox, multi-strategy compare, optional costs, richer DQ warnings, optional strict Upstox mode  
2. **Phase 4** — Kite equity holdings import + live book vs SIP backtest (prices still Upstox)  
3. **Coin / MF** — last; not this version  

---

## Source-of-truth map

| Doc | Role |
|-----|------|
| [PRODUCT.md](../PRODUCT.md) | Vision + phase status |
| [ROADMAP.md](./ROADMAP.md) | Exit criteria + sequencing |
| This file | What Phases 1–2 actually shipped + how to run/read |
| [build-report.md](./build-report.md) | v0 NAV demo only |
| [build-report-sip-lab-plan.md](./build-report-sip-lab-plan.md) | Earlier planning synthesis (pre-ship) |
