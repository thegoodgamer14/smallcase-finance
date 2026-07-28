# Data Dictionary — SIP Lab Entities

**Status:** implementable contract for SIP Lab (Phase 0–2)  
**Owner:** Data Architect  
**Companion:** [architecture/sip-engine.md](architecture/sip-engine.md)  
**v0 dictionary (still valid):** [data-dictionary.md](data-dictionary.md)  
**Policy:** [ADR 004](decisions/004-sip-lab-prd-decisions.md) · [ADR 005](decisions/005-upstox-sole-market-data.md)

This document defines **new** entities for monthly SIP backtests. It does **not** replace v0 tables (`instruments`, `prices`, `smallcases`, `nav_series`, …). SIP engine **reads** v0 curated prices + optional smallcase constituents; it **writes** optional SIP tables under `data/curated/sip/` when runs are persisted.

---

## Conventions (inherit v0 + SIP-specific)

All [v0 conventions](data-dictionary.md#conventions-binding) apply (dates ISO, symbols uppercase, weights fractions, returns decimals, INR, Parquet column names exact).

| Convention | SIP rule |
|------------|----------|
| Kind | **S** = source of truth; **D** = derived from a SIP run; **A** = authoring (raw JSON) |
| Cashflow sign | **Negative** = money invested (outflow); **Positive** = money returned / terminal value (inflow) |
| XIRR | Decimal rate (`0.12` = 12% annualized); golden abs tol **`1e-4`** |
| Costs MVP | All cost fields **0** or absent; engine assumes zero friction |
| Asset class | Equity / ETF only — no MF scheme rows in SIP tables this version |
| Price dependency | Daily bars from `prices` (Upstox-curated or labeled sample) |
| Run identity | `run_id` = stable slug or UUID string per engine invocation when persisted |
| Empty tables | Absent file **or** 0-row Parquet; both mean “no persisted SIP data” |
| Ephemeral MVP | Engine may return results without writing any SIP Parquet |

### Logical type → storage

Same mapping as v0 data dictionary (string / date / timestamp / float / int / bool).

---

## Entity overview

```
instruments 1──* prices                    (v0 — market data)
     │
     │ symbol
     ▼
smallcases / inline basket ──► StrategyConfig (A/S)
                                    │
                                    ▼
                               sip_runs (D meta)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            sip_cashflows    sip_units_ledger   sip_market_value
                    │               │               │
                    └───────────────┴───────┬───────┘
                                            ▼
                                     sip_metrics
                                            │
                                            ▼
                                    sip_contribution
```

| # | Entity | Kind | Required for engine run? | Persist MVP? |
|---|--------|------|--------------------------|--------------|
| 0 | `prices` (v0) | S | **Yes** (input) | existing |
| 1 | `strategy_config` (JSON) | A/S | **Yes** (input) | raw JSON yes |
| 2 | `strategy_configs` (Parquet) | S | No (flatten optional) | optional |
| 3 | `sip_runs` | D | No | optional |
| 4 | `sip_cashflows` | D | No (in-memory OK) | optional |
| 5 | `sip_units_ledger` | D | No | optional |
| 6 | `sip_market_value` | D | No | optional |
| 7 | `sip_metrics` | D | No | optional |
| 8 | `sip_contribution` | D | No | optional |

---

## 0. Input dependency — `prices` (v0, unchanged)

| | |
|--|--|
| **Path** | `data/curated/prices/prices.parquet` |
| **SIP usage** | Session calendar + invest/mark prices |
| **Required columns** | `symbol`, `date`, `close` (or `adj_close` if `price_field=adj_close`) |
| **Source for real runs** | Upstox → raw drop → curated (`source` e.g. `upstox`) |
| **Demo** | `source=sample` (must not be presented as live SIP) |

See [data-dictionary.md § prices](data-dictionary.md#2-prices--s).

---

## 1. `strategy_config` — **A** (authoring JSON)

| | |
|--|--|
| **Path** | `data/raw/strategies/{strategy_id}.json` |
| **Grain** | One strategy definition file |
| **Primary key** | `strategy_id` (filename should match) |
| **Description** | Human-authored SIP + basket configuration; validated by Pydantic before run |

### Top-level fields

| # | Field | Logical | Required | Default | Description |
|---|-------|---------|----------|---------|-------------|
| 1 | `strategy_id` | string | yes | — | Stable slug PK; lowercase kebab-case |
| 2 | `name` | string | yes | — | Display title |
| 3 | `currency` | string | no | `INR` | Portfolio currency |
| 4 | `basket` | object | yes | — | See basket object below |
| 5 | `allocation_mode` | string | no | `custom_weights` | `custom_weights` \| `equal_weight` |
| 6 | `sip_amount` | float | yes | — | Monthly contribution; must be `> 0` |
| 7 | `day_of_month` | int | yes | — | Calendar day **1–28** (MVP) |
| 8 | `start_date` | date string | yes | — | ISO date; first schedule bound |
| 9 | `end_date` | date string | no | null | Last schedule bound; null = through last price |
| 10 | `as_of` | date string | no | null | Terminal valuation date override |
| 11 | `price_field` | string | no | `close` | `close` \| `adj_close` |
| 12 | `rebalance_mode` | string | no | `none` | `none` \| `on_sip` \| `monthly` \| `quarterly` |
| 13 | `fractional_units` | bool | no | `true` | MVP default true |
| 14 | `costs` | object | no | zeros | Reserved; see costs object |
| 15 | `version` | string | no | `1` | Config revision tag |
| 16 | `notes` | string | no | null | Free-form |
| 17 | `created_at` | timestamp string | no | null | Authoring metadata (UTC) |

### `basket` object

**Variant A — smallcase reference**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `kind` | string | yes | Must be `smallcase_ref` |
| `smallcase_id` | string | yes | FK → `smallcases.smallcase_id` / raw smallcase JSON |

Weights come from versioned `smallcase_constituents` (v0) as-of each invest date.

**Variant B — inline constituents**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `kind` | string | yes | Must be `inline` |
| `constituents` | array | yes | Non-empty list |
| `constituents[].symbol` | string | yes | Uppercase ticker |
| `constituents[].target_weight` | float | yes* | Fraction; required if `allocation_mode=custom_weights` |

\* If `allocation_mode=equal_weight`, weights may be omitted and inferred as \(1/n\).

### `costs` object (MVP zeros)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brokerage_bps` | float | `0` | One-way bps (later) |
| `stt_bps` | float | `0` | Later |
| `slippage_bps` | float | `0` | Later |
| `flat_fee` | float | `0` | Absolute currency fee per trade (later) |

### Example

```json
{
  "strategy_id": "digital-india-sip-5k",
  "name": "Digital India — ₹5k monthly SIP",
  "currency": "INR",
  "basket": {
    "kind": "smallcase_ref",
    "smallcase_id": "digital-india"
  },
  "allocation_mode": "custom_weights",
  "sip_amount": 5000,
  "day_of_month": 5,
  "start_date": "2022-01-01",
  "end_date": null,
  "as_of": null,
  "price_field": "close",
  "rebalance_mode": "none",
  "fractional_units": true,
  "costs": {
    "brokerage_bps": 0,
    "stt_bps": 0,
    "slippage_bps": 0,
    "flat_fee": 0
  },
  "version": "1",
  "notes": "MVP zero-cost SIP against curated Upstox prices"
}
```

### Integrity checks

1. `day_of_month ∈ [1, 28]`.
2. `sip_amount > 0` finite.
3. Inline weights sum ≈ 1.0 when `custom_weights` (tol `1e-6`).
4. Symbols uppercase, no `.NS` / `.BO` suffix.
5. Equity/ETF only (no MF codes).
6. `start_date ≤ end_date` when both set.

---

## 2. `strategy_configs` — **S** (optional Parquet flatten)

| | |
|--|--|
| **Path** | `data/curated/sip/strategy_configs.parquet` |
| **Grain** | One row per strategy (latest or versioned — see note) |
| **Primary key** | (`strategy_id`, `version`) |
| **Sort** | `strategy_id`, `version` ASC |
| **Description** | Flattened strategy headers for listing in API/UI; basket payload may be JSON string |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `strategy_id` | string | yes | PK part |
| 2 | `version` | string | yes | PK part |
| 3 | `name` | string | yes | Display |
| 4 | `currency` | string | yes | Default `INR` |
| 5 | `basket_kind` | string | yes | `smallcase_ref` \| `inline` |
| 6 | `smallcase_id` | string | no | Set when `basket_kind=smallcase_ref` |
| 7 | `allocation_mode` | string | yes | |
| 8 | `sip_amount` | float | yes | `> 0` |
| 9 | `day_of_month` | int | yes | 1–28 |
| 10 | `start_date` | date | yes | |
| 11 | `end_date` | date | no | |
| 12 | `as_of` | date | no | |
| 13 | `price_field` | string | yes | |
| 14 | `rebalance_mode` | string | yes | |
| 15 | `fractional_units` | bool | yes | |
| 16 | `config_json` | string | no | Full original JSON for round-trip |
| 17 | `updated_at` | timestamp | yes | UTC |

**Inline constituents** (if not only in `config_json`): optional side table or JSON array in `config_json` only for MVP.

---

## 3. `sip_runs` — **D** (optional run metadata)

| | |
|--|--|
| **Path** | `data/curated/sip/sip_runs.parquet` |
| **Grain** | One engine invocation |
| **Primary key** | `run_id` |
| **Sort** | `run_id` ASC |
| **Description** | Provenance for a SIP backtest run |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | UUID or slug PK |
| 2 | `strategy_id` | string | yes | FK → strategy |
| 3 | `strategy_version` | string | no | Config version used |
| 4 | `start_date` | date | yes | Effective schedule start |
| 5 | `end_date` | date | no | Effective schedule end |
| 6 | `as_of` | date | yes | Terminal valuation date used |
| 7 | `sip_amount` | float | yes | Amount used (after overrides) |
| 8 | `day_of_month` | int | yes | |
| 9 | `price_field` | string | yes | |
| 10 | `rebalance_mode` | string | yes | |
| 11 | `data_source` | string | yes | `upstox` \| `sample` \| `fixture` \| `mixed` |
| 12 | `costs_zero` | bool | yes | Must be `true` for MVP goldens |
| 13 | `n_sips` | int | yes | Contribution count; `>= 0` |
| 14 | `n_warnings` | int | no | |
| 15 | `engine_version` | string | no | Code/semver tag |
| 16 | `computed_at` | timestamp | yes | UTC |

---

## 4. `sip_cashflows` — **D**

| | |
|--|--|
| **Path** | `data/curated/sip/sip_cashflows.parquet` |
| **Grain** | One cashflow leg per run |
| **Primary key** | (`run_id`, `cf_seq`) |
| **Sort** | `run_id`, `cf_seq` ASC |
| **Description** | Full cashflow series for XIRR and export |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | FK → `sip_runs` |
| 2 | `cf_seq` | int | yes | 0-based order in solver input (stable) |
| 3 | `date` | date | yes | Cashflow date (invest or terminal) |
| 4 | `amount` | float | yes | **Signed**: contrib `< 0`, terminal `> 0` |
| 5 | `kind` | string | yes | `contribution` \| `terminal` \| `redemption` |
| 6 | `currency` | string | yes | Default `INR` |
| 7 | `notes` | string | no | e.g. `rolled_from=2024-01-06` |

**Checks:** at least one contribution and one terminal for a complete XIRR run; dates non-decreasing in `cf_seq` order; sum of contributions `< 0`.

---

## 5. `sip_units_ledger` — **D**

| | |
|--|--|
| **Path** | `data/curated/sip/sip_units_ledger.parquet` |
| **Grain** | One row per run, event, symbol (position delta or post-event units) |
| **Primary key** | (`run_id`, `event_seq`, `symbol`) |
| **Sort** | `run_id`, `event_seq`, `symbol` ASC |
| **Description** | Units bought/sold and cumulative units after each SIP/rebalance event |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | FK → `sip_runs` |
| 2 | `event_seq` | int | yes | Event order |
| 3 | `event_date` | date | yes | Session date of event |
| 4 | `event_type` | string | yes | `sip_buy` \| `rebalance` |
| 5 | `symbol` | string | yes | FK → instruments / prices |
| 6 | `price` | float | yes | Price used; `> 0` |
| 7 | `delta_units` | float | yes | Signed; buy `> 0`, sell `< 0` |
| 8 | `units_after` | float | yes | Cumulative units after event; `>= 0` |
| 9 | `cash_delta` | float | yes | Signed cash for this symbol leg (buy negative) |
| 10 | `target_weight` | float | no | Weight used for allocation |
| 11 | `weight_after` | float | no | MV weight after event if marked |

**MVP:** fractional `units_after` allowed; sum of `cash_delta` over symbols on a `sip_buy` ≈ `−sip_amount` (tol relative `1e-8`).

---

## 6. `sip_market_value` — **D**

| | |
|--|--|
| **Path** | `data/curated/sip/sip_market_value.parquet` |
| **Grain** | One mark per run per session date |
| **Primary key** | (`run_id`, `date`) |
| **Sort** | `run_id`, `date` ASC |
| **Description** | Portfolio market value path from first SIP through `as_of` |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | FK → `sip_runs` |
| 2 | `date` | date | yes | Trading session |
| 3 | `market_value` | float | yes | \(\sum q_i P_i\); `>= 0` |
| 4 | `total_invested_to_date` | float | no | Cumulative contributions (positive number) through `date` |
| 5 | `daily_return` | float | no | \(\mathrm{MV}_t/\mathrm{MV}_{t-1}-1\); **null or 0** on first mark / post-inflow days if not adjusted |
| 6 | `n_symbols` | int | no | Held names with units `> 0` |
| 7 | `has_sip` | bool | no | True if a contribution occurred this date |
| 8 | `has_rebalance` | bool | no | True if rebalance this date |

**Note:** Raw daily returns on MV are **not** cashflow-aware; do not use them as XIRR. Optional fields support charts (invested vs value).

---

## 7. `sip_metrics` — **D**

| | |
|--|--|
| **Path** | `data/curated/sip/sip_metrics.parquet` |
| **Grain** | One metrics row per run (extend later with windows if needed) |
| **Primary key** | `run_id` |
| **Sort** | `run_id` ASC |
| **Description** | XIRR (primary) and secondary SIP metrics |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | PK / FK → `sip_runs` |
| 2 | `xirr` | float | no | Primary annualized rate; null if undefined |
| 3 | `xirr_day_count` | string | yes | e.g. `ACT/365.25` |
| 4 | `total_invested` | float | yes | Sum of \|contribution\|; `>= 0` |
| 5 | `final_value` | float | yes | \(\mathrm{MV}_{as\_of}\); `>= 0` |
| 6 | `absolute_gain` | float | yes | `final_value - total_invested` |
| 7 | `n_sips` | int | yes | |
| 8 | `first_sip_date` | date | no | |
| 9 | `last_sip_date` | date | no | |
| 10 | `as_of` | date | yes | |
| 11 | `max_drawdown` | float | no | Negative fraction on MV path |
| 12 | `volatility` | float | no | Ann. vol of daily MV returns (interpret with care) |
| 13 | `cagr_mv` | float | no | **Not cashflow-aware**; optional; label in UI |
| 14 | `xirr_status` | string | yes | `ok` \| `undefined` \| `failed` |
| 15 | `xirr_message` | string | no | Failure detail |
| 16 | `computed_at` | timestamp | yes | UTC |

**Fixture gate:** when `xirr_status=ok`, golden tests require \(\lvert xirr - xirr_{ref}\rvert \le 10^{-4}\).

---

## 8. `sip_contribution` — **D**

| | |
|--|--|
| **Path** | `data/curated/sip/sip_contribution.parquet` |
| **Grain** | One row per run per symbol (full-horizon SIP P&L attribution) |
| **Primary key** | (`run_id`, `symbol`) |
| **Sort** | `run_id`, `symbol` ASC |
| **Description** | Per-symbol cash allocated vs ending market value (SIP contribution) |

| # | Field | Logical | Required | Description |
|---|-------|---------|----------|-------------|
| 1 | `run_id` | string | yes | FK → `sip_runs` |
| 2 | `symbol` | string | yes | Ticker; reserved `_RESIDUAL` allowed |
| 3 | `cash_in` | float | yes | Sum of cash allocated to buys of this symbol (positive number) |
| 4 | `units_end` | float | yes | Units at `as_of`; `>= 0` |
| 5 | `price_end` | float | no | Mark price at `as_of` |
| 6 | `market_value_end` | float | yes | `units_end * price_end` |
| 7 | `contribution` | float | yes | `market_value_end - cash_in` (approx P&L) |
| 8 | `weight_end` | float | no | Share of final MV |
| 9 | `computed_at` | timestamp | yes | UTC |

**Residual:** row `symbol='_RESIDUAL'` may hold `absolute_gain - sum(contribution_i)` from rebalance/gap/rounding.

**Not** multi-period Brinson; not a substitute for XIRR.

---

## Raw vs curated layout (SIP)

```
data/
  raw/
    strategies/
      {strategy_id}.json                 # StrategyConfig authoring
    prices/
      {yyyy-mm-dd}_upstox/               # Upstox OHLCV drops (existing policy)
      {yyyy-mm-dd}_sample/               # demo only
  curated/
    prices/prices.parquet                # engine price input (v0)
    instruments/instruments.parquet      # symbol master (v0)
    smallcases/...                       # when basket.kind=smallcase_ref
    sip/
      strategy_configs.parquet           # optional
      sip_runs.parquet
      sip_cashflows.parquet
      sip_units_ledger.parquet
      sip_market_value.parquet
      sip_metrics.parquet
      sip_contribution.parquet
```

**Path constants (implementer):** extend `data_access/paths.py` with keys under a `SIP_CURATED_FILES` (or similar) map when persistence lands. Do not mix SIP derived tables into v0 `nav/` or `metrics/` paths.

---

## Cross-table integrity (SIP)

| Check | Rule | Severity |
|-------|------|----------|
| Strategy symbols | Every symbol in inline basket / ledger exists in `instruments` (or is allowed unknown with warn) | warn/error |
| Price coverage | Invest dates have prices for allocated symbols after gap policy | warn |
| CF ↔ ledger | Sum of contribution CF amounts = −`total_invested` | error if persist |
| CF terminal | Exactly one `kind=terminal` per complete run | error |
| Units non-negative | `units_after >= 0` | error |
| XIRR inputs | ≥1 contribution and 1 terminal when `xirr_status=ok` | error |
| data_source | `sample` / `fixture` must not be labeled as Upstox market SIP | error (product) |
| costs_zero | MVP goldens require true | error in fixtures |
| No MF rows | No mutual-fund scheme identifiers in SIP baskets this version | error |

---

## Minimal data to answer SIP product questions

| Product question | Minimum inputs / outputs |
|------------------|---------------------------|
| What is my SIP XIRR? | StrategyConfig + prices → cashflows → `xirr` |
| When did money go in? | `sip_cashflows` where `kind=contribution` |
| What do I hold? | `sip_units_ledger` latest / `units_end` |
| How did value evolve? | `sip_market_value` |
| What drove P&L by name? | `sip_contribution` |
| Is this real market data? | `sip_runs.data_source` + price `source` |

---

## Relationship to v0 metrics tables

| v0 table | SIP Lab relationship |
|----------|----------------------|
| `nav_series` | **Not** SIP MV; remains weight-index NAV |
| `metrics_snapshot` | **Not** XIRR; remains NAV-window risk metrics |
| `contribution` | Weight×return for index; use `sip_contribution` for SIP P&L |
| `rebalance_events` | Basket methodology audit; SIP rebalance is engine-internal unless logged in `sip_units_ledger` |

---

## Pydantic / schema ownership

| Artifact | Owner | Location (target) |
|----------|-------|-------------------|
| StrategyConfig model | Backend + Data Architect contract | `schemas/sip.py` (or `schemas/strategy.py`) |
| SipEngineResult DTOs | Backend | `schemas/sip.py` |
| Parquet column names | This dictionary | binding |
| Pure calc types | Backend / Analyst | `calc/sip_*.py`, `calc/xirr.py` |

Domain models validate authoring JSON; Parquet columns must match field names above when persisted.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-28 | Initial SIP Lab data dictionary (strategy + run artifacts) |
