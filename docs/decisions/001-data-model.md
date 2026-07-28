# ADR 001 — v0 Data Model & Storage

**Status:** Accepted  
**Date:** 2026-07-28  
**Owner:** Data Architect  
**Related:** `docs/architecture/data-model.md`, `docs/data-dictionary.md`

## Context

We need a local-first data foundation for a personal Smallcase-style tool. The product must answer:

1. What is in a smallcase, and how are weights defined over time?
2. How has the smallcase performed (NAV, returns)?
3. What are risk metrics (volatility, max drawdown, Sharpe)?
4. How did each constituent contribute to returns?
5. When did rebalances happen, and what changed?

There is no production warehouse, no multi-user auth, and no live broker feed. Data will start as CSV/Excel drops under `data/raw/`. Analysis will use Python (Polars/Pandas) + DuckDB, with a FastAPI backend and Next.js UI later.

## Decision

### Storage

| Layer | Format | Role |
|-------|--------|------|
| `data/raw/` | As-received (CSV, XLSX, JSON, zip) | Immutable source drops; never mutate |
| `data/curated/` | Parquet (primary), optional small JSON sidecars for metadata | Clean analytical tables; source of truth for app/pipelines |
| Query | DuckDB (file or in-process) over Parquet | Ad-hoc SQL, joins, metrics; no separate warehouse server |

**Why Parquet + DuckDB:** columnar, typed, portable, zero-ops for a personal project; DuckDB reads Parquet directly; easy to re-partition later.

**Not chosen for v0:** PostgreSQL (ops overhead), pure SQLite for all fact tables (worse for time-series scans), cloud lakehouse.

### Source of truth vs derived

| Entity | Kind | Notes |
|--------|------|-------|
| `instruments` | **Source** | Master list of tickers we care about |
| `prices` | **Source** | Daily OHLCV (close required); from market data drop or API export |
| `smallcases` | **Source** | Portfolio definition (name, theme, methodology, rebalance rule) |
| `smallcase_constituents` | **Source** | Target weights, **versioned by `effective_from`** |
| `rebalance_events` | **Source** (or pipeline-emitted log) | Explicit rebalance moments + reason |
| `holdings_snapshots` | **Source optional / derived** | Actual positions if user has broker holdings; else reconstructed from weights × prices |
| `nav_series` | **Derived** | Daily NAV + daily return from constituents + prices |
| `metrics_snapshot` | **Derived** | Point-in-time risk/return stats over a window |
| `contribution` | **Derived** | Per-symbol return attribution for a period |

### Versioning principle

Anything that can change (especially weights) is timestamped:

- Constituents use `effective_from` (date) so historical NAV can use the weight set in force that day.
- No hard deletes of historical weight rows; supersede by inserting a new version.
- Derived tables may be fully rebuilt; they carry `computed_at` for lineage.

### Identity & conventions

- **Symbols:** uppercase strings as used on the exchange feed (e.g. `RELIANCE`, `TCS`). Optional `exchange` (`NSE`/`BSE`) on instruments; prices grain is `(symbol, date)` for v0 (single primary listing).
- **Currency:** INR assumed; store `currency` on smallcases and prices for future multi-currency.
- **Dates:** calendar `date` (ISO `YYYY-MM-DD`), not timestamps, for market-day grains.
- **Weights:** fraction of portfolio, sum to ~1.0 per smallcase version (tolerance 1e-6). Not percentages.
- **NAV base:** start at `100.0` on first valid date unless overridden.
- **IDs:** `smallcase_id` is a stable slug (`momentum-quality`) or UUID string; prefer readable slugs for personal use.

### File layout under `data/`

Binding detail: [docs/data/file-layout.md](../data/file-layout.md).

```
data/
  raw/                          # immutable drops + authored defs
    smallcases/{id}.json
    prices/{yyyy-mm-dd}_{source}/
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

Partitioning by year/symbol is deferred until files get large; single Parquet files are fine for v0.

### Contracts for other agents

- **Data Engineer:** ingest raw → validate against dictionary / `smallcase_finance.schemas.models` → write curated Parquet; rebuild derived tables idempotently.
- **Data Analyst:** read only `data/curated/` (+ DuckDB views); never write raw.
- **Backend:** serve curated tables / DuckDB queries; treat derived tables as cache that can be regenerated. Map rows to API DTOs in `schemas/` sibling modules.
- **Frontend:** consume API DTOs shaped from these entities (composition, NAV chart, metrics cards).

Domain row models: `src/smallcase_finance/schemas/models.py` (re-export: `models/entities.py`).

## Consequences

**Positive**

- Clear SoT vs derived boundary → reproducible rebuilds.
- Weight versioning enables correct historical NAV and rebalance impact analysis.
- Parquet layout is notebook- and API-friendly without infra.

**Trade-offs / accepted limits (v0)**

- No corporate-actions engine beyond optional adjusted close in `prices`.
- No multi-currency FX tables.
- Contribution is period-based (not full Brinson multi-level).
- Holdings from broker are optional; model supports them but NAV can run on target weights alone.
- DuckDB catalog file (if used) is disposable; Parquet is canonical.

## Alternatives considered

1. **SQLite-only** — simpler single file, but weaker for large price history scans and multi-table analytics. Rejected as primary; may still use SQLite for app prefs later.
2. **Normalized Postgres from day one** — overkill for personal local-first v0.
3. **Store only latest weights** — cannot backtest or explain past performance correctly. Rejected.

## Follow-ups (out of scope for this ADR)

- Ingestion pipeline implementation (Data Engineer).
- Exact NAV methodology code (price gaps, missing symbols, rebalance day conventions).
- Benchmark series table (can add `benchmarks` + `benchmark_prices` when needed).
