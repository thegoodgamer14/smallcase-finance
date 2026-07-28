# Data File Layout — v0

**Status:** binding for Data Engineer / Backend  
**Companion:** [data-dictionary.md](../data-dictionary.md), [pipeline.md](./pipeline.md), [how-to-add-data.md](./how-to-add-data.md), [ADR 001](../decisions/001-data-model.md)  
**Path constants:** `src/smallcase_finance/data_access/paths.py` (`CURATED_FILES`)

All paths relative to **repo root** unless noted.

---

## Tree (exact)

```
data/
  README.md
  raw/                                      # immutable source drops — never edit in place
    .gitkeep
    smallcases/                             # human-authored portfolio definitions
      {smallcase_id}.json                   # e.g. digital-india.json
    prices/                                 # optional personal / vendor price drops
      {yyyy-mm-dd}_{source}/                # e.g. 2026-07-28_yahoo/
        *.csv | *.parquet | *.xlsx
    instruments/                            # optional instrument master drops
      {yyyy-mm-dd}_{source}/
        *.csv | *.json
    holdings/                               # optional broker holdings exports
      {yyyy-mm-dd}_{source}/
        *.csv | *.xlsx
    sample/                                 # optional generator seed / fixtures
      ...

  curated/                                  # clean analytical SoT — pipeline writes only
    .gitkeep
    instruments/
      instruments.parquet
    prices/
      prices.parquet
    smallcases/
      smallcases.parquet
      smallcase_constituents.parquet
    rebalances/
      rebalance_events.parquet
    holdings/
      holdings_snapshots.parquet            # optional; may be absent
    nav/
      nav_series.parquet                    # derived
    metrics/
      metrics_snapshot.parquet              # derived
      contribution.parquet                  # derived
```

**Not used in v0:** Hive partitions (`year=2024/...`), DuckDB catalog as canonical store, per-symbol price files.

---

## Curated table → path map

| Logical table | Absolute-from-repo path | Kind |
|---------------|-------------------------|------|
| `instruments` | `data/curated/instruments/instruments.parquet` | S |
| `prices` | `data/curated/prices/prices.parquet` | S |
| `smallcases` | `data/curated/smallcases/smallcases.parquet` | S |
| `smallcase_constituents` | `data/curated/smallcases/smallcase_constituents.parquet` | S |
| `rebalance_events` | `data/curated/rebalances/rebalance_events.parquet` | S |
| `holdings_snapshots` | `data/curated/holdings/holdings_snapshots.parquet` | S/D optional |
| `nav_series` | `data/curated/nav/nav_series.parquet` | D |
| `metrics_snapshot` | `data/curated/metrics/metrics_snapshot.parquet` | D |
| `contribution` | `data/curated/metrics/contribution.parquet` | D |

`paths.CURATED_FILES` keys **must** match the logical table names above.

---

## Raw conventions

| Drop type | Path pattern | Notes |
|-----------|--------------|-------|
| Smallcase definition | `data/raw/smallcases/{smallcase_id}.json` | One file per smallcase; schema = `SmallcaseDefinitionFile` |
| Price bulk | `data/raw/prices/{yyyy-mm-dd}_{source}/` | Keep original filenames; pipeline maps columns |
| Instrument master | `data/raw/instruments/{yyyy-mm-dd}_{source}/` | Optional if instruments inferred from prices + defs |
| Holdings | `data/raw/holdings/{yyyy-mm-dd}_{source}/` | Optional broker export |
| Sample seed | `data/raw/sample/` | Generator inputs only; label curated `source=sample` |

**Rules**

1. Never overwrite or mutate files under `data/raw/` after drop; new drop = new dated folder (except smallcase JSON edits which are version-controlled authoring files).
2. Pipelines write **only** under `data/curated/`.
3. Derived tables may be deleted and fully rebuilt.
4. Prefer atomic write: write `*.parquet.tmp` then rename to final name.
5. Empty curated: absent file **or** 0-row Parquet with dictionary schema — both mean “no data”.

---

## Expected pipeline outputs (minimum for demo)

After sample generator + smallcase ingest:

```
data/curated/instruments/instruments.parquet
data/curated/prices/prices.parquet
data/curated/smallcases/smallcases.parquet
data/curated/smallcases/smallcase_constituents.parquet
data/curated/rebalances/rebalance_events.parquet   # if events present in JSON
data/curated/nav/nav_series.parquet
data/curated/metrics/metrics_snapshot.parquet
data/curated/metrics/contribution.parquet
```

`holdings_snapshots.parquet` is optional for v0 demo.

---

## Env overrides

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATA_CURATED_ROOT` | `<repo>/data/curated` | Root for all curated Parquet reads |

Raw root is fixed at `<repo>/data/raw` for v0 (no env) unless Data Engineer adds `DATA_RAW_ROOT` later — document if added.

---

## DuckDB read pattern (reference)

```sql
SELECT * FROM read_parquet('data/curated/prices/prices.parquet');
SELECT * FROM read_parquet('data/curated/smallcases/smallcase_constituents.parquet');
```

Prefer repo-relative paths from process CWD = repo root.
