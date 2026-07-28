# Data Pipeline — Raw → Curated

**Owner:** Data Engineer  
**Entrypoint:** `python -m smallcase_finance.pipeline` or `make data`  
**Layout:** [file-layout.md](./file-layout.md) · **Schema:** [data-dictionary.md](../data-dictionary.md)

---

## What it does

1. **Sample generate** (if `data/raw/prices/` is empty): writes synthetic OHLCV + instrument master under dated sample drops.
2. **Ingest** authored smallcase JSON + price/instrument drops.
3. **Quality checks** (null rates, PK uniqueness, weight sums ≈ 1.0, symbol FKs).
4. **Write curated Parquet** (atomic `*.tmp` → rename).
5. **Derived rebuild** (lightweight NAV, metrics windows, ITD contribution).

Idempotent: re-running fully replaces curated tables.

---

## One-command rebuild

From repo root:

```bash
# install package + deps once
pip install -e ".[dev]"
# or: pip install -r requirements.txt && PYTHONPATH=src ...

make data
# equivalent:
python -m smallcase_finance.pipeline
```

### Flags

| Flag | Meaning |
|------|---------|
| `--force-sample` | Overwrite synthetic sample prices/instruments |
| `--skip-sample` | Never call the generator (fail if no raw prices) |
| `--skip-derived` | Source tables only (no NAV/metrics/contribution) |
| `-v` / `--verbose` | Debug logging |

```bash
python -m smallcase_finance.pipeline --force-sample -v
python -m smallcase_finance.pipeline --skip-derived
```

---

## Inputs (raw)

| Path | Required | Notes |
|------|----------|-------|
| `data/raw/smallcases/{id}.json` | yes (for demo) | Validated by `SmallcaseDefinitionFile` |
| `data/raw/prices/{yyyy-mm-dd}_{source}/*.{csv,parquet}` | yes* | *auto-generated if missing |
| `data/raw/instruments/{yyyy-mm-dd}_{source}/*.{json,csv}` | optional | Inferred from prices + defs if absent |

**Sample smallcases shipped:** `digital-india`, `momentum-quality`.

**Sample universe (14 symbols):** RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, HCLTECH, WIPRO, TECHM, LTIM, BHARTIARTL, ASIANPAINT, ITC, SBIN, BAJFINANCE.

Synthetic range: **2023-01-02 → 2025-12-31** (Mon–Fri). Label: `source=sample`. **Not real market data.**

---

## Outputs (curated)

| Table | Path |
|-------|------|
| instruments | `data/curated/instruments/instruments.parquet` |
| prices | `data/curated/prices/prices.parquet` |
| smallcases | `data/curated/smallcases/smallcases.parquet` |
| smallcase_constituents | `data/curated/smallcases/smallcase_constituents.parquet` |
| rebalance_events | `data/curated/rebalances/rebalance_events.parquet` |
| nav_series | `data/curated/nav/nav_series.parquet` |
| metrics_snapshot | `data/curated/metrics/metrics_snapshot.parquet` |
| contribution | `data/curated/metrics/contribution.parquet` |

`holdings_snapshots` is optional and not written by the v0 pipeline.

---

## Quality checks (blocking errors)

- Instruments non-empty; unique `symbol`; non-empty `name`
- Prices non-empty; `close > 0`; unique (`symbol`, `date`)
- Per (`smallcase_id`, `effective_from`): `sum(target_weight) ≈ 1.0` (tol `1e-6`)
- All symbols in prices/constituents exist in instruments
- All `smallcase_id`s in child tables exist in smallcases

**Warnings (non-blocking):** large calendar gaps in prices; constituents missing price history.

---

## Derived policy (pipeline v0)

| Topic | Policy |
|-------|--------|
| Price field | `close` |
| Gap | Exclude symbol with missing return that day; **renormalize** remaining weights; log count of gaps |
| NAV seed | `base_nav` (default 100) on first trading day ≥ `inception_date` |
| Metrics windows | `1M`, `3M`, `6M`, `1Y`, `YTD`, `ITD` as-of last NAV date |
| Risk-free | `DEFAULT_RF` env / config (default `0.0`; product may set `0.06`) |
| Contribution | Simple ITD: `avg_weight * symbol_return` (not full Brinson) |

Backend `calc/` may recompute with richer logic later; these Parquet files make the product demoable offline.

---

## Adding personal data

Full step-by-step (examples, aliases, UI verify): **[how-to-add-data.md](./how-to-add-data.md)**.

1. Drop prices under `data/raw/prices/{yyyy-mm-dd}_{your_source}/` (CSV or Parquet).  
   Required columns: `symbol`, `date`, `close`. Optional: OHLC, `volume`, `adj_close`.
2. Optionally drop instrument master under `data/raw/instruments/{yyyy-mm-dd}_{source}/`.
3. Author or edit `data/raw/smallcases/{smallcase_id}.json` (weights must sum to 1.0).
4. Re-run `make data` / `make pipeline`.

**Rules:** do not mutate old drops in place (except version-controlled smallcase JSON). Pipeline writes only under `data/curated/`.

---

## Module map

```
src/smallcase_finance/pipeline/
  __main__.py          # python -m entry
  run.py               # orchestration + CLI
  generate_sample.py   # synthetic OHLCV + instruments
  ingest_prices.py
  ingest_instruments.py
  ingest_smallcases.py
  quality.py
  derived.py           # NAV / metrics / contribution
  io.py                # atomic parquet write
```

Path constants: `src/smallcase_finance/data_access/paths.py` (`CURATED_FILES`, `DATA_RAW_ROOT`).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: smallcase_finance` | `pip install -e .` or `PYTHONPATH=src` |
| `weights … sum=…` error | Fix JSON weights to sum to 1.0 |
| Empty prices after run | Check `data/raw/prices/`; try `--force-sample` |
| Symbols missing from instruments | Add instrument rows or re-run (pipeline merges inferred symbols) |
| Want clean rebuild | `make clean-curated && make data` |
