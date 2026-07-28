# Build Report — SIP Lab Plan (PO Synthesis)

**Date:** 2026-07-28  
**Audience:** Founder / next implementation session  
**Role:** Product Owner synthesis of vision, inventory, this run, and Phase 0–2 next steps  
**Binding policy:** [ADR 004](./decisions/004-sip-lab-prd-decisions.md) · [ADR 005](./decisions/005-upstox-sole-market-data.md)  
**Executable plan:** [ROADMAP.md](./ROADMAP.md) · [product/prd-sip-lab.md](./product/prd-sip-lab.md) · [product/backlog-phase-0-2.md](./product/backlog-phase-0-2.md)  
**v0 baseline (still shippable):** [build-report.md](./build-report.md)

This report only claims what exists in the repo after inspection. Specs and scaffolds are separated from a working SIP engine.

---

## 1) Vision

**Product:** SIP Lab / Basket Backtest Engine (evolution of smallcase-finance v0).

**Job to be done:** *If I had SIP’d a fixed INR amount into this custom stock/ETF basket every month, what would my **XIRR** and path look like?*

| Pillar | Meaning |
|--------|---------|
| **SIP-first** | Explicit monthly cash → buy units → mark-to-market → cashflow series → **XIRR** (primary metric) |
| **Baskets** | Local smallcase JSON / strategy config (weights or equal-weight); founder-authored, not Smallcase.com scrape |
| **Reproducible** | Upstox history → immutable raw drops → curated Parquet → pure calc → API/UI; golden fixtures gate correctness |
| **Honest demos** | Sample/synthetic prices allowed without credentials, **labeled demo only** — never as live market SIP |
| **Local-first** | Run on the founder’s machine; public code, private secrets |

**Primary success metric:** XIRR on contribution + terminal cashflows, golden absolute tolerance **≤ 1e-4**.

**Not SIP:** v0 weight-based NAV (`calc/nav.py`) and `POST /backtest` rebalance-vs-buyhold. Those remain valid for index-style demos; they must **not** be reused as SIP performance.

**Locked implementation order** ([ADR 004](./decisions/004-sip-lab-prd-decisions.md)):

1. Correct SIP engine  
2. SIP Lab UI  
3. Kite equity import / live-vs-SIP compare (Phase 4)  
4. **Coin / MF last** (not this version)

---

## 2) Upstox-only history

**Policy (binding):** Equity/ETF historical **OHLCV** for real SIP / basket claims comes **only** from the **Upstox API**.

| Rule | Detail |
|------|--------|
| **Sole live source** | Upstox historical candles → dated raw drop → pipeline → `data/curated/prices/` |
| **Forbidden this version** | yfinance, NSE bhavcopy, Fyers, multi-provider sprawl |
| **Without token** | Sample/synthetic prices under `data/raw/prices/*_sample/` (or pipeline GBM generator) for **demo only** |
| **Missing data** | Skip / warn; never invent prices from another vendor |
| **Kite** | Holdings import only in Phase 4; **not** a price source |
| **Coin / MF** | Out of scope for history and for product surface this version |

**Code that exists today:**

- Client + CLI sync: `src/smallcase_finance/integrations/upstox/` (`client.py`, `sync.py`, `instruments.py`, `__main__.py`)
- Make target: `make sync-upstox` (falls back to sample when no token, then still runs pipeline)
- Provider layer (this run): `MarketDataProvider` protocol + `UpstoxProvider` under `src/smallcase_finance/market_data/`
- Config gate: `upstox_configured()` requires non-empty `UPSTOX_ACCESS_TOKEN`

**Still true operationally:** live sync remains **token-optional with sample fallback**. Policy docs (ADR 005) require labeling sample as demo; a future “strict require Upstox” mode is Phase 3, not implemented.

Full contract: [docs/integrations/upstox.md](./integrations/upstox.md).

---

## 3) Coin deferred

| Item | Status |
|------|--------|
| Coin import APIs | **Not built** — correct non-goal |
| MF holdings endpoints | **Not built** |
| MF NAV engine | **Not built** |
| Product docs | Explicit deferral in PRODUCT.md, PRD, ADR 004, ROADMAP (“after Phase 4 / last”) |

Coin remains **last** on the ordered roadmap. Do not pull MF work into Phase 0–2.

---

## 4) Public repo

