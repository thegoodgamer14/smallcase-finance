# How to Add Personal Data

**Audience:** You, using this tool with your own prices and smallcases  
**Prerequisites:** Package installed (`pip install -e ".[dev]"` or `make install`)  
**Companion docs:** [pipeline.md](./pipeline.md) · [file-layout.md](./file-layout.md) · [data-dictionary.md](../data-dictionary.md)

This guide is the step-by-step path from “I have CSV prices” to “I see my smallcase in the UI.”

---

## Overview

```
your files → data/raw/ → make pipeline → data/curated/*.parquet → API → UI
```

| You provide | Pipeline produces |
|-------------|-------------------|
| Prices (required for real analysis) | `prices.parquet`, `instruments.parquet` |
| Smallcase JSON (required) | `smallcases.parquet`, constituents, rebalances |
| Instrument master (optional) | Merged into instruments; else inferred |

If `data/raw/prices/` has **no** CSV/Parquet files, the pipeline **auto-generates** synthetic sample prices so demos still work. Your personal drop replaces that path once present.

---

## Step 1 — Prepare price files

### Folder convention

```
data/raw/prices/{yyyy-mm-dd}_{source}/
  prices.csv          # or any *.csv / *.parquet
```

Examples:

```
data/raw/prices/2026-07-28_yahoo/
data/raw/prices/2026-03-01_nse/
data/raw/prices/2026-07-28_manual/
```

- `{yyyy-mm-dd}`: date you **dropped** the export (not the market date range).  
- `{source}`: free label (`yahoo`, `nse`, `manual`, …) — becomes the default `source` column if missing.  
- **Do not overwrite** an old drop in place; add a new dated folder.

### Required columns

| Column | Type | Notes |
|--------|------|--------|
| `symbol` | string | Uppercase ticker, **no** exchange suffix (`INFY` not `INFY.NS`) |
| `date` | date | Trading day `YYYY-MM-DD` |
| `close` | float | Must be `> 0` — used for NAV |

### Optional columns

`open`, `high`, `low`, `volume`, `adj_close`, `currency`, `source`

### Column aliases accepted

The ingest step renames common vendor headers:

| Vendor header | Maps to |
|---------------|---------|
| `ticker`, `Symbol` | `symbol` |
| `Date` | `date` |
| `Close`, `Open`, `High`, `Low`, `Volume` | lowercase OHLC/volume |
| `Adj Close`, `adjclose`, `AdjClose` | `adj_close` |

Exchange suffixes `.NS`, `.BO`, `.NSE`, `.BSE` on symbols are stripped automatically.

### Example CSV

```csv
symbol,date,close,open,high,low,volume
TCS,2023-01-02,3200.5,3180,3210,3175,1200000
INFY,2023-01-02,1500.0,1490,1510,1485,900000
TCS,2023-01-03,3215.0,3205,3220,3190,1100000
INFY,2023-01-03,1508.25,1502,1512,1498,880000
```

### Rules

- One row per (`symbol`, `date`). Duplicates across drops: **last file wins**.  
- No row on holidays / non-trading days (do not insert null closes).  
- Missing a symbol on some days is OK; NAV **excludes** that symbol and renormalizes remaining weights.  
- Prefer long history (e.g. multi-year daily) so CAGR / vol / drawdown are meaningful.

---

## Step 2 — Optional instrument master

If omitted, the pipeline **infers** instruments from price symbols + smallcase constituents (minimal `name` = symbol).

To supply display names and sectors:

```
data/raw/instruments/{yyyy-mm-dd}_{source}/instruments.json
```

JSON array (or `{"instruments": [...]}`):

```json
[
  {
    "symbol": "TCS",
    "name": "Tata Consultancy Services",
    "sector": "Information Technology",
    "industry": "IT Services",
    "exchange": "NSE",
    "currency": "INR",
    "is_active": true
  }
]
```

CSV with the same columns also works. See sample:

[`data/raw/instruments/2026-07-28_sample/instruments.json`](../../data/raw/instruments/2026-07-28_sample/instruments.json)

---

## Step 3 — Define (or edit) a smallcase

Path:

```
data/raw/smallcases/{smallcase_id}.json
```

`smallcase_id` must be a lowercase slug matching the filename (e.g. `my-tech.json` → `"smallcase_id": "my-tech"`).

### Template

```json
{
  "smallcase_id": "my-tech",
  "name": "My Tech Basket",
  "theme": "IT",
  "description": "Personal equal-ish IT basket.",
  "methodology": "custom_weights",
  "rebalance_rule": "quarterly",
  "base_nav": 100.0,
  "currency": "INR",
  "inception_date": "2023-01-02",
  "notes": "Personal definition",
  "versions": [
    {
      "effective_from": "2023-01-02",
      "effective_to": null,
      "version_label": "v1",
      "constituents": [
        { "symbol": "TCS", "target_weight": 0.34 },
        { "symbol": "INFY", "target_weight": 0.33 },
        { "symbol": "HCLTECH", "target_weight": 0.33 }
      ]
    }
  ],
  "rebalance_events": []
}
```

### Weight and version rules

