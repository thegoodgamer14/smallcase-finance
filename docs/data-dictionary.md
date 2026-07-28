# Data Dictionary — Smallcase Finance v0

**Status:** implementable contract (locked for v0)  
**Owner:** Data Architect  
**Consumers:** Data Engineer (ingest), Backend (read/validate), Analyst (DuckDB/Polars)

Logical model: [architecture/data-model.md](architecture/data-model.md)  
ADR: [decisions/001-data-model.md](decisions/001-data-model.md)  
File paths: [data/file-layout.md](data/file-layout.md)  
Pipeline: [data/pipeline.md](data/pipeline.md) · Personal data: [data/how-to-add-data.md](data/how-to-add-data.md)  
Metrics math: [analytics/metrics-definitions.md](analytics/metrics-definitions.md)  
Pydantic: `src/smallcase_finance/schemas/models.py`

---

## Conventions (binding)

| Convention | Rule |
|------------|------|
| Dates | Calendar `date` ISO `YYYY-MM-DD` — never datetime for market-day grains |
| Timestamps | UTC `datetime` (timezone-aware preferred; store as UTC) for `created_at` / `computed_at` / `updated_at` |
| Symbols | Uppercase ASCII ticker, **no** exchange suffix (`INFY` not `INFY.NS` / `INFY.BO`) |
| IDs | `smallcase_id`: lowercase slug (`digital-india`); stable once published |
| Weights | Float **fraction** in `[0, 1]`; per version `sum(target_weight) ∈ [1 - 1e-6, 1 + 1e-6]` |
| Returns | Decimal fraction (`0.01` = +1%); **not** percent points |
| Nulls | Use null for unknown/optional; **no** sentinels (`-1`, `""`, `NaT` as string) |
| Kind | **S** = source of truth (do not invent in app); **D** = derived (idempotent full rebuild OK) |
| Currency | Default `INR`; store on rows but **no FX conversion in v0** |
| Price for NAV | Use `close` unless pipeline config sets `price_field=adj_close` |
| Parquet | Column names **exact** as below; one file per table path; no Hive partitions in v0 |
| Sort | Write Parquet sorted by primary key columns (ascending) for stable diffs |
| Empty tables | File may be absent **or** zero-row Parquet with correct schema; consumers treat both as empty |

### Logical type → storage dtypes

| Logical | Python | Polars | Pandas (nullable) | Arrow / Parquet |
|---------|--------|--------|-------------------|-----------------|
| string | `str` | `Utf8` | `string` | `utf8` |
| date | `datetime.date` | `Date` | `datetime64[ns]` (date only) or `object` of `date` | `date32` |
| timestamp | `datetime.datetime` | `Datetime("us", "UTC")` | `datetime64[us, UTC]` | `timestamp[us, UTC]` |
| float | `float` | `Float64` | `float64` | `float64` |
| int | `int` | `Int64` | `Int64` | `int64` |
| bool | `bool` | `Boolean` | `boolean` | `bool` |

**Required** columns are non-null in every row. **Optional** may be null.

---

## 1. `instruments` — **S**

| | |
|--|--|
| **Path** | `data/curated/instruments/instruments.parquet` |
| **Grain** | One row per instrument |
| **Primary key** | `symbol` |
| **Sort** | `symbol` ASC |
| **Description** | Master list of equities (or other instruments) referenced by prices and smallcases |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `symbol` | string | yes | — | Ticker id (PK). Uppercase. |
| 2 | `name` | string | yes | — | Display name (e.g. `Reliance Industries`) |
| 3 | `sector` | string | no | null | Sector label (NSE/GICS-like) |
| 4 | `industry` | string | no | null | Finer industry if available |
| 5 | `exchange` | string | no | null | e.g. `NSE`, `BSE` |
| 6 | `currency` | string | no | `INR` | Quote currency |
| 7 | `isin` | string | no | null | ISIN if known |
| 8 | `is_active` | bool | yes | `true` | `false` if delisted / out of universe |
| 9 | `updated_at` | timestamp | no | null | Last metadata refresh (UTC) |

**Checks:** `symbol` unique; non-empty after strip+upper.

---

## 2. `prices` — **S**