| Rule | Practice |
|------|----------|
| **Visibility** | Repository stays **public** |
| **Secrets** | Env / gitignored `.env` only — never commit tokens or filled env files |
| **Template** | `.env.example` ships **empty placeholders only** |
| **Incident** | Accidental secret commit → rotate Upstox app secret / tokens immediately |

Env names used in code and docs:

- `UPSTOX_ACCESS_TOKEN` (primary Bearer for candles)
- `UPSTOX_API_KEY` (portal API Key / OAuth `client_id`)
- `UPSTOX_API_SECRET` (portal API Secret / OAuth `client_secret`)
- `UPSTOX_REDIRECT_URI` (OAuth only)
- Optional: `UPSTOX_API_BASE`, `UPSTOX_DEFAULT_YEARS`, `UPSTOX_SYNC_ENABLED`

---

## 5) What shipped this run

Two layers: **v0 already complete** (prior DoD; see [build-report.md](./build-report.md)), and **SIP Lab planning + Phase 0 scaffolds** present in the working tree (product docs + strategy/provider code + secrets hardening). The SIP **engine** (units, cashflows, XIRR) is **not** implemented.

### 5.1 Product & architecture docs (SIP Lab)

| Artifact | Path |
|----------|------|
| PRD (condensed) | `docs/product/prd-sip-lab.md` |
| Backlog P0–P2 | `docs/product/backlog-phase-0-2.md` |
| Roadmap phases 0–4 | `docs/ROADMAP.md` |
| ADR 004 PRD decisions | `docs/decisions/004-sip-lab-prd-decisions.md` |
| ADR 005 Upstox sole source | `docs/decisions/005-upstox-sole-market-data.md` |
| SIP engine design | `docs/architecture/sip-engine.md` |
| SIP data dictionary | `docs/data-dictionary-sip.md` |
| SIP Lab page spec (UI not built) | `docs/design/pages/sip-lab.md` |
| Kite Phase 4 plan only | `docs/integrations/kite-connect.md` |
| PRODUCT / README vision update | `PRODUCT.md`, `README.md` |
| Upstox auth + sole-provider docs | `docs/integrations/upstox.md`, `.env.example` |

### 5.2 Code scaffolds (Phase 0 progress — not a full SIP product)

| Piece | Location | Notes |
|-------|----------|--------|
| **Strategy / SIP config schema** | `src/smallcase_finance/strategies/models.py` | Pydantic: amount, day_of_month 1–28, start/end, basket inline or smallcase_ref, allocation mode, zero-cost defaults |
| **Config loader** | `src/smallcase_finance/strategies/loader.py` | YAML/JSON; nested `sip:` or flat fields |
| **Example strategy** | `config/strategies/example-sip-equity.yaml` | Illustrative 4-name equal-weight-style basket + ₹5k SIP day 5 |
| **MarketDataProvider protocol** | `src/smallcase_finance/market_data/protocol.py` | Vendor-agnostic `get_history` |
| **UpstoxProvider** | `src/smallcase_finance/market_data/upstox_provider.py` | Sole production impl; empty history + `source_label=sample` when unconfigured |
| **Secrets in config** | `src/smallcase_finance/config.py` | `UPSTOX_ACCESS_TOKEN`, `API_KEY`, `API_SECRET`, `REDIRECT_URI` |
| **Tests** | `tests/test_strategy_config.py`, `tests/test_market_data_provider.py` | Verified green (23 tests) in this inspection |

### 5.3 Still not shipped (critical gaps)

| Gap | Evidence |
|-----|----------|
| SIP contribution engine (monthly cash → buy) | No `calc/sip_*`; `calc/` is still nav/returns/risk/weights/rebalance only |
| XIRR + cashflow series | No `calc/xirr.py`; no cashflow fixtures; no 1e-4 golden suite |
| Units / lot ledger + MV-from-units | No ledger module; SIP data dictionary describes tables not yet produced |
| Calendar SIP day → next trading day **engine** | Field exists on `SIPConfig`; schedule logic not implemented |
| SIP run service / API | No SIP route; `POST /backtest` remains lump-sum rebalance vs buy-hold only |
| SIP Lab web UI | Routes are `/`, `/holdings`, `/performance` only; page **spec** exists, no `app/sip-lab/` |
| Strict Upstox-only enforcement at run time | Sample fallback still powers demos without token (by design for onboarding) |
| Kite equity import | Spec only (`docs/integrations/kite-connect.md`) |

### 5.4 v0 baseline still available (reuse, not SIP)

