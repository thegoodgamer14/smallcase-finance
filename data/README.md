# Data layout

```
data/
  raw/                         # Immutable source drops / authored definitions
    smallcases/{id}.json       # Human-authored smallcase definitions
    prices/{yyyy-mm-dd}_{src}/ # Optional price bulk drops
    instruments/...            # Optional instrument master drops
    holdings/...               # Optional broker holdings
  curated/                     # Clean Parquet — app & analytics source of truth
    instruments/instruments.parquet
    prices/prices.parquet
    smallcases/smallcases.parquet
    smallcases/smallcase_constituents.parquet
    rebalances/rebalance_events.parquet
    holdings/holdings_snapshots.parquet
    nav/nav_series.parquet
    metrics/metrics_snapshot.parquet
    metrics/contribution.parquet
```

See:

- [docs/data/how-to-add-data.md](../docs/data/how-to-add-data.md) — **step-by-step personal data**
- [docs/data/file-layout.md](../docs/data/file-layout.md) — **exact paths** (binding)
- [docs/data-dictionary.md](../docs/data-dictionary.md) — fields, dtypes, PK/grain
- [docs/data/pipeline.md](../docs/data/pipeline.md) — pipeline runbook
- [docs/architecture/data-model.md](../docs/architecture/data-model.md) — logical model
- [docs/decisions/001-data-model.md](../docs/decisions/001-data-model.md) — ADR
- `src/smallcase_finance/schemas/models.py` — Pydantic contracts

Drop bulk files under `raw/{entity}/{yyyy-mm-dd}_{source}/`.  
Author smallcases under `raw/smallcases/{smallcase_id}.json`.  
Pipelines write only to `curated/`.

## Rebuild curated (one command)

```bash
pip install -e ".[dev]"   # once
make data                 # or: python -m smallcase_finance.pipeline
```

If `raw/prices/` is empty, the pipeline auto-generates a synthetic sample drop.