| | |
|--|--|
| **Path** | `data/curated/prices/prices.parquet` |
| **Grain** | One trading day per symbol |
| **Primary key** | (`symbol`, `date`) |
| **Sort** | `symbol` ASC, `date` ASC |
| **Description** | Daily market prices for NAV and returns |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `symbol` | string | yes | — | FK → `instruments.symbol` |
| 2 | `date` | date | yes | — | Trading date (row absent on holidays) |
| 3 | `close` | float | yes | — | Closing price used for NAV when `price_field=close`; must be `> 0` |
| 4 | `open` | float | no | null | Open; if present `> 0` |
| 5 | `high` | float | no | null | High; if present `> 0` |
| 6 | `low` | float | no | null | Low; if present `> 0` |
| 7 | `volume` | float | no | null | Shares traded; if present `>= 0` |
| 8 | `adj_close` | float | no | null | Adjusted close; if present `> 0` |
| 9 | `currency` | string | no | `INR` | Quote currency |
| 10 | `source` | string | no | null | e.g. `nse`, `yahoo`, `sample`, `manual` |

**Checks:** PK unique; non-trading days have **no row** (do not insert null close).  
**v0:** one primary listing per `symbol` (no multi-exchange price rows).

---

## 3. `smallcases` — **S**

| | |
|--|--|
| **Path** | `data/curated/smallcases/smallcases.parquet` |
| **Grain** | One portfolio definition |
| **Primary key** | `smallcase_id` |
| **Sort** | `smallcase_id` ASC |
| **Description** | Thematic portfolio definitions |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | Stable slug (PK), lowercase kebab-case |
| 2 | `name` | string | yes | — | Human title |
| 3 | `theme` | string | no | null | Short theme label |
| 4 | `description` | string | no | null | Longer blurb |
| 5 | `methodology` | string | yes | `custom_weights` | See enum below (or free text) |
| 6 | `rebalance_rule` | string | yes | `manual` | See enum below (or free text) |
| 7 | `base_nav` | float | yes | `100.0` | Starting index level; must be `> 0` |
| 8 | `currency` | string | yes | `INR` | Portfolio currency |
| 9 | `inception_date` | date | no | null | First date NAV should exist |
| 10 | `benchmark_id` | string | no | null | Reserved; unused in v0 |
| 11 | `created_at` | timestamp | yes | — | Definition created (UTC) |
| 12 | `updated_at` | timestamp | no | null | Last definition edit (UTC) |
| 13 | `notes` | string | no | null | Free-form |

**Preferred `methodology` values:**  
`equal_weight` | `market_cap_weight` | `custom_weights` | `factor_score`  
(other free-text allowed; pipelines must not fail on unknown strings)

**Preferred `rebalance_rule` values:**  
`none` | `monthly` | `quarterly` | `threshold_5pct` | `manual`

---

## 4. `smallcase_constituents` — **S** (versioned)

| | |
|--|--|
| **Path** | `data/curated/smallcases/smallcase_constituents.parquet` |
| **Grain** | One target weight row per symbol in a version |
| **Primary key** | (`smallcase_id`, `symbol`, `effective_from`) |
| **Sort** | `smallcase_id`, `effective_from`, `symbol` ASC |
| **Description** | Target weights, versioned over time |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → `smallcases.smallcase_id` |
| 2 | `symbol` | string | yes | — | FK → `instruments.symbol` |
| 3 | `target_weight` | float | yes | — | Fraction of portfolio; `0 <= w <= 1` |
| 4 | `effective_from` | date | yes | — | Inclusive start of this weight version |
| 5 | `effective_to` | date | no | null | Inclusive end; null = still active / open |
| 6 | `version_label` | string | no | null | Tag e.g. `2024-Q1`, `v1` |
| 7 | `created_at` | timestamp | no | null | When this row was written (UTC) |

**Integrity rules (pipeline must enforce)**

1. For each (`smallcase_id`, `effective_from`): `sum(target_weight) ≈ 1.0` (tol `1e-6`).
2. Active weights on date `d`: rows with `effective_from <= d` and (`effective_to` is null **or** `effective_to >= d`).  
   Preferred timeline: non-overlapping versions; lookup = max `effective_from` where `effective_from <= d`.
3. Never delete historical versions; supersede by new `effective_from` (optionally set prior `effective_to`).
4. Symbols with `target_weight = 0` should be omitted (not stored).

---

## 5. `rebalance_events` — **S**

| | |
|--|--|
| **Path** | `data/curated/rebalances/rebalance_events.parquet` |
| **Grain** | One rebalance action per smallcase per day |
| **Primary key** | (`smallcase_id`, `rebalance_date`) |
| **Sort** | `smallcase_id`, `rebalance_date` ASC |
| **Description** | Log of rebalance actions (why/when weights changed) |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → `smallcases.smallcase_id` |
| 2 | `rebalance_date` | date | yes | — | Effective rebalance day |
| 3 | `reason` | string | no | null | e.g. `scheduled_quarterly`, `manual`, `threshold_breach` |
| 4 | `from_effective_from` | date | no | null | Prior constituent version key |
| 5 | `to_effective_from` | date | yes | — | New constituent version key (usually = `rebalance_date`) |
| 6 | `notes` | string | no | null | Free-form |
| 7 | `created_at` | timestamp | no | null | UTC |