1. Per version: `sum(target_weight) ≈ 1.0` (tolerance `1e-6`). Pipeline **fails** if not.  
2. Each `target_weight` must be in `(0, 1]`.  
3. Symbols unique within a version.  
4. Multiple versions: set `effective_from` (and optionally `effective_to`); NAV picks the latest version with `effective_from ≤ date`.  
5. Every constituent symbol should appear in your price history for the period you care about.

### Ship examples

- [`digital-india.json`](../../data/raw/smallcases/digital-india.json) — two versions + rebalance event  
- [`momentum-quality.json`](../../data/raw/smallcases/momentum-quality.json) — single equal-weight version  

Copy one and edit for a fast start.

Full raw JSON contract: [data-dictionary.md § Raw definition](../data-dictionary.md#raw-definition-contract-human-authored-json).

---

## Step 4 — Run the pipeline

From **repo root**:

```bash
make pipeline
# equivalent:
python3 -m smallcase_finance.pipeline
# verbose:
python3 -m smallcase_finance.pipeline -v
```

### Useful flags

| Flag | When to use |
|------|-------------|
| `--skip-sample` | Never generate synthetic prices (fail if no personal prices) |
| `--force-sample` | Overwrite the synthetic sample drop |
| `--skip-derived` | Write source tables only (no NAV/metrics) |
| `-v` | Debug logging |

### Expected curated outputs

```
data/curated/instruments/instruments.parquet
data/curated/prices/prices.parquet
data/curated/smallcases/smallcases.parquet
data/curated/smallcases/smallcase_constituents.parquet
data/curated/rebalances/rebalance_events.parquet
data/curated/nav/nav_series.parquet
data/curated/metrics/metrics_snapshot.parquet
data/curated/metrics/contribution.parquet
```

Clean rebuild:

```bash
make clean-curated && make pipeline
```

---

## Step 5 — Verify

### CLI / API

```bash
make api   # if not already running

curl -s http://127.0.0.1:8000/smallcases | jq '.items[].id'
curl -s "http://127.0.0.1:8000/smallcases/my-tech/metrics?window=ITD" | jq '.metrics'
curl -s "http://127.0.0.1:8000/smallcases/my-tech/holdings" | jq
```

### UI

```bash
make web   # http://localhost:3000
```

Use the **smallcase switcher** in the top bar to select your id. Pages:

| Route | Content |
|-------|---------|
| `/` | Dashboard — KPIs, equity curve, period returns, contributors |
| `/holdings` | Target weights / composition |
| `/performance` | Performance & risk detail |

If the API was already running during the pipeline, **restart it** so file handles see new Parquet.

---

## Using only personal data (no sample)

1. Place your price drop under `data/raw/prices/...`.  
2. Author your smallcase JSON(s). You may leave sample smallcases in place or remove JSON you do not want.  
3. Run with skip-sample if you want to forbid generator fallback:

```bash
python3 -m smallcase_finance.pipeline --skip-sample
```

4. Optional: delete the synthetic sample folders under `data/raw/prices/2026-07-28_sample/` and `data/raw/instruments/2026-07-28_sample/` if you no longer need them (raw is never deleted by `make clean-curated`).

---

## Common failures

| Symptom | Fix |
|---------|-----|
| `weights … sum=…` | Fix JSON so each version sums to 1.0 |
| `ModuleNotFoundError: smallcase_finance` | `pip install -e ".[dev]"` from repo root |
| Empty prices / pipeline fails with no prices | Check drop path; or omit `--skip-sample` so sample can generate |
| Symbol missing from instruments | Add instrument row or re-run (merge infers missing symbols) |
| API 503 / `data_reachable: false` | Run pipeline; check `DATA_CURATED_ROOT` |
| UI cannot reach API | Start `make api`; set `NEXT_PUBLIC_API_URL` if not on 8000 |
| Sparse metrics / weird CAGR | Need enough daily history; check date range and missing closes |
| Wrong currency display | Set `"currency": "INR"` (or other) on smallcase + prices; no FX conversion in v0 |

---

## What not to do

1. **Do not** hand-edit `data/curated/**/*.parquet` — always re-run the pipeline.  
2. **Do not** put live secrets or broker API keys here — v0 is offline files only.  
3. **Do not** expect broker positions to drive the UI unless you build `holdings_snapshots` (optional; not required for v0 target-weight views).  
4. **Do not** use multi-exchange duplicate rows for the same `symbol` — one primary listing per symbol.

---

## Checklist (first personal run)

- [ ] Prices under `data/raw/prices/{date}_{source}/` with `symbol`, `date`, `close`  
- [ ] Symbols uppercase, no `.NS` / `.BO` needed (or stripped by ingest)  
- [ ] Smallcase JSON under `data/raw/smallcases/` with weights summing to 1.0  
- [ ] Constituent symbols covered by prices  
- [ ] `make pipeline` succeeds  
- [ ] `GET /smallcases` lists your id  
- [ ] Dashboard shows NAV and metrics for your smallcase  

When stuck: [pipeline.md](./pipeline.md) troubleshooting table, or OpenAPI at http://127.0.0.1:8000/docs.
