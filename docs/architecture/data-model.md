# Logical Data Model — Smallcase Finance v0

Companion to [ADR 001](../decisions/001-data-model.md) and the [data dictionary](../data-dictionary.md).

## Entity-relationship overview

```
instruments 1──* prices
     │
     │ symbol
     ▼
smallcase_constituents *──1 smallcases 1──* nav_series
     │                        │
     │                        ├──* metrics_snapshot
     │                        ├──* contribution
     │                        ├──* rebalance_events
     │                        └──* holdings_snapshots
     └──── (symbol joins to instruments / prices)
```

### Cardinality notes

| Relationship | Cardinality | Join keys |
|--------------|-------------|-----------|
| instruments → prices | 1:N | `symbol` |
| smallcases → constituents | 1:N (versioned) | `smallcase_id` + `effective_from` |
| constituents → instruments | N:1 | `symbol` |
| smallcases → nav_series | 1:N | `smallcase_id`, `date` |
| smallcases → metrics_snapshot | 1:N | `smallcase_id`, `as_of`, `window` |
| smallcases → contribution | 1:N | `smallcase_id`, period bounds, `symbol` |
| smallcases → rebalance_events | 1:N | `smallcase_id`, `rebalance_date` |
| smallcases → holdings_snapshots | 1:N | `smallcase_id`, `as_of`, `symbol` |

## Entity descriptions

### 1. `instruments` (source)

Universe of tradable names used in smallcases and price history.

- Grain: one row per `symbol`
- Key fields: `symbol`, `name`, `sector`, `exchange`, `currency`, `is_active`

### 2. `prices` (source)

Daily market prices. Close is mandatory for NAV; OHLC optional.

- Grain: one row per (`symbol`, `date`)
- Key fields: `symbol`, `date`, `close`, optional `open`/`high`/`low`/`volume`, `adj_close`
- Convention: prefer split/dividend-adjusted close in `close` or populate `adj_close` and document which NAV uses

### 3. `smallcases` (source)

Thematic portfolio definition (the “product”).

- Grain: one row per `smallcase_id`
- Key fields: `smallcase_id`, `name`, `theme`, `methodology`, `rebalance_rule`, `base_nav`, `currency`, `inception_date`, `created_at`, `notes`

**Methodology / rebalance_rule** are free-text or short enums for v0, e.g.:

- methodology: `equal_weight`, `market_cap_weight`, `custom_weights`, `factor_score`
- rebalance_rule: `none`, `monthly`, `quarterly`, `threshold_5pct`, `manual`

### 4. `smallcase_constituents` (source, versioned)

Target composition. **This is the critical versioned table.**

- Grain: one row per (`smallcase_id`, `symbol`, `effective_from`)
- Key fields: `target_weight`, optional `effective_to` (nullable = open-ended)
- Rule: for a given `smallcase_id` + `effective_from`, weights across symbols should sum to 1.0
- Historical lookup: on date `d`, use the version with max `effective_from` where `effective_from <= d` (and `effective_to` is null or `>= d`)

### 5. `rebalance_events` (source / pipeline log)

Explicit record of weight changes.

- Grain: one row per (`smallcase_id`, `rebalance_date`) [or + `event_id` if multiple same day]
- Key fields: `reason`, `from_effective_from`, `to_effective_from`, optional notes
- Links conceptually to two constituent versions; does not duplicate weight rows

### 6. `holdings_snapshots` (optional source or derived)

Actual or reconstructed positions at a point in time.

- Grain: (`smallcase_id`, `as_of`, `symbol`)
- Key fields: `weight`, `shares` (optional), `market_value` (optional), `source` (`target` | `broker` | `reconstructed`)
- v0: can be omitted; UI “composition” can read latest constituents instead

### 7. `nav_series` (derived)

Daily portfolio value index.

