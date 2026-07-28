# Upstox Historical Market Data — Research Notes

**Canonical user/ops guide:** [`upstox.md`](upstox.md) (start there)  
**Audience:** Backend / Data Engineer implementers  
**Scope:** Equity/ETF (India) historical OHLC for SIP Lab / basket backtests (~3y default lookback)  
**Status:** Research companion — endpoint accuracy verified against official docs (2026-07-28); client lives under `src/smallcase_finance/integrations/upstox/`  
**Product binding:** Upstox is the **sole** historical equity/ETF OHLCV source this version — **no** yfinance, bhavcopy, or Fyers. Without token → sample data for demo only.  
**Repo prices contract:** [`docs/data-dictionary.md`](../data-dictionary.md) § `prices`

---

## Summary for implementers

| Need | Recommendation |
|------|----------------|
| Auth for personal sync CLI | Manual access token (or OAuth code exchange) → `UPSTOX_ACCESS_TOKEN` env |
| App credentials | `UPSTOX_API_KEY` (= `client_id`) + `UPSTOX_API_SECRET` (= `client_secret`) (+ `UPSTOX_REDIRECT_URI` if OAuth) |
| Daily OHLC (preferred) | **V3** `GET /v3/historical-candle/{instrument_key}/days/1/{to_date}/{from_date}` |
| Daily OHLC (current client default) | **V2** `GET /v2/historical-candle/{instrument_key}/day/{to_date}/{from_date}` — **~1 year max** per call; chunk or migrate to V3 for multi-year |
| Symbol resolution | Curated map + `data/raw/instruments/upstox_instrument_map.json`; optional BOD JSON / search API |
| 3-year lookback | **One request per symbol** on V3 daily (max retrieval = 1 decade) |
| Secrets | **Never commit**; `.env` / shell env only; ship `.env.example` placeholders only |
| Fallback | Synthetic sample under `data/raw/prices/*_sample/` when token missing |
| Alternate providers | **None** in this product version |

---

## 1) Auth model

### 1.1 Overview

Upstox uses **OAuth 2.0 authorization code flow**. The application never handles the user's Upstox password; the user authenticates on Upstox, and the app receives an `access_token` for subsequent API calls.

Docs:

