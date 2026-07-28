# API Reference (v0)

Local-first FastAPI over curated Parquet. Full architecture: [architecture/backend.md](./architecture/backend.md).

## Run

```bash
# from repo root
pip install -e ".[dev]"   # or: make install
make pipeline             # ensure data/curated/*.parquet exist
make api                  # uvicorn on 127.0.0.1:8000
```

- Base URL: `http://127.0.0.1:8000`
- OpenAPI UI: `http://127.0.0.1:8000/docs`
- CORS: `http://localhost:3000` and `http://127.0.0.1:3000` (Next.js)

If curated data is missing, run `make pipeline` (or `python -m smallcase_finance.pipeline`).  
`GET /health` reports `data_reachable: false` when the curated root is missing.

---

## Conventions

| Topic | Rule |
|-------|------|
| Weights / metrics | **Decimals**, not percent (`0.142` = 14.2%) |
| `max_drawdown` | **Negative** fraction (e.g. `-0.27`) |
| Symbols | Uppercase, no exchange suffix (`INFY`) |
| Currency | INR by default |
| Errors | `{ "detail": "..." }` — 404 unknown id, 400 bad range, 503 curated missing |

---

## Endpoints

### Health

```bash
curl -s http://127.0.0.1:8000/health | jq
```

```json
{
  "status": "ok",
  "version": "0.0.1",
  "data_curated_root": ".../data/curated",
  "data_reachable": true
}
```

---

### List smallcases

```bash
curl -s 'http://127.0.0.1:8000/smallcases' | jq
curl -s 'http://127.0.0.1:8000/smallcases?q=digital' | jq
curl -s 'http://127.0.0.1:8000/smallcases?tag=quality' | jq
```

Response: `{ "items": [ { "id", "name", "theme", "currency", "methodology", "rebalance_rule", "inception_date", "as_of", "constituent_count", ... } ] }`

---

### Smallcase detail

```bash
curl -s http://127.0.0.1:8000/smallcases/digital-india | jq
```

---

### Holdings / composition

Target weights as of a date (default: latest NAV as-of).

```bash
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/holdings' | jq
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/holdings?as_of=2023-06-01' | jq
```

Weights are fractions in `[0, 1]`; `weight_sum` ≈ 1.0.

---

### NAV series

```bash
# Full series (optional start/end)
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/nav' | jq '.series | length'
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/nav?start=2024-01-01&end=2024-03-31' | jq

# Latest point only (headers / sparklines)
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/nav?latest_only=true' | jq
```

---

### Performance series (NAV + daily return)

```bash
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/performance' | jq '.series[0:3]'
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/performance?start=2024-01-01&end=2024-01-31' | jq
```

Source: curated `nav_series`. `benchmark_series` is null in v0.

---

### Headline metrics

Windows: `1M` | `3M` | `6M` | `1Y` | `YTD` | `ITD` | `custom`.

```bash
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?window=ITD' | jq
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?window=1Y' | jq '.metrics'
# Custom range → computed via calc.risk from NAV
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/metrics?start=2024-01-01&end=2024-12-31' | jq
```

Named windows prefer curated `metrics_snapshot`; custom / missing windows recompute from NAV.  
`assumptions` always present (`periods_per_year`, `risk_free_rate`, …).

---

### Attribution (contribution)

Simple `avg_weight × symbol_return` from curated `contribution` (not multi-period Brinson).

```bash
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/attribution' | jq
# Exact period match (optional)
curl -s 'http://127.0.0.1:8000/smallcases/digital-india/attribution?period_start=2023-01-02&period_end=2025-12-31' | jq '.items[0:3]'
```

Empty `items` if contribution table missing — UI should degrade gracefully.

---

### Backtest (optional simulation)

Pure in-memory rebalance simulation over curated prices. **Does not write** Parquet.

```bash
curl -s -X POST http://127.0.0.1:8000/backtest \
  -H 'Content-Type: application/json' \
  -d '{
    "smallcase_id": "digital-india",
    "start": "2023-01-02",
    "end": "2024-12-31",
    "rebalance_rule": "quarterly",
    "initial_nav": 100.0
  }' | jq '{params, metrics, n_nav: (.nav_series|length), rebalances: (.rebalance_events|length)}'
```

| Body field | Default | Notes |
|------------|---------|-------|
| `smallcase_id` | required | |
| `start` / `end` | inception / latest prices | Inclusive |
| `rebalance_rule` | smallcase default | `monthly`≈21d, `quarterly`≈63d, `manual`/`none` ≈ never |
| `methodology` | smallcase default | `equal_weight` forces 1/N |
| `initial_nav` | `100` | |
| `threshold` | null | Skip rebalance if one-way turnover below this |

Response includes rebalanced `metrics`, `nav_series`, `rebalance_events`, and optional `buy_hold_metrics` for comparison.

**Not SIP:** this endpoint is weight-NAV rebalance simulation. For monthly SIP + XIRR use **`POST /backtests/sip`** below.

---

## SIP Lab

Monthly **SIP cashflow** path over curated prices. Primary metric is **XIRR** (not v0 weight-NAV total return).

| Rule | Detail |
|------|--------|
| SIP day | Fixed calendar day-of-month → **next trading day** if market closed |
| Costs | **Zero** MVP (full amount deploys at session close) |
| Prices | Curated Parquet only (Upstox history or labeled **sample** demo) |
| Strategies | File-backed under `config/strategies/*.yaml\|json` |
| Secrets | Never returned |

