# Upstox — sole historical market-data provider

**Status:** Binding product contract (SIP Lab / Basket Backtest Engine)  
**Audience:** Founder, backend, data engineer  
**Code:** [`src/smallcase_finance/integrations/upstox/`](../../src/smallcase_finance/integrations/upstox/)  
**Deep research notes:** [`upstox-research.md`](upstox-research.md)  
**ADR:** [`docs/decisions/003-upstox-price-source.md`](../decisions/003-upstox-price-source.md)

---

## Product policy (read this first)

| Rule | Detail |
|------|--------|
| **Sole historical source** | Equity/ETF **OHLCV** for backtests and SIP Lab comes **only** from the **Upstox API**. |
| **No alternate providers** | **No** yfinance, **no** NSE bhavcopy, **no** Fyers, **no** paid multi-provider sprawl in this product version. |
| **Without a token** | App runs on **sample / synthetic** prices under `data/raw/prices/*_sample/` for **demo only**. Not for real performance claims. |
| **What Upstox is used for** | Historical daily candles → raw price drops → pipeline → curated Parquet. |
| **What Upstox is not used for** | Live trading, order placement, Coin / mutual funds, F&O, Smallcase.com basket import. |
| **Secrets** | Repo is **public**. **Never commit** access tokens, API secrets, or filled `.env` files. |

Smallcase **definitions** stay as local JSON under `data/raw/smallcases/`. Upstox supplies **prices only**.

---

## 1) Developer portal setup

Official docs:

