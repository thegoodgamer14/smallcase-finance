# Upstox historical prices

Optional live market-data path for **daily OHLCV** used by the local pipeline and backtests.

Sample synthetic prices remain the default when no token is configured.

## What this does / does not do

| Does | Does not |
|------|----------|
| Fetch daily candles for NSE equities | Log into Smallcase.com |
| Write `data/raw/prices/{date}_upstox/` | Place orders / trade |
| Support **custom lookback** (`--years` or `--from`/`--to`) | Auto-import your Smallcase.com baskets |
| Fall back to sample data without a token | Store secrets in git |

Your smallcases stay as local JSON under `data/raw/smallcases/`. Upstox only supplies **prices**.

## Setup

1. Create an Upstox developer app and obtain an **access token** (Bearer).  
   Official candle docs: [Historical Candle Data](https://upstox.com/developer/api-documentation/get-historical-candle-data/).
2. Copy env template and set the token (never commit `.env`):

```bash
cp .env.example .env
# edit .env → UPSTOX_ACCESS_TOKEN=...
export $(grep -v '^#' .env | xargs)   # or use direnv / your shell
```

3. Sync + rebuild curated data:

```bash
# Default lookback (UPSTOX_DEFAULT_YEARS, usually 3)
make sync-upstox

# Custom years
make sync-upstox YEARS=5

# Custom inclusive calendar range
make sync-upstox FROM=2020-01-01 TO=2025-12-31

# Specific symbols only
make sync-upstox SYMBOLS=TCS,INFY YEARS=2
```

Equivalent CLI:

```bash
python -m smallcase_finance.integrations.upstox --years 5 --pipeline
python -m smallcase_finance.integrations.upstox --from 2021-06-01 --to 2024-06-01 --pipeline
python -m smallcase_finance.integrations.upstox --symbols TCS,RELIANCE --years 3
```

Without credentials the CLI **prints a clear warning**, ensures sample raw prices exist, and (with `--pipeline` / `make sync-upstox`) still rebuilds curated data so the demo keeps working.

## Instrument keys

Upstox needs `instrument_key` values like `NSE_EQ|INE467B01029`.  
We ship a curated map for sample / large-cap symbols in code. Override or extend:

```
data/raw/instruments/upstox_instrument_map.json
```

```json
{
  "MYSTOCK": "NSE_EQ|INE0...."
}
```

Unknown symbols are **skipped with warnings**; remaining symbols still sync (weights renormalize later in NAV construction when prices are missing).

## API (local)

| Endpoint | Purpose |
|----------|---------|
| `GET /integrations/upstox/status` | `{ configured: bool, default_years, hint }` — never returns the secret |
| `GET /integrations/upstox/lookback-preview` | Resolve `--years` / from / to without fetching |
| `POST /integrations/upstox/sync` | Disabled unless `UPSTOX_SYNC_ENABLED=1` |

Prefer the **CLI** for sync so tokens stay in your shell environment.

## Evaluating custom performance windows

The metrics API already accepts custom ranges (independent of how prices were fetched):

```bash
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?start=2023-06-01&end=2024-06-01' | jq
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/performance?start=2023-06-01&end=2024-06-01' | jq
```

The web UI exposes preset chips (1M … SI) plus a **custom from/to** control.

## Future one-click connect

Roadmap (not in this slice): browser OAuth for Upstox, “Sync prices” button with secure local token storage, optional multi-broker adapters. This release is intentionally **env + CLI first**.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Auth failed | Token expired / wrong header; regenerate access token |
| Symbol skipped | Add ISIN key to `upstox_instrument_map.json` |
| Empty bars | Date range outside listing period; try a shorter window |
| Still on sample | Confirm env is exported in the same shell that runs sync |