- Grain: (`smallcase_id`, `date`)
- Key fields: `nav`, `daily_return`, optional `cum_return`
- Build rule (conceptual):
  1. Determine active weights for date `d` from constituents.
  2. Portfolio return ≈ Σ weight_i × symbol_return_i (using prior close → close).
  3. `nav_d = nav_{d-1} × (1 + daily_return_d)`; seed `base_nav` on first date.
- Missing price: document pipeline policy (forward-fill last close, or drop day, or exclude symbol and renormalize). Default recommendation: **exclude symbol with missing return that day and renormalize remaining weights**; log gaps.

### 8. `metrics_snapshot` (derived)

Point-in-time performance & risk over a defined window.

- Grain: (`smallcase_id`, `as_of`, `window`) where `window` ∈ `1M|3M|6M|1Y|YTD|ITD|custom`
- Key fields: `cagr`, `total_return`, `volatility` (ann.), `max_drawdown`, `sharpe`, optional `sortino`, `calmar`, `start_date`, `end_date`, `n_obs`, `computed_at`
- Risk-free rate: store `rf_rate` used (constant annual, e.g. 0.06) for Sharpe reproducibility

### 9. `contribution` (derived)

Simple return attribution by symbol for a period.

- Grain: (`smallcase_id`, `period_start`, `period_end`, `symbol`)
- Key fields: `avg_weight`, `symbol_return`, `contribution` (≈ avg_weight × symbol_return), optional `weight_start`, `weight_end`
- Not full multi-period linking; good enough for v0 “what drove returns?”
- Residual row optional: `symbol = '_RESIDUAL'` for interaction / rebalance effects if needed later

## Derived rebuild graph

```
instruments + prices + smallcases + smallcase_constituents
        │
        ▼
   nav_series ──────────────────────────────┐
        │                                   │
        ▼                                   ▼
 metrics_snapshot                    contribution
        ▲
 rebalance_events (informational; not required for NAV if constituents versioned)
```

All derived tables are **idempotent rebuilds** from source Parquet. Pipelines should support `rebuild --smallcase X` and `rebuild --all`.

## Physical layout

Exact paths (binding): [docs/data/file-layout.md](../data/file-layout.md).

```
data/
  raw/
    smallcases/{smallcase_id}.json   # authored definitions (SmallcaseDefinitionFile)
    prices/{yyyy-mm-dd}_{source}/    # bulk price drops
    instruments|holdings/...         # optional drops
  curated/
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

### DuckDB usage (suggested, not mandatory)

```sql
-- example views; catalog path optional e.g. data/curated/smallcase.duckdb
CREATE OR REPLACE VIEW instruments AS
  SELECT * FROM read_parquet('data/curated/instruments/instruments.parquet');

CREATE OR REPLACE VIEW prices AS
  SELECT * FROM read_parquet('data/curated/prices/prices.parquet');

-- ... same pattern for other tables
```

Backend and notebooks should prefer relative paths from repo root.

## Contracts (what each consumer can assume)

| Consumer | May read | May write | Must not |
|----------|----------|-----------|----------|
| Data Engineer | raw + curated | curated (all) | mutate raw in place |
| Data Analyst | curated | notebooks outputs only (not curated SoT) | invent schema fields without ADR |
| Backend | curated / DuckDB | trigger rebuild jobs only | treat derived as unrebuildable |
| Frontend | API only | — | touch Parquet paths |

## Open extensions (post-v0)

- `benchmarks` + benchmark price/NAV series for relative performance
- Corporate actions table if unadjusted prices are used
- Multi-exchange primary listing / dual-listed symbols
- Factor scores and methodology parameters as structured JSON
- User notes / tags as a thin metadata table

## Schema stubs

Curated-table / raw-definition models (Pydantic, binding):

`src/smallcase_finance/schemas/models.py`

Re-export path (stable): `src/smallcase_finance/models/entities.py`

API request/response DTOs are separate under `src/smallcase_finance/schemas/` sibling modules (Backend-owned): `smallcase.py`, `nav.py`, etc.

Use domain models for ingest validation; Parquet column names must match field names in the [data dictionary](../data-dictionary.md).
