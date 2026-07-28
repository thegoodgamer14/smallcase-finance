# PRD — SIP Lab / Basket Backtest Engine (condensed)

**Version:** 1.0 (SIP Lab)  
**Date:** 2026-07-28  
**Status:** Binding product summary  
**Full decisions:** [ADR 004](../decisions/004-sip-lab-prd-decisions.md), [ADR 005](../decisions/005-upstox-sole-market-data.md)  
**Roadmap:** [docs/ROADMAP.md](../ROADMAP.md)  
**Near-term backlog:** [backlog-phase-0-2.md](./backlog-phase-0-2.md)

---

## 1. Problem

The founder authors Smallcase-style equity/ETF baskets and wants to know: *“If I had SIP’d a fixed amount into this basket every month, what would XIRR and path look like?”*  

v0 ships weight-based NAV / rebalance demos. That is **not** the same as monthly cash contributions → units → cashflow XIRR. SIP Lab is the dedicated engine and UI for that question.

---

## 2. Vision

**SIP Lab / Basket Backtest Engine:** monthly SIP performance of custom stock/ETF baskets, with **XIRR as the primary metric**, local reproducibility, and **Upstox** as the sole historical OHLCV source for equities/ETFs.

---

## 3. Users & context

| Role | Need |
|------|------|
| **Founder (sole user)** | Define baskets, run SIPs, trust numbers, export, later compare to live equity book |
| **Market** | India equities/ETFs (INR); not multi-user SaaS |

**Founder facts:** Equities on Kite; Coin MF deferred; authors smallcase baskets; repo stays **public**.

---

## 4. Goals

1. Correct, testable **SIP engine** (calendar day → next trading day; units ledger; XIRR).  
2. **Reproducible** runs over cached Upstox history (raw drops + curated Parquet).  
3. **SIP Lab UI** + API + export after engine correctness.  
4. Later: benchmark, multi-strategy compare, optional costs, DQ warnings.  
5. Later: **Kite equity** import and portfolio vs strategy SIP compare.  
6. Coin / MF only after equity path — **not** this version’s implementation.

---

## 5. Non-goals (this version)

- Live trading, order placement, F&O  
- Coin import APIs, MF holdings endpoints, MF NAV engine  
- yfinance / bhavcopy / Fyers / multi-provider market data  
- Multi-user, social, paid product packaging  
- Treating v0 rebalance NAV as SIP performance  
- Presenting sample/synthetic prices as real market SIP results  

---

## 6. Product rules (binding)

| Area | Rule |
|------|------|
| **History** | Upstox API **only** for equity/ETF OHLCV |
| **SIP day** | Fixed calendar day of month; if non-trading → **next trading day** |
| **Costs** | **Zero** brokerage/STT/slippage MVP |
| **Primary metric** | **XIRR**; golden fixture tolerance **≤ 1e-4** |
| **Secrets** | `UPSTOX_ACCESS_TOKEN`, `UPSTOX_API_KEY`, `UPSTOX_API_SECRET` (env only) |
| **Demo without token** | Sample prices allowed **with labels** — not alternate vendor |
| **Basket defs** | Local JSON / strategy config (not Smallcase.com scrape) |
| **Kite** | Phase 4 equity holdings only; **not** a price source |
| **Order of work** | Engine → UI → Kite equity compare → Coin last |

---

## 7. Scope by phase (summary)

| Phase | Outcome |
|-------|---------|
| **P0** | Strategy/SIP config; Upstox as sole `MarketDataProvider`; Parquet cache; secrets/docs |
| **P1** | SIP engine + XIRR golden tests (equity/ETF only) |
| **P2** | FastAPI SIP API + Next.js SIP Lab UI + export |
| **P3** | Benchmark (Upstox), strategy compare, cost toggle, DQ warnings |
| **P4** | Kite equity holdings import + portfolio vs strategy SIP; Coin still later |

---

## 8. Functional requirements (MVP through P2)

### 8.1 Strategy / basket

- Author or select a basket (constituents + weights or equal-weight mode).  
- SIP config: monthly amount, day-of-month, start date, end date (or “to latest price”).  
- Equity/ETF symbols only; map to Upstox `instrument_key`.

### 8.2 Market data

- Fetch/sync historical daily OHLCV via Upstox; cache raw + curated Parquet.  
- No silent fill from other vendors; missing data → warn / partial.

### 8.3 SIP engine

- On each SIP date (adjusted to next session): deploy amount into basket per allocation rules.  
- Track units and portfolio market value over time.  
- Build cashflows; compute **XIRR** (primary) plus secondary path metrics as available (CAGR, max DD, etc. without replacing XIRR as success criterion).

### 8.4 API & UI (P2)

- Run SIP backtest; show XIRR, series, contribution path; data-source banner.  
- Export cashflows + summary (CSV/JSON).

---

## 9. Success metrics

| Metric | Gate |
|--------|------|
| XIRR fixture accuracy | ≤ **1e-4** absolute vs reference |
| SIP day correctness | 100% of fixture calendar cases (incl. weekend/holiday) |
| Provider purity | Zero code paths to non-Upstox live history in product |
| Reproducibility | Same config + same curated prices → same XIRR |
| Secret safety | No secrets in git; public repo clean |

---

## 10. Stack (reuse v0)

| Layer | Choice |
|-------|--------|
| Frontend | Next.js + TypeScript + Tailwind + Recharts |
| Backend | Python + FastAPI |
| Calc / SIP | Pure modules under `src/smallcase_finance/calc/` (+ services) |
| Data | Parquet + DuckDB; pipeline under `data/raw` → `data/curated` |
| Prices | `integrations/upstox/` only for live history |

---

## 11. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Confusing v0 NAV with SIP | Separate SIP service path + PRD/ADR language |
| Sample results look “real” | Labels, banners, DQ warnings; optional strict mode (P3) |
| Token expiry (Upstox ~daily) | CLI/portal re-token; docs; daytime sync |
| Incomplete instrument map | Explicit skips/warnings; no invented prices |
| Scope creep (Coin, trading) | Roadmap order + non-goals |

---

## 12. Open items (not blocking P0–P1 start)

- Exact strategy schema field names and allocation modes beyond weights.  
- Fractional shares vs rupee residual cash (document MVP choice in engine ADR/PR).  
- Holiday calendar: price-calendar “next bar” is enough for MVP.  
- Full SIP Lab wireframes (design after engine fixtures).  

---

## 13. References

- [PRODUCT.md](../../PRODUCT.md) — v0 status (update as SIP Lab becomes current goal)  
- [Upstox contract](../integrations/upstox.md)  
- [Kite Phase 4 plan](../integrations/kite-connect.md)  
- [Metrics definitions](../analytics/metrics-definitions.md)  
- v0 plan / build: [v0-plan.md](../architecture/v0-plan.md), [build-report.md](../build-report.md)