- [Authentication](https://upstox.com/developer/api-documentation/authentication)
- [Get Token](https://upstox.com/developer/api-documentation/get-token)
- [Request structure](https://upstox.com/developer/api-documentation/request-structure)

### 1.2 App registration

Create an app at [Upstox Developer Apps](https://account.upstox.com/developer/apps). You receive:

| Upstox name | OAuth name | Use |
|-------------|------------|-----|
| **API Key** | `client_id` | Public app id in authorize URL + token exchange |
| **API Secret** | `client_secret` | Server-side only; token exchange |
| **Redirect URI** | `redirect_uri` | Must match exactly between app config and token request |

### 1.3 Ways to obtain an access token

| Method | Best for this project | How |
|--------|----------------------|-----|
| **Manual** (dashboard **Generate**) | **v0.1 CLI / make sync** | Copy token into env; no OAuth plumbing |
| **Authorization code flow** | Future one-click connect | Dialog → `code` → POST token |
| **Semi-automated** (access-token-request + notifier webhook) | Scheduled jobs with phone approval | Beta flow; see [Access Token Request](https://upstox.com/developer/api-documentation/access-token-request) |

#### OAuth code flow (reference)

1. Redirect user to:
   ```
   https://api.upstox.com/v2/login/authorization/dialog
     ?response_type=code
     &client_id=<API_KEY>
     &redirect_uri=<REDIRECT_URI>
     &state=<optional>
   ```
2. Callback: `?code=...&state=...` (`code` is **single-use**).
3. Exchange:
   ```
   POST https://api.upstox.com/v2/login/authorization/token
   Content-Type: application/x-www-form-urlencoded

   code=...&client_id=...&client_secret=...&redirect_uri=...&grant_type=authorization_code
   ```

Response fields of interest ([Get Token](https://upstox.com/developer/api-documentation/get-token)):

| Field | Notes |
|-------|--------|
| `access_token` | Bearer token for API calls |
| `extended_token` | Longer-lived, **read-oriented**; some write APIs reject it (`UDAPI100067`) |
| `user_id`, `exchanges`, … | Profile metadata; not needed for candles |

### 1.4 Token lifetime

From official Get Token docs:

> The `access_token` is valid **until 3:30 AM the following day** (IST), regardless of when it was issued.  
> Example: token at 8 PM Tuesday expires 3:30 AM Wednesday; token at 2:30 AM Wednesday also expires 3:30 AM that same Wednesday.

There is **no refresh_token** in the documented response. Re-auth / re-generate when expired.

### 1.5 Calling authenticated APIs

```http
Authorization: Bearer <access_token>
Accept: application/json
```

Base URL pattern: `https://api.upstox.com/{v2|v3}/...`  
([Request structure](https://upstox.com/developer/api-documentation/request-structure))

### 1.6 Recommended env vars (this repo)

| Env var | Required for | Secret? | Notes |
|---------|--------------|---------|--------|
| `UPSTOX_ACCESS_TOKEN` | Historical + search APIs | **yes** | Primary Bearer for sync CLI |
| `UPSTOX_API_KEY` | OAuth / token exchange | treat as secret | Official = `client_id`. **Not** a Bearer alias — put the token only in `UPSTOX_ACCESS_TOKEN`. |
| `UPSTOX_API_SECRET` | OAuth / token exchange | **yes** | = `client_secret` (not used by sync CLI today) |
| `UPSTOX_REDIRECT_URI` | OAuth only | no | Must match app config |
| `UPSTOX_API_BASE` | Client base URL | no | Default `https://api.upstox.com/v2` |
| `UPSTOX_DEFAULT_YEARS` | Lookback default | no | Default `3` |
| `UPSTOX_SYNC_ENABLED` | HTTP POST sync | no | Default off; prefer CLI |
| `UPSTOX_EXTENDED_TOKEN` | Optional read path | **yes** | Prefer `ACCESS_TOKEN` unless we verify historical works with extended |

**Explicit policy:** never store secrets in git. Commit only `.env.example` with empty placeholders. Local `.env` must be gitignored. See canonical [upstox.md §2](upstox.md#2-environment-variables-this-project).

Example `.env.example` (placeholders only):

```bash
# Upstox — never commit real values
UPSTOX_ACCESS_TOKEN=
# UPSTOX_API_KEY=          # OAuth client_id; not the Bearer
# UPSTOX_API_SECRET=
# UPSTOX_REDIRECT_URI=http://127.0.0.1:8765/callback
# UPSTOX_API_BASE=https://api.upstox.com/v2
# UPSTOX_DEFAULT_YEARS=3
```

Instrument **master download** (BOD JSON) does **not** require auth (public CDN URLs).

---

## 2) Resolving NSE/BSE symbol → `instrument_key`

Upstox APIs do **not** accept bare tickers like `INFY` on the candle endpoint. They require an **`instrument_key`**.

Format (equities):

```text
{SEGMENT}|{ISIN_or_token}
```

Examples:

| Symbol | Exchange | `instrument_key` |
|--------|----------|------------------|
| RELIANCE | NSE | `NSE_EQ\|INE002A01018` |
| RELIANCE | BSE | `BSE_EQ\|INE002A01018` |
| NIFTY 50 index | NSE | `NSE_INDEX\|Nifty 50` |

Field pattern appendix: [Field Pattern](https://upstox.com/developer/api-documentation/appendix/field-pattern)  
(`instrument_key` ≈ `SEGMENT|identifier`; pipe must be **URL-encoded as `%7C`** in path).

### 2.1 Preferred: BOD instruments JSON (no auth)

Docs: [Instruments](https://upstox.com/developer/api-documentation/instruments)

| File | URL |
|------|-----|
| Complete | `https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz` |
| NSE only | `https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz` |
| BSE only | `https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz` |

- Refresh: ~daily around **6 AM**; rarely mid-day.
- Prefer **JSON** (CSV deprecated).
- Use `instrument_key` as the stable id (not `exchange_token`, which can be reused after expiry for derivatives).

Sample equity object (from docs):

```json
{
  "segment": "NSE_EQ",
  "name": "RELIANCE INDUSTRIES LTD",
  "exchange": "NSE",
  "isin": "INE002A01018",
  "instrument_type": "EQ",
  "instrument_key": "NSE_EQ|INE002A01018",
  "exchange_token": "2885",
  "trading_symbol": "RELIANCE",
  "short_name": "Reliance Industries",
  "security_type": "NORMAL"
}
```

### 2.2 Mapping algorithm (equities for our smallcases)

Our symbols are uppercase tickers **without** exchange suffix (`INFY`, not `INFY.NS`) — see data dictionary conventions.

Recommended resolve rules:

1. Load NSE (and optionally BSE) instrument JSON.
2. Filter: `segment in {"NSE_EQ","BSE_EQ"}` and equity-like `instrument_type` (typically `EQ`; also series like `BE`, `A` on BSE — validate per name).
3. Match `trading_symbol.upper() == symbol`.
4. **Default exchange preference: NSE** (v0: one primary listing per symbol).
5. If no NSE hit, try BSE; if still missing → **WARN + skip symbol** (aligns with incomplete-price policy).
6. Cache map: `symbol → {instrument_key, isin, exchange, name}` under `data/raw/instruments/` or curated instruments.

Optional enrichment into our `instruments` table: `isin`, `exchange`, `name`.

### 2.3 Alternative: Search Instruments API (auth required)

```http
GET https://api.upstox.com/v2/instruments/search?query=RELIANCE&exchanges=NSE&segments=EQ
Authorization: Bearer {token}
```

Docs: [Search Instruments](https://upstox.com/developer/api-documentation/instrument-search)

- Free-text / ISIN search; pagination max **30** records/page.
- Good for ad-hoc lookups; **bulk BOD file is better** for syncing a full universe.

### 2.4 Ambiguity notes

- Same ISIN can appear on **NSE and BSE** with different `instrument_key`s — pick one (NSE default).
- `trading_symbol` is the right join key for our local JSON smallcases (`TCS`, `INFY`, …).
- Indices use different keys (`NSE_INDEX|Nifty 50`); not required for equity smallcases in v0.1.

---

## 3) Historical candle endpoint

### 3.1 Prefer V3 for multi-year daily bars

**Announcement:** [Enhanced Historical Candle Data APIs V3](https://upstox.com/developer/api-documentation/announcements/enhanced-historical-candle-data-apis-v3)  
**Endpoint docs:** [Historical Candle Data V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data)

```http
GET https://api.upstox.com/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
Authorization: Bearer {access_token}
Accept: application/json
```

Path params:

| Param | Daily backtest value | Notes |
|-------|----------------------|--------|
| `instrument_key` | e.g. `NSE_EQ\|INE002A01018` | URL-encode `\|` → `%7C` |
| `unit` | `days` | Also: `minutes`, `hours`, `weeks`, `months` |
| `interval` | `1` | Only `1` for days/weeks/months |
| `to_date` | inclusive end `YYYY-MM-DD` | Required |
| `from_date` | start `YYYY-MM-DD` | Optional; include for explicit range |

Example (3y-ish daily for NHPC-style key from docs):

```text
https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE848E01016/days/1/2026-07-28/2023-07-28
```

#### V3 availability & max range (official table)

| Unit | Interval options | History from | Max span per request |
|------|------------------|--------------|----------------------|
| minutes | 1–300 | Jan 2022 | 1 month (≤15m); 1 quarter (>15m) |
| hours | 1–5 | Jan 2022 | 1 quarter |
| **days** | **1** | **Jan 2000** | **1 decade** up to `to_date` |
| weeks | 1 | Jan 2000 | No limit (docs) |
| months | 1 | Jan 2000 | No limit (docs) |

**Implication for default 3-year lookback:** one V3 daily call per symbol covers the full window. No year-chunking required (unlike V2 daily).

### 3.2 V2 historical (legacy; still documented)

Docs: [Historical Candle Data (v2)](https://upstox.com/developer/api-documentation/get-historical-candle-data)

```http
GET https://api.upstox.com/v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
```

| Interval | Documented max lookback ending at `to_date` |
|----------|-----------------------------------------------|
| `1minute` | final month |
| `30minute` | past year |
| **`day`** | **past year** |
| `week` | past ten years |
| `month` | past ten years |

**If forced to use V2 daily:** paginate with **≤1 year** windows (walk `to_date` backward), merge, dedupe by date.

### 3.3 Intraday (current session only — not for multi-year backtest)

- V2: [Intraday Candle Data](https://upstox.com/developer/api-documentation/get-intra-day-candle-data)  
  `GET /v2/historical-candle/intraday/{instrument_key}/{1minute|30minute}`
- V3: [Intraday Candle Data V3](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data)

Out of scope for v0.1 multi-year NAV.

### 3.4 Market quote OHLC (snapshot, not history)

Docs: [OHLC Quotes](https://upstox.com/developer/api-documentation/get-market-quote-ohlc)

```http
GET https://api.upstox.com/v2/market-quote/ohlc?instrument_key=...&interval=1d
```

- Up to **500** instrument keys per call.
- For `1d`, returns **live/session OHLC**, not multi-year history.
- Use for optional “today’s bar” refresh only; **not** a substitute for historical candles.

### 3.5 Rate limits

Docs: [Rate limiting](https://upstox.com/developer/api-documentation/rate-limiting)

Historical candles fall under **Other Standard APIs** (per-user, per-API class):

| Window | Limit |
|--------|-------|
| Per second | **50** |
| Per minute | **500** |
| Per 30 minutes | **2000** |

Exceeding → HTTP **429** / error `UDAPI10005` (“Too Many Request Sent”).  
Docs warn temporary suspension possible if limits are abused.

**Practical sync pacing (smallcase ~10–50 symbols, 1 req/symbol):** well under limits; still add a small delay (e.g. 50–100 ms) and backoff on 429 for politeness.

### 3.6 Pagination model

There is **no cursor/page token**. Pagination = **client-driven date windowing**:

1. Choose `from_date` / `to_date` within unit max span.
2. If range exceeds max → split into adjacent windows.
3. Concatenate `candles` arrays; sort by timestamp; drop duplicates.

For V3 `days/1` and N≤10 years: **no split**.

### 3.7 One instrument per request

Historical candle endpoints accept a **single** `instrument_key` (not comma-separated). Loop symbols sequentially (or with modest concurrency ≤ rate limits).

---

## 4) Response → our `prices` contract

### 4.1 Upstox candle array

Success body (V2 and V3 share this shape):

```json
{
  "status": "success",
  "data": {
    "candles": [
      [
        "2023-10-01T00:00:00+05:30",
        53.1,
        53.95,
        51.6,
        52.05,
        235519861,
        0
      ]
    ]
  }
}
```

| Index | Field | Type | Notes |
|-------|-------|------|--------|
| 0 | timestamp | string ISO-8601 | Usually IST (`+05:30`); day bars often midnight IST |
| 1 | open | number | |
| 2 | high | number | |
| 3 | low | number | |
| 4 | close | number | |
| 5 | volume | number | |
| 6 | open interest | number | 0 for cash equities |

Candles may arrive **newest-first** (examples show reverse chrono) — **always sort ascending by date** before write.

### 4.2 Mapping to curated / raw `prices` schema

From [`docs/data-dictionary.md`](../data-dictionary.md):

| Our column | Required | Source | Transform |
|------------|----------|--------|-----------|
| `symbol` | yes | local smallcase / instruments map | Uppercase ticker (not instrument_key) |
| `date` | yes | candle[0] | Parse to calendar **date** in IST (or date part of timestamp); store as `date`, not datetime |
| `close` | yes | candle[4] | float; must be `> 0` |
| `open` | no | candle[1] | float |
| `high` | no | candle[2] | float |
| `low` | no | candle[3] | float |
| `volume` | no | candle[5] | float / int as float |
| `adj_close` | no | **not provided by Upstox** | leave null |
| `currency` | no | constant | `INR` |
| `source` | no | constant | `upstox` |

### 4.3 Corporate actions / adjusted close

**Unsure / not documented on candle endpoints:** whether `close` is split/dividend adjusted.

- Official candle field list has **no** adjusted-close field.
- Treat v0.1 series as **raw exchange OHLC** unless we later validate against another source.
- Document `adj_close=null`, `source=upstox` so NAV math assumptions stay explicit.
- Pipeline already supports `price_field=close` (default).

### 4.4 Suggested raw drop layout (fits existing ingest)

Existing ingest discovers parquet/csv under `data/raw/prices/` ([`ingest_prices.py`](../../src/smallcase_finance/pipeline/ingest_prices.py)).

Suggested:

```text
data/raw/prices/YYYY-MM-DD_upstox/
  prices.parquet   # or per-symbol files; last-wins on (symbol, date)
  README.md        # optional: range, symbol count, token date (no secrets)
```

Columns after transform must match `PRICE_SCHEMA` / dictionary.

---

## 5) Failure modes and recommended retries

### 5.1 HTTP / common API errors

Sources: [Error codes](https://upstox.com/developer/api-documentation/error-codes), endpoint-specific 4XX tables.

| Code / condition | Meaning | Retry? | Action |
|------------------|---------|--------|--------|
| **401** / `UDAPI100050` | Invalid/expired token | no (until new token) | Fail sync with clear message: regenerate token |
| **429** / `UDAPI10005` | Rate limit | **yes** | Exponential backoff + jitter (e.g. 1s, 2s, 4s…); respect 30-min budget |
| **500** / **503** / `UDAPI100500` | Server / maintenance | **yes** | Retry 2–3× with backoff |
| Network timeout / connection error | Transient | **yes** | Retry 2–3× |
| **400** `UDAPI1021` | Bad instrument_key format | no | Fix encoding / key |
| **400** `UDAPI100011` | Unknown instrument_key | no | Skip symbol + WARN |
| **400** `UDAPI1148` (V3) | Date range invalid for unit | no | Shrink window / fix dates |
| **400** `UDAPI1022` | Missing `to_date` | no | Client bug |
| Empty `candles: []` | No data in range / holiday-only / illiquid | no | WARN; treat as missing history for that symbol |
| OAuth `UDAPI100057` | Invalid auth code | no | Restart login |
| `UDAPI100069` / `UDAPI100016` | Bad client credentials | no | Fix env keys |

### 5.2 Symbol-level policy (product binding)

Matches existing incomplete-price policy:

1. Resolve symbol → instrument_key; if fail → **WARN, skip symbol**.
2. Fetch candles; if empty or hard 4xx (invalid key) → **WARN, skip symbol**.
3. On partial history (starts mid-window): keep available bars; downstream NAV/rebalance logic already **renormalizes weights** when a symbol lacks a return that day.
4. Do **not** invent prices; do **not** fail the whole sync for one missing name unless **all** symbols fail.

### 5.3 Retry helper sketch (guidance only)

```
for each symbol:
  try up to N=3:
    GET historical
    if 200 → map & accumulate; break
    if 429 or 5xx or network → sleep backoff; continue
    if 401 → abort entire job (token)
    else → WARN skip symbol; break
```

Idempotent write: merge into parquet on PK `(symbol, date)` last-wins (already how price ingest dedupes).

### 5.4 Token expiry during long jobs

Access token dies at **3:30 AM IST**. For overnight batch jobs:

- Prefer running sync earlier in the day, or
- Detect 401 mid-run, checkpoint progress, require fresh token.

---

## 6) Secrets hygiene (explicit)

| Do | Don't |
|----|-------|
| Put tokens/keys in env / local `.env` (gitignored) | Commit `.env`, tokens, client secrets |
| Ship `.env.example` with empty keys | Log full `Authorization` headers |
| Document required vars in Makefile/README | Paste tokens into notebooks checked into git |
| Rotate token after accidental exposure | Store passwords or broker login in repo |

Instrument CDN downloads and this research doc contain **no** credentials.

---

## 7) Sync flow (implemented; keep research aligned)

Implemented in `integrations/upstox/sync.py` + CLI/`make sync-upstox`:

1. Resolve lookback (`--years` / `--from`/`--to` / `UPSTOX_DEFAULT_YEARS`).
2. Collect symbols from local smallcases under `data/raw/smallcases/*.json` (or `--symbols`).
3. If no token: WARN + sample fallback (`generate_sample_raw`); optional pipeline.
4. Resolve keys via curated map + `upstox_instrument_map.json` (NSE_EQ\|ISIN).
5. For each resolved symbol: historical daily candles (client default: **V2** `.../day/{to}/{from}` on `UPSTOX_API_BASE`).
6. Map candles → prices rows (`source=upstox`, `adj_close=null`); write `data/raw/prices/<date>_upstox/prices.parquet`.
7. Optional `--pipeline` / `make sync-upstox` → curated recompute.
8. On unresolved/empty: WARN + skip symbol; do not invent prices.

**Follow-up:** migrate fetch URL to V3 `days/1` for multi-year without year-chunking (see §3.1).

---

## 8) Open questions / uncertainties

| Topic | Status |
|-------|--------|
| Are daily `close` values split/dividend adjusted? | **Not stated** in official candle docs → treat as unadjusted until verified |
| Does `extended_token` work for V3 historical? | Docs say read-oriented; **verify** before relying on it |
| Exact IST vs exchange calendar edge cases for `date` | Use calendar date of candle timestamp in IST; drop pure holidays (no row) |
| V2 daily “1 year” hard cap behavior when range is longer | Prefer V3; if V2, assume client must chunk (error `UDAPI1148` style / truncated — **confirm in live call**) |
| Sandbox historical parity | Not researched in depth; production endpoints assumed for real OHLC |

---

## 9) Official doc index (cite these)

| Topic | URL |
|-------|-----|
| Auth overview | https://upstox.com/developer/api-documentation/authentication |
| Get token + expiry | https://upstox.com/developer/api-documentation/get-token |
| Request structure | https://upstox.com/developer/api-documentation/request-structure |
| Instruments BOD JSON | https://upstox.com/developer/api-documentation/instruments |
| Instrument search | https://upstox.com/developer/api-documentation/instrument-search |
| Field patterns | https://upstox.com/developer/api-documentation/appendix/field-pattern |
| Historical V2 | https://upstox.com/developer/api-documentation/get-historical-candle-data |
| Historical V3 | https://upstox.com/developer/api-documentation/v3/get-historical-candle-data |
| V3 launch notes | https://upstox.com/developer/api-documentation/announcements/enhanced-historical-candle-data-apis-v3 |
| Intraday V2 | https://upstox.com/developer/api-documentation/get-intra-day-candle-data |
| OHLC quote snapshot | https://upstox.com/developer/api-documentation/get-market-quote-ohlc |
| Rate limits | https://upstox.com/developer/api-documentation/rate-limiting |
| Error codes | https://upstox.com/developer/api-documentation/error-codes |
| Developer apps | https://account.upstox.com/developer/apps |

---

## 10) Mapping cheat-sheet (copy for implementers)

```text
# resolve
trading_symbol "INFY" + segment NSE_EQ  →  instrument_key "NSE_EQ|INE..."

# fetch (V3 daily, 3y)
GET /v3/historical-candle/NSE_EQ%7CINE.../days/1/{to}/{from}
Authorization: Bearer $UPSTOX_ACCESS_TOKEN

# map one candle
[ts, o, h, l, c, v, oi] → {
  symbol, date=date(ts IST), open=o, high=h, low=l, close=c,
  volume=v, adj_close=null, currency="INR", source="upstox"
}
```
