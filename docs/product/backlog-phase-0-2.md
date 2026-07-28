# Backlog — Phases 0–2 (SIP Lab)

**Product:** SIP Lab / Basket Backtest Engine  
**Scope:** Executable work packages for **P0–P2** only (P3–P4 live on [ROADMAP](../ROADMAP.md))  
**Format:** `id`, `title`, `agent`, `AC`, `deps`, size (`S` / `M` / `L`)  
**Policy:** [ADR 004](../decisions/004-sip-lab-prd-decisions.md), [ADR 005](../decisions/005-upstox-sole-market-data.md), [PRD](./prd-sip-lab.md)

**Size guide:** **S** ≤ ~0.5 day · **M** ~1–2 days · **L** multi-day / multi-file

**Agents:** `data-architect` · `data-engineer` · `backend` · `data-analyst` · `design` · `frontend` · `PO`

---

## Phase 0 — Foundations

| id | title | agent | AC | deps | size |
|----|-------|-------|----|------|------|
| **P0-01** | Define SIP strategy config schema (Pydantic + example JSON) | `data-architect` | Schema covers basket ref or inline constituents, weights/mode, SIP amount, day-of-month (1–28 or documented clamp), start/end, version; invalid configs fail with clear errors; documented in data dictionary or schema doc | — | **M** |
| **P0-02** | Backend load/validate strategy config from local path | `backend` | Service or util loads example strategy; rejects bad fields; unit tests for happy + invalid paths | P0-01 | **S** |
| **P0-03** | Introduce `MarketDataProvider` protocol / interface | `backend` | Abstract get-history (symbol/key, from, to) → OHLCV frame/records; no vendor logic in interface | — | **S** |
| **P0-04** | Upstox as sole `MarketDataProvider` implementation | `backend` | Concrete provider wraps/extends `integrations/upstox/`; only production historical path; no yfinance/bhavcopy/Fyers imports | P0-03 | **M** |
| **P0-05** | Sample/demo provider path labeled non-market | `backend` | Without token, sample path may serve demos; responses/logs include `source=sample` (or equivalent); not presented as Upstox | P0-04 | **S** |
| **P0-06** | Harden raw dated Upstox price drops + pipeline → curated Parquet | `data-engineer` | Sync writes immutable dated drop under `data/raw/prices/`; pipeline updates curated prices; re-run does not mutate prior drops; README/pipeline docs match | P0-04 | **M** |
| **P0-07** | Instrument key coverage for basket symbols | `data-engineer` | Map tickers → Upstox `instrument_key`; missing keys listed with warn/skip; no invented candles | P0-06 | **M** |
| **P0-08** | Secrets contract: env + `.env.example` + docs | `backend` | Placeholders for `UPSTOX_ACCESS_TOKEN`, `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`; docs match portal auth; gitignore protects `.env`; no secrets in repo | — | **S** |
| **P0-09** | Align product docs with sole-provider policy | `PO` | ROADMAP/PRD/ADR cross-links consistent; PRODUCT.md notes SIP Lab as next goal; no “optional multi-provider” language in active SIP docs | P0-08 | **S** |
| **P0-10** | Operator smoke: token → sync → curated (or sample fallback demo) | `data-engineer` | Documented Make/CLI path; founder can complete once with token; without token, sample path is explicit | P0-06, P0-08 | **S** |

### Phase 0 exit

All P0 ACs met; Upstox sole provider wired; strategy config loadable; secrets safe; cache path clear.

---

## Phase 1 — SIP engine + XIRR goldens

| id | title | agent | AC | deps | size |
|----|-------|-------|----|------|------|
| **P1-01** | SIP schedule: fixed calendar day → next trading day | `backend` | Given price session calendar + day-of-month, contribution dates match fixtures for weekday, weekend, and holiday/missing-session cases | P0-01, P0-02 | **M** |
| **P1-02** | Units ledger / allocation (zero costs) | `backend` | Each SIP deploys full amount per weights/mode at documented price field; units deterministic; residual cash rule documented if any | P1-01 | **L** |
| **P1-03** | Portfolio MV path between SIPs | `backend` | Market value series uses held units × prices; endpoints align with cashflow dates for terminal value | P1-02 | **M** |
| **P1-04** | Cashflow series builder | `data-analyst` | Contributions as outflows; terminal (or exit) as inflow; dates/amounts match ledger; exported structure stable for tests | P1-02, P1-03 | **M** |
| **P1-05** | XIRR implementation + numerical stability | `data-analyst` | XIRR on cashflows; edge cases (few cashflows, flat path) documented; pure function testable without API | P1-04 | **M** |
| **P1-06** | Golden fixtures tolerance ≤ 1e-4 | `data-analyst` | Hand-checked or reference XIRR fixtures in `tests/`; CI fails if abs error > 1e-4; equity/ETF only; synthetic prices OK if labeled | P1-05, P1-01 | **L** |
| **P1-07** | SIP run service entrypoint (not v0 rebalance) | `backend` | One function/service: strategy + prices → cashflows, units path, XIRR, secondary metrics; does not call weight-NAV rebalance as SIP | P1-02–P1-05 | **M** |
| **P1-08** | Pytest suite for SIP day + XIRR + allocation | `backend` | `pytest` green locally via Make/target; covers P1-01 and P1-06 at minimum | P1-06, P1-07 | **S** |
| **P1-09** | Engine docs: SIP semantics + non-goals | `data-analyst` | Short doc under `docs/` (metrics or architecture): day rule, zero costs, XIRR primary, vs v0 NAV | P1-07 | **S** |