End-to-end local demo remains: basket JSON → pipeline/Parquet → weight-NAV/risk → FastAPI → Next.js.

| Layer | Exists |
|-------|--------|
| Pipeline raw → curated | `python3 -m smallcase_finance.pipeline` / `make pipeline` |
| Pure calc (no I/O) | `calc/nav`, `returns`, `risk`, `weights`, `rebalance` |
| API | health, smallcases, holdings, nav, performance, metrics, attribution, `POST /backtest`, optional Upstox sync |
| UI | Dashboard, holdings, performance; AppShell, MetricCard, charts, format/hooks/types |
| Sample baskets | `digital-india`, `momentum-quality` |
| Upstox client + instrument map | integrations + CLI + Make |
| Tests | metrics + API smoke + upstox (+ new strategy/provider tests) |

---

## 6) Phase 0–2 next steps

Canonical IDs: [backlog-phase-0-2.md](./product/backlog-phase-0-2.md) and [ROADMAP.md](./ROADMAP.md).  
*(Note: `PRODUCT.md` labels “Phase 0” as v0 shipped; ROADMAP/backlog use Phase 0 = SIP foundations. Prefer ROADMAP IDs below.)*

### Phase 0 — Foundations (finish remaining ACs)

**Already advanced this run:** P0-01/02 (strategy schema + load), P0-03/04/05 (provider + Upstox + sample label), P0-08 (secrets env + docs), partial P0-09 (product docs aligned).

| Priority | Backlog | Work | Done when |
|----------|---------|------|-----------|
| Next | **P0-06** | Harden dated Upstox raw drops + pipeline → curated | Immutable drops; docs match; re-run safe |
| Next | **P0-07** | Instrument key coverage for basket symbols | Missing keys warn/skip; no invented candles |
| Next | **P0-10** | Operator smoke: token → sync → curated | Documented Make/CLI path founder can complete once |
| Polish | **P0-09** | Keep PRODUCT/README/ROADMAP language consistent (phase numbering) | No conflicting “multi-provider optional” in active SIP docs |

**Exit:** Founder can set a portal token, sync a basket’s symbols, and see curated prices tagged Upstox (or clearly labeled sample without token).

### Phase 1 — SIP engine + XIRR goldens (primary build)

| Order | Backlog | Work |
|-------|---------|------|
| 1 | **P1-01** | Fixed calendar day → next trading day from price session calendar |
| 2 | **P1-02** | Units ledger / allocation at close; zero costs; fractional units MVP |
| 3 | **P1-03** | Portfolio market-value path between SIPs |
| 4 | **P1-04** | Cashflow series (contributions out, terminal in) |
| 5 | **P1-05** | XIRR pure function + edge cases |
| 6 | **P1-06** | Golden fixtures abs tol **≤ 1e-4** |
| 7 | **P1-07** | SIP run service (must not call rebalance NAV as SIP) |
| 8 | **P1-08** | Pytest suite green via Make |
| 9 | **P1-09** | Engine docs already started (`sip-engine.md`); keep in sync with code |

**Exit:** `pytest` green on SIP day + XIRR goldens; one service/CLI path runs multi-period equity/ETF SIP offline.

**Do not start:** UI, Kite, Coin, cost models that break zero-cost goldens.

### Phase 2 — API + Next.js SIP Lab + export

| Area | Backlog | Work |
|------|---------|------|
| API | **P2-01–P2-03, P2-09, P2-11** | SIP request/response schemas; `POST` SIP run; list strategies; export; `docs/api.md` |
| Design | **P2-04** | Spec largely present (`design/pages/sip-lab.md`); refine if engine response shape differs |
| UI | **P2-05–P2-08, P2-10** | `/sip-lab` page, charts, XIRR KPI, data-source banner, export control |
| Wrap | **P2-12** | E2E local demo path in README/Make |

**Exit:** Browser SIP Lab against local API; XIRR matches engine; export works; sample vs Upstox labeled.

### Explicitly later

| Phase | Scope |
|-------|--------|
| **P3** | Benchmark (Upstox), multi-strategy compare, optional costs, DQ warnings, strict Upstox mode |
| **P4** | Kite equity holdings import + portfolio vs strategy SIP |
| **After** | Coin / MF |

---

## 7) How to configure Upstox credentials