- [Authentication](https://upstox.com/developer/api-documentation/authentication)
- [Get Token](https://upstox.com/developer/api-documentation/get-token)
- [Developer Apps](https://account.upstox.com/developer/apps)

### 1.1 Create an app

1. Sign in at [Upstox Developer Apps](https://account.upstox.com/developer/apps).
2. Create an application.
3. Note the credentials Upstox issues:

| Upstox portal name | OAuth name | Role |
|--------------------|------------|------|
| **API Key** | `client_id` | Public app id (authorize URL + token exchange) |
| **API Secret** | `client_secret` | Server-side only; token exchange |
| **Redirect URI** | `redirect_uri` | Must match exactly between app config and token request |

There is no separate “Client ID” product field beyond the **API Key** (`client_id`).

### 1.2 Obtain an access token (Bearer)

Upstox uses **OAuth 2.0 authorization code flow**. Your app never handles the user’s Upstox password.

#### Option A — Manual (recommended for this project)

Best for personal CLI / `make sync-upstox`:

1. Open [Developer Apps](https://account.upstox.com/developer/apps) → your app.
2. Click **Generate** to create an access token.
3. Copy the token into local env as `UPSTOX_ACCESS_TOKEN` (see §2).

No OAuth plumbing required.

#### Option B — Authorization code flow (optional; free HTTPS on Vercel)

For a public redirect without buying a domain, deploy the **Next.js app** free on
Vercel Hobby ([docs/deploy/vercel.md](../deploy/vercel.md)). Register:

```text
https://<your-project>.vercel.app/callback/upstox
```

`apps/web` implements `GET /callback/upstox` (exchanges `code` → shows access token once for copy into **local** `.env`). Full FastAPI stays local on free tier.

1. Redirect user to:
   ```text
   https://api.upstox.com/v2/login/authorization/dialog
     ?response_type=code
     &client_id=<API_KEY>
     &redirect_uri=<REDIRECT_URI>
     &state=<optional>
   ```
2. Callback: `?code=...&state=...` (`code` is **single-use**).
3. Exchange on your server (or via `/callback/upstox`):
   ```http
   POST https://api.upstox.com/v2/login/authorization/token
   Content-Type: application/x-www-form-urlencoded

   code=...&client_id=...&client_secret=...&redirect_uri=...&grant_type=authorization_code
   ```
4. Response includes `access_token` (and optionally `extended_token` for longer-lived **read** access).
5. Put the token in `UPSTOX_ACCESS_TOKEN` (Render Environment or local `.env`).

#### Option C — Semi-automated (optional notifier webhook)

Access-token request + mobile approval → **POST** to a **notifier webhook** (not the OAuth redirect).  
See [Access Token Request](https://upstox.com/developer/api-documentation/access-token-request) and [Notifier Webhook](https://upstox.com/developer/api-documentation/appendix/notifier-webhook-endpoint/).

| Portal field | URL | When |
|--------------|-----|------|
| **Redirect URI** | `https://smallcase-sip-lab.vercel.app/callback/upstox` | OAuth browser login (`?code=`) |
| **Notifier webhook** | `https://smallcase-sip-lab.vercel.app/webhooks/upstox/notifier` | Optional; token POSTed after Access Token Request approval |
| **Postback URL** | *(leave blank)* | Order/GTT webhooks — not used (no orders) |

**Do not** reuse `/callback/upstox` as the notifier: different method (GET vs POST) and payload.  
**Recommended for this project:** leave notifier blank; use portal **Generate** (Option A).

### 1.3 Token lifetime

From official Get Token docs:

> The `access_token` is valid **until 3:30 AM the following day** (IST), regardless of when it was issued.

Examples:

- Token at 8 PM Tuesday → expires 3:30 AM Wednesday.
- Token at 2:30 AM Wednesday → expires 3:30 AM **that same** Wednesday.

There is **no refresh_token** in the documented response. Re-generate (or re-run OAuth) when expired. Prefer running sync during the day, not across 3:30 AM IST.

### 1.4 Calling authenticated APIs

```http
Authorization: Bearer <access_token>
Accept: application/json
```

Base URL pattern: `https://api.upstox.com/{v2|v3}/...`  
([Request structure](https://upstox.com/developer/api-documentation/request-structure))

---

## 2) Environment variables (this project)

| Env var | Required for live prices? | Secret? | Meaning |
|---------|---------------------------|---------|---------|
| **`UPSTOX_ACCESS_TOKEN`** | **Yes** | **Yes** | Bearer token for historical (and other) APIs. **Primary.** Portal → Generate, or OAuth response `access_token`. |
| `UPSTOX_API_KEY` | OAuth app create / token exchange | Treat as secret | Official Upstox **API Key** = `client_id`. **Not** a Bearer alias — put the access token only in `UPSTOX_ACCESS_TOKEN`. |
| `UPSTOX_API_SECRET` | OAuth token exchange only | **Yes** | Official **API Secret** = `client_secret`. Not used by the sync CLI today. |
| `UPSTOX_REDIRECT_URI` | OAuth only | No | Must match app config (e.g. `http://127.0.0.1:8765/callback`). |
| `UPSTOX_API_BASE` | No | No | Default `https://api.upstox.com/v2` (see §3 for V2 vs V3). |
| `UPSTOX_DEFAULT_YEARS` | No | No | Default lookback when `--years` / `--from` not set. Default **`3`**. |
| `UPSTOX_SYNC_ENABLED` | No | No | Set `1` only for local demos of `POST /integrations/upstox/sync`. Prefer CLI. |

### Local setup

```bash
cp .env.example .env
# edit .env — set UPSTOX_ACCESS_TOKEN only (never commit .env)

# Soft-loaded by config.py via python-dotenv; or export explicitly:
export UPSTOX_ACCESS_TOKEN='...'
```

`.env.example` ships **empty placeholders only**. Real values stay in gitignored `.env` or your shell.

**Instrument master JSON** (BOD files on Upstox CDN) does **not** require auth. Candle endpoints **do**.

---

## 3) Historical candle endpoints

Official docs:

- **V3 (preferred for multi-year daily):** [Historical Candle Data V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data)
- **V2 (legacy; current client default base):** [Historical Candle Data](https://upstox.com/developer/api-documentation/get-historical-candle-data)
- **V3 announcement:** [Enhanced Historical Candle Data APIs V3](https://upstox.com/developer/api-documentation/announcements/enhanced-historical-candle-data-apis-v3)

### 3.1 V3 daily (recommended for SIP / multi-year backtests)

```http
GET https://api.upstox.com/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
Authorization: Bearer {access_token}
Accept: application/json
```

| Path param | Daily backtest value | Notes |
|------------|----------------------|--------|
| `instrument_key` | e.g. `NSE_EQ\|INE002A01018` | URL-encode `\|` → `%7C` |
| `unit` | `days` | Also: `minutes`, `hours`, `weeks`, `months` |
| `interval` | `1` | Only `1` for days/weeks/months |
| `to_date` | inclusive end `YYYY-MM-DD` | Required |
| `from_date` | start `YYYY-MM-DD` | Optional; always pass for explicit range |

Example (daily range):

```text
https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE848E01016/days/1/2026-07-28/2023-07-28
```

#### V3 availability & max range (official)

| Unit | Interval options | History from | Max span per request |
|------|------------------|--------------|----------------------|
| minutes | 1–300 | Jan 2022 | 1 month (≤15m); 1 quarter (>15m) |
| hours | 1–5 | Jan 2022 | 1 quarter |
| **days** | **1** | **Jan 2000** | **1 decade** up to `to_date` |
| weeks | 1 | Jan 2000 | No limit (docs) |
| months | 1 | Jan 2000 | No limit (docs) |

**Implication:** default 3-year lookback = **one V3 daily request per symbol**. No year-chunking.

### 3.2 V2 daily (what the current client calls by default)

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

Current code (`client.py`) builds:

```text
{UPSTOX_API_BASE}/historical-candle/{encoded_key}/day/{to_date}/{from_date}
```

with default `UPSTOX_API_BASE=https://api.upstox.com/v2`.

**If staying on V2 daily for multi-year windows:** paginate in **≤1 year** chunks (walk `to_date` backward), merge, dedupe by date. Prefer migrating fetch to V3 `days/1` for SIP Lab multi-year ranges.

### 3.3 Path order and encoding

- Path order is always **`to_date` then `from_date`** (both V2 and V3).
- `instrument_key` contains `|` → must be **percent-encoded** as `%7C` in the URL path.
- **One** `instrument_key` per request (loop symbols).

### 3.4 Rate limits

Docs: [Rate limiting](https://upstox.com/developer/api-documentation/rate-limiting)

Historical candles are under **Other Standard APIs** (per-user, per-API class):

| Window | Limit |
|--------|-------|
| Per second | **50** |
| Per minute | **500** |
| Per 30 minutes | **2000** |

Exceeding → HTTP **429** / temporary suspension risk. Smallcase-sized universes (~10–50 symbols, 1 req/symbol) are well under limits; still use polite delays and backoff on 429.

### 3.5 Out of scope for multi-year NAV

| API | Why not for SIP history |
|-----|-------------------------|
| Intraday candles | Current session only |
| Market quote OHLC (`/v2/market-quote/ohlc`) | Live/session snapshot, not multi-year history |

---

## 4) `instrument_key` resolution

Upstox candle endpoints do **not** accept bare tickers (`INFY`). They require:

```text
{SEGMENT}|{ISIN_or_token}
```

Examples:

| Symbol | `instrument_key` |
|--------|------------------|
| RELIANCE | `NSE_EQ\|INE002A01018` |
| TCS | `NSE_EQ\|INE467B01029` |
| INFY | `NSE_EQ\|INE009A01021` |

Field pattern: [Field Pattern Appendix](https://upstox.com/developer/api-documentation/appendix/field-pattern).

### 4.1 Our map (shipped + override)

Code: [`instruments.py`](../../src/smallcase_finance/integrations/upstox/instruments.py)

1. **Defaults:** curated NSE equity map (`DEFAULT_NSE_INSTRUMENT_KEYS`) for sample smallcases and common large caps.
2. **Override file** (wins on conflict):

```text
data/raw/instruments/upstox_instrument_map.json
```

```json
{
  "MYSTOCK": "NSE_EQ|INE0...."
}
```

3. **Resolve:** uppercase ticker; strip `.NS` / `.NSE` suffixes; lookup map; missing → **WARN + skip** that symbol.

### 4.2 Building keys from Upstox instruments master (optional)

Docs: [Instruments](https://upstox.com/developer/api-documentation/instruments)

Public CDN (no auth):

| File | URL |
|------|-----|
| Complete | `https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz` |
| NSE | `https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz` |

Match `trading_symbol` → prefer `segment=NSE_EQ` → store `instrument_key`.  
Search API (auth): [Instrument search](https://upstox.com/developer/api-documentation/instrument-search).

---

## 5) Response mapping → our price schema

### 5.1 Upstox candle array (V2 and V3 share shape)

```json
{
  "status": "success",
  "data": {
    "candles": [
      ["2023-10-01T00:00:00+05:30", 53.1, 53.95, 51.6, 52.05, 235519861, 0]
    ]
  }
}
```

| Index | Field |
|-------|--------|
| 0 | timestamp (ISO-8601, usually IST `+05:30`) |
| 1 | open |
| 2 | high |
| 3 | low |
| 4 | close |
| 5 | volume |
| 6 | open interest (0 for cash equities) |

Candles may arrive **newest-first** — client **sorts ascending by date** before write.

### 5.2 Mapping to our `prices` contract

Aligned with [`docs/data-dictionary.md`](../data-dictionary.md) and `sync.candles_to_frame`:

| Our column | Source | Transform |
|------------|--------|-----------|
| `symbol` | local ticker | Uppercase (not instrument_key) |
| `date` | candle[0] | Calendar date (`YYYY-MM-DD` of timestamp) |
| `open` | candle[1] | float or null |
| `high` | candle[2] | float or null |
| `low` | candle[3] | float or null |
| `close` | candle[4] | float (required, `> 0`) |
| `volume` | candle[5] | float or null |
| `adj_close` | — | **null** (Upstox candles have no adjusted close field) |
| `currency` | constant | `INR` |
| `source` | constant | **`upstox`** |

### 5.3 Corporate actions

Official candle docs do **not** state whether `close` is split/dividend adjusted. Treat series as **exchange OHLC**; leave `adj_close=null`. Pipeline default `price_field=close`.

### 5.4 Raw drop layout

```text
data/raw/prices/YYYY-MM-DD_upstox/
  prices.parquet
  manifest.json    # row count, symbols, date min/max — no secrets
```

Then: existing pipeline ingest → `data/curated/prices/prices.parquet`.

---

## 6) CLI and Make targets

### Make (preferred one-liner)

```bash
# Default lookback (UPSTOX_DEFAULT_YEARS, usually 3) + pipeline
make sync-upstox

# Custom years
make sync-upstox YEARS=5

# Custom inclusive calendar range
make sync-upstox FROM=2020-01-01 TO=2025-12-31

# Specific symbols only
make sync-upstox SYMBOLS=TCS,INFY YEARS=2
```

`make sync-upstox` always passes `--pipeline` (raw → curated rebuild).

### Python module

```bash
python -m smallcase_finance.integrations.upstox --years 5 --pipeline
python -m smallcase_finance.integrations.upstox --from 2021-06-01 --to 2024-06-01 --pipeline
python -m smallcase_finance.integrations.upstox --symbols TCS,RELIANCE --years 3
python -m smallcase_finance.integrations.upstox --years 3 --json   # machine-readable SyncResult
python -m smallcase_finance.integrations.upstox --no-sample-fallback  # fail if no token
```

Entry point (also): `smallcase-upstox-sync` from `pyproject.toml`.

### Lookback resolution

| Inputs | Result |
|--------|--------|
| neither | last `UPSTOX_DEFAULT_YEARS` years ending today |
| `--years N` | ~`N * 365.25` days ending at `--to` or today |
| `--from` / `--to` | inclusive custom range (missing side filled from years/default) |

Default symbol set = union of constituents in `data/raw/smallcases/*.json`.

### Without credentials

1. CLI logs a clear warning.
2. Ensures **sample** raw prices exist (`generate_sample_raw`).
3. With `--pipeline` / `make sync-upstox`, still rebuilds curated data so the **demo** works.
4. Result sets `used_sample_fallback=true`.

**No token ⇒ sample data only.** Do not treat sample NAV/XIRR as live market performance.

---

## 7) Local HTTP status endpoints (optional)

| Endpoint | Purpose |
|----------|---------|
| `GET /integrations/upstox/status` | `{ configured, default_years, hint }` — **never** returns the secret |
| `GET /integrations/upstox/lookback-preview` | Resolve years/from/to without fetching |
| `POST /integrations/upstox/sync` | Disabled unless `UPSTOX_SYNC_ENABLED=1` |

Prefer the **CLI** so tokens stay in the shell / local `.env`.

---

## 8) Security checklist

| Do | Don't |
|----|-------|
| Store tokens in gitignored `.env` or shell env | Commit `.env`, tokens, API secrets |
| Ship empty placeholders in `.env.example` | Log full `Authorization` headers |
| Rotate token after accidental exposure | Paste tokens into notebooks committed to git |
| Keep HTTP sync off by default | Enable `UPSTOX_SYNC_ENABLED` on a public host |

Repo is **public** — assume any committed secret is compromised.

---

## 9) Troubleshooting

| Symptom | Check |
|---------|--------|
| Auth failed (401/403) | Token expired at 3:30 AM IST; regenerate; confirm `Authorization: Bearer …` |
| Symbol skipped | Add `NSE_EQ\|ISIN` to `data/raw/instruments/upstox_instrument_map.json` |
| Empty bars | Range before listing; try shorter window; verify instrument_key |
| Still on sample | `UPSTOX_ACCESS_TOKEN` empty or not exported in the shell that runs sync |
| Multi-year sparse on V2 daily | V2 `day` max is ~1 year; use V3 `days/1` or year-chunk |
| Rate limit | Back off on 429; sequential symbol loop is enough for small universes |

---

## 10) Official doc index

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
| Rate limits | https://upstox.com/developer/api-documentation/rate-limiting |
| Error codes | https://upstox.com/developer/api-documentation/error-codes |
| Developer apps | https://account.upstox.com/developer/apps |

---

## 11) Implementer cheat-sheet

```text
# resolve
trading_symbol "INFY" + NSE_EQ  →  instrument_key "NSE_EQ|INE009A01021"

# fetch (V3 daily, multi-year — preferred)
GET /v3/historical-candle/NSE_EQ%7CINE.../days/1/{to}/{from}
Authorization: Bearer $UPSTOX_ACCESS_TOKEN

# fetch (V2 daily — current default client base; ~1y max)
GET /v2/historical-candle/NSE_EQ%7CINE.../day/{to}/{from}

# map one candle
[ts, o, h, l, c, v, oi] → {
  symbol, date=date(ts), open=o, high=h, low=l, close=c,
  volume=v, adj_close=null, currency="INR", source="upstox"
}

# write
data/raw/prices/{today}_upstox/prices.parquet
→ make pipeline / --pipeline
```