### Phase 1 exit

Golden XIRR tests pass; SIP service runs multi-period equity/ETF basket offline.

---

## Phase 2 — API + Next.js SIP UI + export

| id | title | agent | AC | deps | size |
|----|-------|-------|----|------|------|
| **P2-01** | API schemas for SIP request/response | `backend` | Pydantic models: strategy or strategy_id, range, result with XIRR, cashflows, series, `data_source` | P1-07 | **M** |
| **P2-02** | `POST` SIP backtest route | `backend` | Route invokes SIP service; 4xx on bad config; 200 with metrics; smoke test | P2-01, P1-08 | **M** |
| **P2-03** | List/load strategies endpoint (if not file-only) | `backend` | UI can list sample strategies or load by id from local defs | P0-02, P2-01 | **S** |
| **P2-04** | SIP Lab page wireframe / UI spec | `design` | Layout: strategy form, run CTA, XIRR KPI, chart, cashflow table, export, source banner; Tailwind-ready notes | P1-09 | **M** |
| **P2-05** | SIP Lab Next.js page + forms | `frontend` | User selects/edits SIP params, runs backtest via API, sees loading/error states | P2-02, P2-04 | **L** |
| **P2-06** | Charts: equity / contribution path | `frontend` | Recharts (or existing stack) plots MV and/or cumulative invested vs value; empty/error states | P2-05 | **M** |
| **P2-07** | KPI strip: XIRR primary + secondary metrics | `frontend` | XIRR emphasized; secondary (e.g. total invested, final value, max DD if returned) readable | P2-05 | **S** |
| **P2-08** | Data-source banner on SIP results | `frontend` | Sample vs Upstox clearly labeled; consistent with API `data_source` | P2-05, P0-05 | **S** |
| **P2-09** | Export cashflows + summary (CSV and/or JSON) | `backend` | API or client-side export matches response cashflows/summary within rounding | P2-02 | **M** |
| **P2-10** | Export control in UI | `frontend` | Download button produces usable file; works in local demo | P2-09, P2-05 | **S** |
| **P2-11** | API docs update (`docs/api.md`) for SIP routes | `backend` | Request/response examples; notes zero costs + SIP day rule | P2-02 | **S** |
| **P2-12** | End-to-end local demo path (Make or README) | `PO` | Documented: pipeline/sync → api → web → run SIP → export; links ROADMAP exit for P2 | P2-05, P2-10 | **S** |

### Phase 2 exit

Browser SIP Lab run against local API; XIRR matches engine; export works; source labeled.

---

## Dependency sketch

```
P0-01 → P0-02 ─────────────────────────────┐
P0-03 → P0-04 → P0-05                       │
         P0-04 → P0-06 → P0-07 → P0-10      │
P0-08 → P0-09 → P0-10                       │
                                            ▼
              P1-01 → P1-02 → P1-03 → P1-04 → P1-05 → P1-06
                        └──────────────────→ P1-07 → P1-08 → P1-09
                                              │
                                              ▼
                    P2-01 → P2-02 → P2-05 → P2-06/07/08
                    P2-04 ↗         P2-09 → P2-10
                    P2-03 ↗         P2-11
                                    P2-12 (PO wrap)
```

---

## Explicitly out of this backlog (do not pull into P0–P2)

| Item | Phase |
|------|-------|
| Benchmark via Upstox, multi-strategy compare, cost toggle, DQ pack | **P3** |
| Kite equity holdings import, portfolio vs strategy compare | **P4** |
| Coin / MF APIs, MF NAV | **After P4** |
| Live trading, F&O, multi-user | **Never (this product line)** |

---

## Tracking notes

- Prefer **one PR per backlog id** or small clustered ids (e.g. P1-04–P1-06).  
- Plan Mode before large L items.  
- When complete, tick ACs here or move id to a “Done” section; update [PRODUCT.md](../../PRODUCT.md) current goal.