Official portal: [Upstox Developer Apps](https://account.upstox.com/developer/apps)  
Project runbook: [docs/integrations/upstox.md](./integrations/upstox.md)

### 7.1 Recommended MVP path (manual portal token)

1. Create an app in the Upstox developer portal.  
2. Note **API Key** and **API Secret** (for future OAuth only).  
3. Click **Generate** to create an **access token**.  
4. From repo root:

```bash
cp .env.example .env
# edit .env — set ONLY local values; never commit .env
```

```bash
# .env (gitignored)
UPSTOX_ACCESS_TOKEN=your_bearer_token_here
# optional for OAuth later:
# UPSTOX_API_KEY=
# UPSTOX_API_SECRET=
# UPSTOX_REDIRECT_URI=
```

5. Soft-load: `config.py` loads `.env` via python-dotenv without overriding real shell env. Or:

```bash
export UPSTOX_ACCESS_TOKEN='...'
```

6. Sync + pipeline:

```bash
make sync-upstox
# or with range:
# make sync-upstox YEARS=5
# make sync-upstox FROM=2021-01-01 TO=2024-12-31 SYMBOLS=TCS,INFY
```

Without `UPSTOX_ACCESS_TOKEN`, sync falls back to **sample** prices and still runs the pipeline — results are demos, not market SIP.

### 7.2 Env var map

| Env var | Required for live candles? | Role |
|---------|----------------------------|------|
| **`UPSTOX_ACCESS_TOKEN`** | **Yes** | Bearer for historical APIs (primary) |
| `UPSTOX_API_KEY` | OAuth only | Portal API Key = `client_id` |
| `UPSTOX_API_SECRET` | OAuth token exchange only | Portal API Secret = `client_secret` — **not** used by current CLI sync |
| `UPSTOX_REDIRECT_URI` | OAuth only | Must match developer app |
| `UPSTOX_API_BASE` | No | Default `https://api.upstox.com/v2` |
| `UPSTOX_DEFAULT_YEARS` | No | Default lookback (**3**) when `--years` / `--from` omitted |
| `UPSTOX_SYNC_ENABLED` | No | Set `1` only if using HTTP `POST /integrations/upstox/sync`; prefer CLI |

### 7.3 Token lifetime

Access tokens expire around **3:30 AM IST the following day** (per Upstox Get Token docs). No documented refresh token for the common response — re-generate or re-OAuth. Prefer daytime syncs.

### 7.4 OAuth (optional later)

Authorization-code flow uses `UPSTOX_API_KEY` + `UPSTOX_API_SECRET` + `UPSTOX_REDIRECT_URI`. Documented in [upstox.md](./integrations/upstox.md) §1.2 Option B. **Not required** for first SIP engine correctness.

### 7.5 Public-repo checklist

- [ ] `.env` is gitignored and never staged  
- [ ] `.env.example` has empty values only  
- [ ] No tokens in logs, manifests, or Parquet metadata  
- [ ] If leaked: rotate secret/token in portal immediately  

---

## 8) Risks

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| **Reusing weight-NAV / rebalance as SIP** | Wrong XIRR and contribution semantics | Dedicated SIP path in `calc/` + service; keep `POST /backtest` labeled rebalance-only |
| **Sample prices look “successful”** | Founder trusts fake market path | Labels, banners, `source=sample`; future strict mode (P3); never use sample for “real market” goldens |
| **Access-token-only path expires daily** | Multi-year sync interrupted; incomplete OAuth hurts reproducibility | Docs + re-token runbook; optional OAuth later; prefer daytime sync |
| **Silent missing-price renormalization** | Partial SIP months hidden | Explicit skip/warn; surface partial runs in API/UI |
| **~21-day rebalance step ≠ calendar SIP day** | v0 rebalance cadence is not SIP schedule | Implement fixed day-of-month → next session (P1-01) |
| **Scope creep (UI / Kite / Coin before engine)** | Broken numbers polished by charts | Order: engine → UI → Kite → Coin |
| **Public repo secret commit** | Credential leak | Empty `.env.example`; never commit `.env`; rotate on incident |
| **CAGR / NAV misread as SIP performance** | Retail metric confusion | XIRR primary in UI/API; secondary metrics demoted in copy |
| **Incomplete instrument_key map** | Basket symbols silently incomplete | Warn/skip list; extend map / instruments master (P0-07) |
| **PRODUCT vs ROADMAP phase numbering** | Agent confusion on “Phase 0” | Prefer ROADMAP backlog IDs; align PRODUCT wording when touching docs |

---

## 9) Inventory snapshot

### Gaps (remaining for SIP Lab)

- No SIP contribution engine (monthly invest schedule, cash → buy)  
- No XIRR / cashflow series; no 1e-4 XIRR fixtures  
- No share/unit lot ledger or market-value-from-units model  
- SIP **strategy config exists** (schema + loader + example); **engine that consumes it does not**  
- No fixed calendar day → next trading day **runtime** (config field only; v0 rebalance still ~21/63-day style steps)  
- Upstox is sole *policy* provider; operationally still optional with labeled sample fallback  
- OAuth end-to-end helper not built (`API_SECRET` documented/env-wired; CLI uses access token)  
- No SIP run API (cashflows, XIRR, units path); `POST /backtest` is lump-sum rebalance only  
- Web UI has no SIP Lab route (design spec only)  
- Kite equity import / live-vs-SIP compare deferred (Phase 4, not built)  
- Coin / MF deferred (correct non-goal for this version)

### Reuse (build on, do not re-litigate)

- FastAPI layering: api → services → data_access; pure `calc/` with no I/O  
- Pipeline raw → curated Parquet + DuckDB reads under `data/curated/`  
- Upstox client, CLI sync, instrument_key map, raw price drop contract  
- `MarketDataProvider` + `UpstoxProvider` (this run)  
- StrategyConfig / SIPConfig + example YAML (this run)  
- Smallcase JSON schema (versioned constituents/weights) + sample baskets  
- Weight normalize/drift/rebalance helpers and risk metrics (vol, DD, total return)  
- NAV/returns primitives as **secondary** path metrics (not SIP primary)  
- Config/dotenv pattern, Makefile demo/test, pytest smoke harness  
- Next.js shell: AppShell, charts, MetricCard, format/hooks/types  
- Docs patterns: data dictionary, ADRs, metrics definitions, SIP engine/data dictionary  
- Zero-cost MVP posture already documented  

### Risks (short list)

See §8. Highest urgency: wrong engine model, sample pollution, token expiry, public-repo secrets, scope creep before XIRR goldens.

### Summary

**v0 smallcase-finance** is a complete local demo: basket JSON → pipeline/Parquet → weight-based NAV/risk → FastAPI → Next.js, with optional Upstox OHLCV and sample fallback.

**This run** locked SIP Lab product policy (Upstox-only history, Coin deferred, public repo, XIRR primary, calendar SIP day rule) and shipped Phase 0 **scaffolds**: strategy config, market-data provider abstraction, secrets documentation, and roadmap/backlog.

**SIP Lab still needs** a different engine (monthly cash → units → XIRR), calendar SIP rules in code, golden fixtures, then API/UI. Reuse stack, Upstox client, pipeline, baskets, strategy schema, and pure calc layering; **build SIP/XIRR first, UI second, Kite later, Coin last.**

---

## 10) Suggested next session (PO)

1. Finish **P0-06 / P0-07 / P0-10** (cache + instrument coverage + operator smoke) if any AC incomplete.  
2. Enter Plan Mode for **P1-01–P1-07** as one engine epic; implement pure functions first, service second.  
3. Gate merge on **XIRR goldens ≤ 1e-4** before any SIP UI.  
4. Keep Coin and Kite out of PRs until Phase 1 exit.  

**Commands (current repo):**

```bash
make demo              # v0 path: install → pipeline → test
make sync-upstox       # Upstox (or sample fallback) → pipeline
make test              # includes strategy + market_data + metrics + API smoke
make api && make web   # v0 UI only — no SIP Lab page yet
```

---

## 11) References

| Doc | Role |
|-----|------|
| [PRODUCT.md](../PRODUCT.md) | Vision + current goal |
| [docs/ROADMAP.md](./ROADMAP.md) | Phases 0–4 exit gates |
| [docs/product/prd-sip-lab.md](./product/prd-sip-lab.md) | Binding PRD summary |
| [docs/product/backlog-phase-0-2.md](./product/backlog-phase-0-2.md) | Executable tickets |
| [docs/architecture/sip-engine.md](./architecture/sip-engine.md) | Engine design contract |
| [docs/data-dictionary-sip.md](./data-dictionary-sip.md) | SIP entities |
| [docs/integrations/upstox.md](./integrations/upstox.md) | Auth + candle contract |
| [docs/build-report.md](./build-report.md) | v0 ship report |
| [docs/analytics/metrics-definitions.md](./analytics/metrics-definitions.md) | v0 NAV metrics (secondary for SIP) |
