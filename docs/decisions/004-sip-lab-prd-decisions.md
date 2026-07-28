# ADR 004 — SIP Lab / Basket Backtest Engine: founder-approved PRD decisions

**Status:** Accepted (binding for SIP Lab)  
**Date:** 2026-07-28  
**Owner:** Product Owner  
**Related:** [ADR 005 — Upstox sole market data](./005-upstox-sole-market-data.md), [Upstox integration](../integrations/upstox.md), [Kite Phase 4 plan](../integrations/kite-connect.md), [ADR 003 — Upstox optional (superseded for sole-source policy)](./003-upstox-price-source.md)

---

## Context

The product is evolving from **smallcase-finance v0** (weight-based NAV / rebalance demo) to **SIP Lab / Basket Backtest Engine**: monthly SIP performance of custom stock/ETF baskets, with **XIRR as the primary metric**, local reproducibility, and Upstox-sourced equity/ETF history.

v0 already has FastAPI, Next.js shell, pipeline → curated Parquet, pure `calc/`, sample smallcases, and an Upstox client. SIP Lab needs different engine semantics (cash → units → market value → cashflow XIRR) and a locked set of product rules so implementers do not reuse the wrong model or re-open deferred scope.

This ADR records **founder-approved decisions** that bind design and implementation for this product version.

---

## Decision

### 1) Historical prices: Upstox only

| Rule | Detail |
|------|--------|
| **Sole source** | Equity/ETF historical **OHLCV** for SIP Lab and basket backtests comes **only** from the **Upstox API**. |
| **Forbidden this version** | **No** yfinance, **no** NSE bhavcopy, **no** Fyers (or other) fallbacks in product code paths. |
| **Demos without token** | Sample / synthetic prices may run demos only; they must not be presented as live market performance. See [ADR 005](./005-upstox-sole-market-data.md). |

Rationale: one contract, one cache path, multi-year reproducibility under founder-controlled credentials. Multi-provider sprawl is a non-goal.

### 2) SIP day rule: fixed calendar day → next trading day

| Rule | Detail |
|------|--------|
| **Schedule** | SIP contributions fire on a **fixed calendar day of month** (strategy config). |
| **Non-trading days** | If that calendar day is not a trading session (weekend / holiday / missing session in the price calendar), invest on the **next trading day** with available prices. |
| **Not used for SIP** | Approximate rebalance steps (e.g. every ~21/63 calendar days) are **not** the SIP contribution rule. |

Rationale: matches how retail SIPs are commonly scheduled; aligns cashflow dates with actual sessions for unit purchases.

### 3) Costs: zero default MVP; optional later

| Rule | Detail |
|------|--------|
| **MVP default** | **Zero** brokerage, STT, stamp, slippage, and expense drag. Buy at session close (or documented price field) with full SIP amount → units. |
| **Later** | Optional cost models may be added behind config; they must not change the zero-cost golden fixtures unless fixtures are explicitly versioned. |

Rationale: correctness of cash → units → XIRR first; friction models second.

### 4) Coin / mutual funds: deferred

| Rule | Detail |
|------|--------|
| **This version** | **No** Coin import APIs, **no** MF holdings endpoints, **no** MF NAV engine. |
| **Scope** | Equities/ETFs on Upstox history + local basket definitions only. |

Rationale: founder equities-first; Coin is last on the ordered roadmap.

### 5) Hosting: local-first; free-tier later

| Rule | Detail |
|------|--------|
| **Default** | Run on the founder’s machine: local API, local UI, local `data/` (raw + curated). |
| **Later** | Optional free-tier hosting is out of band for engine correctness; no multi-tenant production assumption. |

Rationale: personal side project; reproducibility over cloud ops.

### 6) XIRR tolerance: ≤ 1e-4 on golden fixtures

| Rule | Detail |
|------|--------|
| **Primary metric** | SIP performance is judged primarily by **XIRR** on the contribution + terminal (or exit) cashflow series. |
| **Fixture gate** | Golden tests must agree with reference XIRR within absolute tolerance **`1e-4`** (i.e. ≤ 0.0001 on the decimal rate, or documented equivalent on the fixture’s unit). |
| **Secondary metrics** | NAV path, CAGR, vol, drawdown remain available but must not replace XIRR as the SIP success criterion. |

Rationale: unit/cashflow engines are easy to get “almost right”; hard fixtures prevent silent regression.

### 7) Repo stays public; secrets via env only

| Rule | Detail |
|------|--------|
| **Visibility** | Repository remains **public**. |
| **Secrets** | Upstox (and any future broker) credentials live in **env** / gitignored `.env` only. Never commit tokens, secrets, or filled env files. |
| **Env names (Upstox)** | `UPSTOX_ACCESS_TOKEN`, `UPSTOX_API_KEY`, `UPSTOX_API_SECRET` (and any official names documented in [upstox.md](../integrations/upstox.md)). |

Rationale: public code + private credentials; accidental secret commit is a first-class risk.

### 8) Kite equity import: Phase 4 roadmap only

| Rule | Detail |
|------|--------|
| **This version** | **No** Kite Connect runtime integration for holdings import or live-vs-SIP compare. |
| **Roadmap** | Phase 4: import equity book from Kite; compare live portfolio vs SIP backtest of strategy. Spec only: [kite-connect.md](../integrations/kite-connect.md). |
| **Market data** | Kite is **not** a price source for this product version (Upstox remains sole OHLCV provider). |

Rationale: order of work is SIP engine → UI → Kite equity import → Coin last.

---

## Implementation order (locked)

1. **Correct SIP engine** (strategy config, calendar day → next session, units ledger, cashflows, XIRR + fixtures).  
2. **UI** (SIP Lab surface).  
3. **Kite equity import / live-vs-SIP compare** (Phase 4).  
4. **Coin / MF** (later).

---

## Explicit non-goals (this version)

- Live trading, order placement, F&O  
- Paid multi-provider market-data sprawl  
- Multi-user / social product  
- Treating weight-NAV rebalance backtest as SIP performance  
- Presenting sample/synthetic prices as real SIP results  

---

## Consequences

- **Positive:** Clear gates for agents and PRs; XIRR fixtures become CI truth; Upstox auth/cache path is the only live history path.  
- **Negative:** Without a valid Upstox token (and instrument coverage), real multi-year SIP claims are blocked; demos must stay labeled sample.  
- **Supersession:** ADR 003’s “optional live price source among others” posture is **tightened** by [ADR 005](./005-upstox-sole-market-data.md): Upstox is the **sole** production historical provider; sample data is demo-only, not an alternate vendor.  
- **Risk to avoid:** Reusing v0 rebalance/NAV paths for SIP cashflows will produce wrong XIRR and contribution semantics — build a dedicated SIP path in `calc/` + services.

---

## Follow-ups (not decided here)

- Exact SIP strategy schema fields (amount, day-of-month, start/end, allocation mode).  
- Fractional shares vs rupee-residual cash handling.  
- Holiday calendar source (pure price-calendar “next available session” is enough for MVP if Upstox daily bars define sessions).  
- API shape for `POST` SIP run (cashflows, XIRR, units path).  
- UI layout for SIP Lab (after engine fixtures pass).
