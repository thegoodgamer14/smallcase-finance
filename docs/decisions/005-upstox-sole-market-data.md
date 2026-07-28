# ADR 005 — Upstox as sole historical market-data provider

**Status:** Accepted (binding for SIP Lab)  
**Date:** 2026-07-28  
**Owner:** Backend / Data Engineer  
**Related:** [ADR 004 — SIP Lab PRD decisions](./004-sip-lab-prd-decisions.md), [ADR 003 — Upstox optional (v0.1; partially superseded)](./003-upstox-price-source.md), [Upstox integration contract](../integrations/upstox.md), [pipeline layout](../data/pipeline.md)

---

## Context

SIP Lab needs multi-year daily equity/ETF OHLCV that is reproducible and under founder control. v0 treated Upstox as an **optional** live source with synthetic sample fallback ([ADR 003](./003-upstox-price-source.md)). That flexibility invited silent pollution of “successful” backtests with non-market prices and left the door open to yfinance / bhavcopy / Fyers fallbacks.

Founder policy (see [ADR 004](./004-sip-lab-prd-decisions.md) §1):

- **Upstox API is the sole historical source** for equity/ETF OHLCV in this product version.  
- **No** yfinance, bhavcopy, Fyers, or multi-provider sprawl.  
- Sample prices remain allowed **only for demos without credentials**.  
- Repo is public → secrets never in git.

This ADR locks provider policy, auth, cache, and demo fallback for implementers extending `src/smallcase_finance/integrations/upstox/`.

---

## Decision

### 1) Sole provider

| Concern | Rule |
|---------|------|
| **Production / real SIP claims** | Historical OHLCV **must** originate from Upstox historical candle APIs (V3 daily preferred for multi-year ranges; see [upstox.md](../integrations/upstox.md)). |
| **Forbidden code paths** | Do not add yfinance, NSE bhavcopy, Fyers, or other vendors as price sources in this version. |
| **Scope of Upstox** | Prices only. Smallcase / basket definitions stay local JSON. No live trading, F&O, Coin/MF via Upstox. |
| **Pipeline** | Sync writes **immutable raw drops** under `data/raw/prices/{yyyy-mm-dd}_upstox/` (or equivalent dated Upstox drop); existing raw → curated Parquet pipeline remains the app read path. |

### 2) Auth (developer portal)

Document and implement against official Upstox contracts ([Authentication](https://upstox.com/developer/api-documentation/authentication), [Get Token](https://upstox.com/developer/api-documentation/get-token)):

| Portal / OAuth concept | Env var | Role |
|------------------------|---------|------|
| Access token (Bearer) | **`UPSTOX_ACCESS_TOKEN`** | **Primary** credential for historical candle calls |
| API Key (`client_id`) | `UPSTOX_API_KEY` | App id; OAuth authorize + token exchange |
| API Secret (`client_secret`) | `UPSTOX_API_SECRET` | Server-side token exchange only; never commit |
| Redirect URI | `UPSTOX_REDIRECT_URI` | OAuth only; must match developer app config |

**Supported founder path (MVP):** generate access token in the [Upstox Developer Apps](https://account.upstox.com/developer/apps) portal → set `UPSTOX_ACCESS_TOKEN` locally → CLI / Make sync.

**Optional later:** full OAuth authorization-code flow using key + secret + redirect; not required for first SIP engine correctness.

**Token lifetime:** access tokens expire by **3:30 AM IST the following day** (per Upstox docs). There is no documented refresh_token for the common response — re-generate or re-OAuth when expired. Prefer daytime syncs.

**HTTP:** `Authorization: Bearer <access_token>`. Prefer CLI / Make for sync; any HTTP sync endpoint stays behind an explicit enable flag and must not log secrets.

### 3) Cache and reproducibility

| Layer | Behavior |
|-------|----------|
| **Raw** | Upstox responses (or normalized raw tables) land as **dated raw drops**; do not mutate prior drops. |
| **Curated** | Pipeline builds/refreshes curated Parquet under `data/curated/`; DuckDB/app reads curated only. |
| **Instrument map** | Maintain `instrument_key` (e.g. `NSE_EQ|…`) coverage for basket symbols; missing keys → clear skip/warn, never invent prices from another vendor. |
| **Lookback** | Custom `--years` / `--from` / `--to` remain first-class; default multi-year lookback documented in integration docs (e.g. 3y). Prefer V3 daily (up to decade per request) for SIP ranges. |
| **Re-run** | Same token window + same request range + same pipeline should regenerate equivalent curated prices (modulo Upstox upstream corrections). |

Do **not** silently substitute non-Upstox vendors when candles are missing. Missing symbols/dates must surface as warnings / partial runs, not alternate-provider fills.

### 4) Sample fallback (demos without token)

| Rule | Detail |
|------|--------|
| **When** | No usable `UPSTOX_ACCESS_TOKEN` (and no valid equivalent auth). |
| **What** | Existing **sample / synthetic** price drops under `data/raw/prices/*_sample/` (or pipeline-generated sample). |
| **How to label** | Logs, API responses, and UI must make clear results are **demo / sample**, not live market SIP performance. |
| **What it is not** | Not a second market-data vendor; not acceptable for golden “real market” claims or production SIP reports. |
| **Hard failure** | Optional strict mode (future) may refuse SIP runs without Upstox; default stays “demo runs with warnings” so local onboarding works. |

This preserves ADR 003’s developer-experience goal while **removing** “optional among many providers” ambiguity.

### 5) Secrets and public repo

- Never commit tokens, secrets, or filled `.env`.  
- `.env.example` carries **empty placeholders only**.  
- Public repo: treat any credential leak as an incident (rotate Upstox app secrets / tokens).

---

## Relationship to ADR 003

| ADR 003 (v0.1) | ADR 005 (SIP Lab) |
|----------------|-------------------|
| Upstox optional live source | Upstox **sole** historical provider for real runs |
| Sample default when no credentials | Sample **demo-only** when no credentials (unchanged UX, stricter labeling) |
| No multi-provider ban stated | Explicit ban: no yfinance / bhavcopy / Fyers this version |
| Access token / API key focus | Full portal mapping including **API secret** for OAuth path; token still primary for CLI |

Where they conflict, **ADR 005 + ADR 004 win** for SIP Lab work.

---

## Consequences

- **Positive:** One integration surface to maintain; SIP fixtures can assume Upstox session calendars; agents cannot “just add yfinance.”  
- **Negative:** Founder must refresh access tokens for multi-day sync work; incomplete instrument_key maps block full baskets; multi-year history depends on Upstox availability and API limits.  
- **Code:** Extend existing `src/smallcase_finance/integrations/upstox/` to official contracts; pipeline remains the only path into curated prices.  
- **Risk:** Sample fallback that looks “successful” can still mislead — enforce warnings and UI labels; never use sample for XIRR golden fixtures that claim market fidelity.

---

## Follow-ups

- Migrate client default historical fetch to **V3 daily** where still on V2 year-chunking.  
- Documented operator runbook: token generate → env → `make sync-upstox` → pipeline → SIP run.  
- Strict “require Upstox for SIP” config flag once UI exists.  
- OAuth local callback helper (optional) using `UPSTOX_API_KEY` + `UPSTOX_API_SECRET`.