**Note:** Weights live only in `smallcase_constituents`; this table is the audit trail.

---

## 6. `holdings_snapshots` — **S optional / D**

| | |
|--|--|
| **Path** | `data/curated/holdings/holdings_snapshots.parquet` |
| **Grain** | One position per smallcase, as-of date, symbol |
| **Primary key** | (`smallcase_id`, `as_of`, `symbol`) |
| **Sort** | `smallcase_id`, `as_of`, `symbol` ASC |
| **Description** | Point-in-time positions (broker actuals or reconstructed targets) |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → smallcases |
| 2 | `as_of` | date | yes | — | Snapshot date |
| 3 | `symbol` | string | yes | — | FK → instruments |
| 4 | `weight` | float | yes | — | Portfolio weight; `0 <= w <= 1` |
| 5 | `shares` | float | no | null | Quantity if known |
| 6 | `market_value` | float | no | null | In smallcase currency |
| 7 | `source` | string | yes | `target` | Enum: `target` \| `broker` \| `reconstructed` |

**v0:** Optional. If empty/absent, UI composition uses latest `smallcase_constituents`.

---

## 7. `nav_series` — **D**

| | |
|--|--|
| **Path** | `data/curated/nav/nav_series.parquet` |
| **Grain** | One NAV point per smallcase trading day |
| **Primary key** | (`smallcase_id`, `date`) |
| **Sort** | `smallcase_id`, `date` ASC |
| **Description** | Daily NAV and return series |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → smallcases |
| 2 | `date` | date | yes | — | Trading date |
| 3 | `nav` | float | yes | — | Index level; `> 0`; starts at `base_nav` |
| 4 | `daily_return` | float | yes | — | `nav_t / nav_{t-1} - 1`; **0.0 on first day** |
| 5 | `cum_return` | float | no | null | `nav / base_nav - 1` |
| 6 | `n_constituents` | int | no | null | Symbols with valid weight that day; `>= 0` |
| 7 | `computed_at` | timestamp | yes | — | Rebuild timestamp (UTC) |

**Inputs:** `smallcase_constituents` + `prices` + `smallcases.base_nav`  
**Gap policy (binding):** exclude symbol with missing return that day; renormalize remaining weights; log gaps.  
**Rebuild:** full table replace per smallcase or all — idempotent.

---

## 8. `metrics_snapshot` — **D**

| | |
|--|--|
| **Path** | `data/curated/metrics/metrics_snapshot.parquet` |
| **Grain** | One metrics row per smallcase, as-of date, window label |
| **Primary key** | (`smallcase_id`, `as_of`, `window`) |
| **Sort** | `smallcase_id`, `as_of`, `window` ASC |
| **Description** | Performance and risk metrics for a lookback window |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → smallcases |
| 2 | `as_of` | date | yes | — | End of measurement window |
| 3 | `window` | string | yes | — | Enum: `1M` \| `3M` \| `6M` \| `1Y` \| `YTD` \| `ITD` \| `custom` |
| 4 | `start_date` | date | yes | — | Window start used |
| 5 | `end_date` | date | yes | — | Usually = `as_of` |
| 6 | `n_obs` | int | yes | — | Count of daily return observations; `>= 0` |
| 7 | `total_return` | float | yes | — | Cumulative return over window |
| 8 | `cagr` | float | no | null | Annualized return; null if window too short |
| 9 | `volatility` | float | no | null | Ann. stdev of daily returns (`√252`) |
| 10 | `max_drawdown` | float | no | null | Worst peak-to-trough (**negative** fraction) |
| 11 | `sharpe` | float | no | null | `(cagr - rf_rate) / volatility` when defined |
| 12 | `sortino` | float | no | null | Optional |
| 13 | `calmar` | float | no | null | Optional `cagr / abs(max_drawdown)` |
| 14 | `rf_rate` | float | no | null | Annual risk-free rate used for Sharpe (e.g. `0.06`) |
| 15 | `computed_at` | timestamp | yes | — | Rebuild timestamp (UTC) |

**Inputs:** `nav_series`  
**Trading days/year:** `252` (see `config.PERIODS_PER_YEAR`).

---

## 9. `contribution` — **D**