### List strategies

```bash
curl -s http://127.0.0.1:8000/strategies | jq
```

```json
{
  "items": [
    {
      "id": "example-sip-equity",
      "name": "Example Equity SIP Basket",
      "summary": "Sample custom basket for SIP Lab…",
      "currency": "INR",
      "sip_amount": 5000.0,
      "day_of_month": 5,
      "start_date": "2023-01-01",
      "end_date": null,
      "allocation_mode": "custom_weights",
      "n_constituents": 4,
      "version": "1"
    }
  ]
}
```

### Strategy detail

```bash
curl -s http://127.0.0.1:8000/strategies/example-sip-equity | jq
```

Full validated config: `basket`, `sip`, `costs`, `allocation_mode`, `price_field`, etc.  
Unknown id → **404**. Invalid file content → **400**.

### Run SIP backtest

```bash
# File-backed strategy + optional overrides
curl -s -X POST http://127.0.0.1:8000/backtests/sip \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy_id": "example-sip-equity",
    "amount": 10000,
    "day_of_month": 5,
    "start": "2023-01-01",
    "end": "2023-12-31"
  }' | jq '{strategy_id, xirr, total_invested, final_value, max_drawdown, data_source, n_sips, warnings}'
```

| Body field | Required | Notes |
|------------|----------|-------|
| `strategy_id` | one of id / inline | Load `config/strategies/{id}.yaml` |
| `strategy` | one of id / inline | Full StrategyConfig-compatible object |
| `amount` | no | Override monthly SIP amount (`> 0`) |
| `day_of_month` | no | Override calendar day **1–28** |
| `start` / `end` | no | Override schedule bounds (inclusive) |
| `as_of` | no | Terminal valuation date override |

**Response (key fields):**

| Field | Meaning |
|-------|---------|
| `xirr` | Primary annualized rate (decimal); may be null if undefined |
| `total_invested` | Sum of contributions |
| `final_value` | Terminal portfolio market value |
| `max_drawdown` | Negative fraction on MV path |
| `series` | Session MV path (`date`, `market_value`, `total_invested_to_date`, `has_sip`) |
| `cashflows` | Signed CF rows (`amount < 0` contribution, `> 0` terminal) |
| `data_source` | `upstox` \| `sample` \| `fixture` \| `mixed` \| `unknown` |
| `assumptions` | Day rule, zero costs, price field, XIRR day count |
| `warnings` | Missing prices, schedule skips, demo labels, etc. |

```json
{
  "strategy_id": "example-sip-equity",
  "name": "Example Equity SIP Basket",
  "xirr": 0.12,
  "total_invested": 60000.0,
  "final_value": 65000.0,
  "max_drawdown": -0.08,
  "n_sips": 12,
  "series": [{"date": "2023-01-05", "market_value": 10000.0, "total_invested_to_date": 10000.0, "has_sip": true}],
  "cashflows": [
    {"date": "2023-01-05", "amount": -10000.0, "kind": "contribution"},
    {"date": "2023-12-29", "amount": 65000.0, "kind": "terminal"}
  ],
  "data_source": "sample",
  "assumptions": {
    "primary_metric": "xirr",
    "sip_day_rule": "fixed calendar day-of-month → next trading day if market closed",
    "costs": "zero",
    "costs_zero": true,
    "price_field": "close",
    "xirr_day_count": "ACT/365.25",
    "fractional_units": true,
    "currency": "INR",
    "rebalance_mode": "none",
    "not_v0_rebalance": true
  },
  "warnings": ["data_source=sample (demo — not real market SIP claims)"]
}
```

| Status | When |
|--------|------|
| **200** | Run completed (check `data_source` / `warnings` for demo labels) |
| **400** | Invalid config, bad date range, no usable prices for symbols |
| **404** | Unknown `strategy_id` |
| **503** | Curated price table missing — run `make pipeline` |

Inline strategy example (no file):

```bash
curl -s -X POST http://127.0.0.1:8000/backtests/sip \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy": {
      "strategy_id": "inline-demo",
      "name": "Inline Demo",
      "basket": {
        "kind": "inline",
        "constituents": [
          {"symbol": "TCS", "target_weight": 0.5},
          {"symbol": "INFY", "target_weight": 0.5}
        ]
      },
      "sip": {
        "amount": 5000,
        "day_of_month": 5,
        "start_date": "2023-01-01",
        "end_date": "2023-06-30"
      }
    }
  }' | jq '{xirr, total_invested, final_value, data_source}'
```

---

## Frontend mapping (quick)

| UI need | Endpoint |
|---------|----------|
| Smallcase switcher | `GET /smallcases` |
| KPI cards | `GET /smallcases/{id}/metrics?window=` |
| Equity curve | `GET /smallcases/{id}/performance` |
| Current NAV | `GET /smallcases/{id}/nav?latest_only=true` |
| Holdings table | `GET /smallcases/{id}/holdings` |
| Top contributors | `GET /smallcases/{id}/attribution` |
| Period grid | call metrics per window (`1M`…`ITD`) |
| Rebalance sandbox | `POST /backtest` |
| SIP strategy picker | `GET /strategies` |
| SIP strategy detail | `GET /strategies/{id}` |
| SIP Lab run (XIRR) | `POST /backtests/sip` |

---

## Sample smallcases (after pipeline)

| id | Notes |
|----|--------|
| `digital-india` | IT/digital basket, quarterly rebalance versions |
| `momentum-quality` | Equal-weight quality names |
