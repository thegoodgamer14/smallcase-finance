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

---

## Sample smallcases (after pipeline)

| id | Notes |
|----|--------|
| `digital-india` | IT/digital basket, quarterly rebalance versions |
| `momentum-quality` | Equal-weight quality names |