| | |
|--|--|
| **Path** | `data/curated/metrics/contribution.parquet` |
| **Grain** | One contribution row per symbol in a period |
| **Primary key** | (`smallcase_id`, `period_start`, `period_end`, `symbol`) |
| **Sort** | `smallcase_id`, `period_start`, `period_end`, `symbol` ASC |
| **Description** | Simple per-symbol return contribution for a period |

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `smallcase_id` | string | yes | — | FK → smallcases |
| 2 | `period_start` | date | yes | — | Inclusive |
| 3 | `period_end` | date | yes | — | Inclusive; must be `>= period_start` |
| 4 | `symbol` | string | yes | — | Constituent symbol; reserved `_RESIDUAL` allowed |
| 5 | `avg_weight` | float | yes | — | Average portfolio weight; `0 <= w <= 1` |
| 6 | `weight_start` | float | no | null | Weight at period start |
| 7 | `weight_end` | float | no | null | Weight at period end |
| 8 | `symbol_return` | float | yes | — | Total return of symbol over period |
| 9 | `contribution` | float | yes | — | Approx `avg_weight * symbol_return` |
| 10 | `computed_at` | timestamp | yes | — | Rebuild timestamp (UTC) |

**Inputs:** constituents + prices (and/or daily weights from NAV build).  
**Not** full multi-period Brinson; residual vs portfolio total may be nonzero when weights change mid-period.

---

## Raw definition contract (human-authored JSON)

Authoring format for smallcases before flatten-to-Parquet.  
**Path pattern:** `data/raw/smallcases/{smallcase_id}.json`  
**Schema model:** `SmallcaseDefinitionFile` in `schemas/models.py`  
**Example:** [`data/raw/smallcases/digital-india.json`](../data/raw/smallcases/digital-india.json)

| Top-level field | Type | Required | Maps to curated |
|-----------------|------|----------|-----------------|
| `smallcase_id` | string | yes | `smallcases.smallcase_id` |
| `name` | string | yes | `smallcases.name` |
| `theme` | string | no | `smallcases.theme` |
| `description` | string | no | `smallcases.description` |
| `methodology` | string | yes | `smallcases.methodology` |
| `rebalance_rule` | string | yes | `smallcases.rebalance_rule` |
| `base_nav` | float | no (default 100) | `smallcases.base_nav` |
| `currency` | string | no (default INR) | `smallcases.currency` |
| `inception_date` | date string | no | `smallcases.inception_date` |
| `notes` | string | no | `smallcases.notes` |
| `versions` | array | yes (≥1) | → `smallcase_constituents` |
| `versions[].effective_from` | date string | yes | `effective_from` |
| `versions[].effective_to` | date string | no | `effective_to` |
| `versions[].version_label` | string | no | `version_label` |
| `versions[].constituents` | array | yes | weight rows |
| `versions[].constituents[].symbol` | string | yes | `symbol` |
| `versions[].constituents[].target_weight` | float | yes | `target_weight` |
| `rebalance_events` | array | no | → `rebalance_events` |
| `rebalance_events[].rebalance_date` | date string | yes | `rebalance_date` |
| `rebalance_events[].reason` | string | no | `reason` |
| `rebalance_events[].from_effective_from` | date string | no | `from_effective_from` |
| `rebalance_events[].to_effective_from` | date string | yes | `to_effective_from` |
| `rebalance_events[].notes` | string | no | `notes` |

Pipeline: validate JSON with `SmallcaseDefinitionFile` → expand to flat constituent + rebalance rows → write Parquet.

---

## Cross-table integrity checklist

| Check | Rule | Severity |
|-------|------|----------|
| Symbol FK | Every `symbol` in prices, constituents, holdings, contribution exists in `instruments` | error (or soft-warn at ingest with log) |
| Smallcase FK | Every `smallcase_id` in child tables exists in `smallcases` | error |
| Weight sum | Per (`smallcase_id`, `effective_from`), weights sum ≈ 1.0 | error |
| Price coverage | Active constituents should have prices; gap policy applies if missing | warn + gap log |
| NAV continuity | One row per trading day from inception through last usable price date | warn if holes |
| Derived freshness | `computed_at` set on every rebuild; full replace OK | required |
| Date order | `effective_to >= effective_from` when both set; `period_end >= period_start` | error |

---

## Minimal viable data to answer product questions

| Product question | Minimum tables |
|------------------|----------------|
| What is the composition? | `smallcases` + `smallcase_constituents` (+ `instruments`) |
| How did it perform? | above + `prices` → build `nav_series` |
| Risk metrics? | `nav_series` → `metrics_snapshot` |
| What drove returns? | constituents + prices → `contribution` |
| When did we rebalance? | `rebalance_events` (+ constituent versions) |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-28 | v0 initial dictionary (9 entities) |
| 2026-07-28 | Implementable pass: dtypes, sort, defaults, raw JSON contract, PK/grain locked |
