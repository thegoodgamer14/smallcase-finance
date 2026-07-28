# SIP Engine Architecture — SIP Lab / Basket Backtest Engine

**Status:** binding design contract for Phase 1 (engine)  
**Owner:** Data Architect  
**Product:** [PRODUCT.md](../../PRODUCT.md) · [PRD](../product/prd-sip-lab.md)  
**Policy:** [ADR 004](../decisions/004-sip-lab-prd-decisions.md) · [ADR 005](../decisions/005-upstox-sole-market-data.md)  
**Entities:** [data-dictionary-sip.md](../data-dictionary-sip.md)  
**v0 NAV (not SIP):** [metrics-definitions.md](../analytics/metrics-definitions.md) · `calc/nav.py` · `POST /backtest`

---

## 1. Purpose

Answer one question reproducibly:

> If I had SIP’d a fixed INR amount into this equity/ETF basket every month on a fixed calendar day (next trading session if needed), what is my **XIRR**, cashflow path, units ledger, and market-value path?

This is **not** the v0 weight-based NAV index (`nav_series` / rebalance backtest). SIP Lab models **cash → units → market value → cashflow XIRR**.

| Concern | v0 weight-NAV | SIP Lab |
|---------|---------------|---------|
| Capital | Implicit index (base_nav) | Explicit monthly contributions |
| Positions | Weights only | **Units** per symbol |
| Success metric | CAGR / total return on NAV | **XIRR** on cashflows |
| Day rule | Every trading day (returns) | Fixed calendar day → **next trading day** |
| Primary code path | `calc/nav.py`, `calc/rebalance.py` | New `calc/sip_*.py` + `calc/xirr.py` (extend; do not overload v0) |

---

## 2. Scope and non-goals

### In scope (Phase 1)

- Equity / ETF baskets only (INR).
- Strategy config (basket + SIP schedule + allocation).
- Fixed calendar day-of-month → next trading day.
- Zero costs (full SIP amount → units at session close).
- Units ledger, contribution cashflows, terminal cashflow, XIRR.
- Secondary path metrics: market-value series, max drawdown, (documented) CAGR/vol on MV path, simple contribution.
- Golden tests with absolute XIRR tolerance **`1e-4`**.
- Prices: **Upstox daily bars** via curated Parquet cache (sample labeled demos only).

### Out of scope (this version)

- Coin / MF, Kite import, live trading, F&O.
- Brokerage / STT / stamp / slippage (optional later behind config; must not break zero-cost goldens).
- yfinance / bhavcopy / Fyers price paths.
- Treating `POST /backtest` rebalance NAV as SIP performance.

---

## 3. Data feed assumption (binding)

| Layer | Rule |
|-------|------|
| **Sole live history** | Upstox API OHLCV (daily preferred) — ADR 005 |
| **Engine input** | Curated daily bars: `data/curated/prices/prices.parquet` |
| **Session calendar** | Trading days = dates present in the **basket price calendar** (see §6) |
| **Price field (MVP)** | `close` (same convention as v0 NAV) |
| **Missing bars** | Skip / warn; never invent prices from another vendor |
| **Demo** | Sample/synthetic prices allowed only when labeled `source=sample` (or equivalent); not real SIP claims |

Pipeline path (existing): Upstox sync → immutable raw drop → curated Parquet → pure calc reads frames/records (no I/O inside `calc/`).

---

## 4. Logical pipeline

```
StrategyConfig
      │
      ▼
 resolve basket weights (versioned constituents or inline)
      │
      ▼
 load prices for universe ∩ [start, end]   ← curated Parquet (Upstox or sample)
      │
      ▼
 build session calendar (trading dates)
      │
      ▼
 SIP schedule: calendar day-of-month → next trading day   (§6)
      │
      ▼
 for each SIP date: allocate amount → buy units at close   (§7)
      │         optional rebalance to target                 (§8)
      ▼
 mark-to-market units daily → market_value series          (§7)
      │
      ▼
 cashflows = contributions (out) + terminal MV (in)        (§5)
      │
      ▼
 XIRR (primary) + secondary metrics + contribution         (§9)
```

**Idempotency:** same `StrategyConfig` + same curated prices → bit-identical cashflows/units within float tolerance; XIRR within fixture gate.

---

## 5. StrategyConfig

Authoring contract (JSON + Pydantic). Logical fields (names binding for implementers):

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `strategy_id` | string | yes | — | Stable slug, lowercase kebab-case |
| `name` | string | yes | — | Display title |
| `currency` | string | no | `INR` | Portfolio currency (no FX) |
| `basket` | object | yes* | — | Basket reference **or** inline (see below) |
| `allocation_mode` | string | no | `custom_weights` | `custom_weights` \| `equal_weight` |
| `sip_amount` | float | yes | — | Monthly contribution in currency units; must be `> 0` |
| `day_of_month` | int | yes | — | Calendar day **1–28** recommended; see clamp rule |
| `start_date` | date | yes | — | First month to schedule (inclusive) |
| `end_date` | date | no | null | Last month to schedule; null = through last usable price date |
| `as_of` | date | no | null | Valuation / terminal date; default = last session with full (or usable) prices |
| `price_field` | string | no | `close` | `close` \| `adj_close` |
| `rebalance_mode` | string | no | `none` | `none` \| `on_sip` \| `monthly` \| `quarterly` |
| `fractional_units` | bool | no | `true` | MVP: **true** — full amount deploys; residual cash ~0 |
| `costs` | object | no | zero | MVP: all zeros; reserved for later |
| `notes` | string | no | null | Free-form |
| `version` | string | no | `1` | Config schema / strategy revision tag |

\* `basket` one of:

```json
{
  "basket": {
    "kind": "smallcase_ref",
    "smallcase_id": "digital-india"
  }
}
```

```json
{
  "basket": {
    "kind": "inline",
    "constituents": [
      { "symbol": "INFY", "target_weight": 0.25 },
      { "symbol": "TCS", "target_weight": 0.25 },
      { "symbol": "RELIANCE", "target_weight": 0.25 },
      { "symbol": "HDFCBANK", "target_weight": 0.25 }
    ]
  }
}
```

### Validation rules

1. `sip_amount > 0`; finite.
2. `day_of_month` ∈ `[1, 28]` for MVP (avoids Feb 29 / month-end ambiguity). Reject 29–31 with a clear error (or document clamp-to-28 if product later allows).
3. `start_date ≤ end_date` when both set; `as_of ≥ start_date` when set.
4. `allocation_mode = custom_weights` → weights sum ≈ 1.0 (tol `1e-6`); symbols uppercase, no exchange suffix.
5. `allocation_mode = equal_weight` → ignore provided weights (or require empty weights) and set `1/n` at each invest/rebalance.
6. Equity/ETF symbols only; no MF scheme codes this version.
7. `costs` all zero in MVP fixtures; non-zero must not be default.

### Example (authoring path)

Suggested path: `data/raw/strategies/{strategy_id}.json`  
See [data-dictionary-sip.md](../data-dictionary-sip.md) for full field dictionary and optional curated tables.

---

## 6. SIP schedule — fixed calendar day → next trading day

### 6.1 Session calendar

Let \(U\) be the basket universe (symbols with target weight \(> 0\) on the relevant version).

**MVP calendar definition (price-calendar, not external holiday API):**

\[
\text{Sessions} = \{ d \mid \text{at least one symbol in } U \text{ has a price row on } d \}
\]

**Stricter optional mode (P3):** require **all** active constituents to have a bar on \(d\) before treating \(d\) as investable; otherwise treat as missing session and roll forward. Engine should expose which mode was used; golden fixtures use a fully filled synthetic calendar so both modes agree.

### 6.2 Candidate calendar dates

For each month \(m\) from `start_date`’s year-month through `end_date` (or last price month):

1. Build candidate \(c = \text{date}(year, month, day\_of\_month)\).
2. If \(c\) is before `start_date` (first partial month), skip or roll per rule: **skip months whose candidate is before `start_date`** unless candidate’s next-session still falls on/after start and is the first scheduled SIP — fixtures should pin this. **Binding default:** first SIP is the first next-session \(s \ge start\_date\) derived from the first month where candidate calendar day’s next-session ≥ `start_date`.
3. If `end_date` set, do not schedule any SIP with invest date \(> end_date\).

### 6.3 Next trading day rule (binding)

\[
s = \min \{ d \in \text{Sessions} \mid d \ge c \}
\]

| Case | Behavior |
|------|----------|
| \(c\) is a session | Invest on \(c\) |
| \(c\) weekend / holiday / no bars | Invest on **next** session after \(c\) |
| No session ≥ \(c\) within horizon | **Skip** that month; record warning `no_session_after_candidate` |
| Multiple SIPs collapse to same session | **Allowed** only if two candidates map to same \(s\) (rare with day 1–28); if it happens, **one** contribution of `sip_amount` that day (do not double). Prefer configs that avoid this. |

**Not used for SIP:** v0 “every ~21 trading days” rebalance cadence. That remains composition analysis only.

### 6.4 Pure function contract

```text
sip_invest_dates(
  day_of_month: int,
  start_date: date,
  end_date: date | None,
  sessions: Sequence[date],  # sorted unique trading days
) -> list[date]
```

- Deterministic; no I/O.
- Input `sessions` must be sorted ascending unique dates.
- Empty sessions → empty schedule + caller warning.

---

## 7. Units, allocation, market value

### 7.1 Target weights on a date

Reuse v0 resolver semantics:

- **smallcase_ref:** `active_weights_on(versions, d)` from `calc/nav.py` (max `effective_from ≤ d`, still active).
- **inline:** static weights for all dates (or equal-weight \(1/n\)).
- Always `normalize_weights` before deploy.

Gap policy on invest day: symbols missing price on \(s\) are **excluded** and remaining weights **renormalized** for that purchase (same spirit as v0 NAV gap policy). Log `gap_symbols` on the ledger event. Do not pull another vendor.

### 7.2 Buy at close (zero costs)

On invest date \(s\), contribution amount \(A = \texttt{sip\_amount}\):

\[
w_i' = \frac{w_i}{\sum_{j \in U_s} w_j},\quad
\Delta q_i = \frac{A \cdot w_i'}{P_{i,s}}
\]

where \(P_{i,s}\) is `price_field` (default `close`), \(U_s\) = symbols with valid price and weight that day.

| Rule | MVP choice |
|------|------------|
| Fractional units | **Allowed** (`fractional_units=true`) |
| Residual cash | ≈ 0 (float dust only); do **not** hold meaningful cash drag in MVP |
| Costs | 0 — no brokerage, STT, slippage |
| Lot sizes | Ignored in MVP |
| Shorts | Forbidden; weights ≥ 0 |

### 7.3 Units ledger

State after each event:

| Quantity | Definition |
|----------|------------|
| \(q_{i,t}\) | Cumulative units of symbol \(i\) after events on date \(t\) |
| Buys | \(q_{i,s} \leftarrow q_{i,s-} + \Delta q_i\) |
| Rebalance | Sell/buy units so market-value weights match target; cash nets to 0 under zero costs (§8) |

Ledger event types: `sip_buy`, `rebalance`, `mark` (optional daily mark rows may be derived without full event log).

### 7.4 Market value path

On any session \(t\) after first SIP:

\[
\mathrm{MV}_t = \sum_i q_{i,t} \cdot P_{i,t}
\]

- Between SIPs, units constant (unless rebalance); MV moves with prices.
- Missing price for a held symbol on day \(t\): use last available close **only for marking** if needed, and flag `stale_mark`; **invest days must not** buy on stale marks — invest only with same-day bar (gap exclude). Prefer fixtures with complete histories.
- Terminal valuation date \(T = \texttt{as\_of}\) or last session ≤ horizon with usable marks.

**Do not** feed SIP market-value into `nav_from_returns` as if it were a unit-capital index without cashflow adjustment — that confuses XIRR with CAGR.

---

## 8. Rebalance (optional, composition hygiene)

SIP contributions already buy at **target** weights each month. Drift appears between SIPs if prices move.

| `rebalance_mode` | Behavior |
|------------------|----------|
| `none` (default MVP) | Units only change on SIP buys; weights drift with prices |
| `on_sip` | After each SIP buy (or combined with it), reset all holdings to target weights at that session’s closes (zero cost, cash-neutral) |
| `monthly` / `quarterly` | On schedule independent of SIP day: next-session after period boundary; rebalance to target |

### 8.1 Zero-cost cash-neutral rebalance

Given current units \(q_i\), prices \(P_i\), target weights \(w_i\):

\[
\mathrm{MV} = \sum_i q_i P_i,\quad
q_i^{\mathrm{new}} = \frac{\mathrm{MV} \cdot w_i}{P_i}
\]

Turnover (informational):

\[
\text{turnover} = \tfrac12 \sum_i \frac{|q_i^{\mathrm{new}} P_i - q_i P_i|}{\mathrm{MV}}
\]

Reuse conceptual helpers from `calc/rebalance.py` (`rebalance_weights`, turnover) for **weight-space** diagnostics, but **do not** call `backtest_rebalance_vs_buyhold` as the SIP engine — that path has no contribution cashflows.

---

## 9. Cashflows, XIRR, secondary metrics, contribution

### 9.1 Cashflow series (binding sign convention)

| Event | Date | Amount | Sign |
|-------|------|--------|------|
| Monthly SIP | invest date \(s\) | `sip_amount` | **Negative** (outflow / investment) |
| Terminal / exit | \(T\) | \(\mathrm{MV}_T\) | **Positive** (inflow / liquidation) |

Optional later: intermediate partial redemptions (out of MVP).

Cashflow list is sorted by date; same-day SIP + terminal only if run ends on a SIP day — both allowed; XIRR must include both.

```text
Cashflow = { date: date, amount: float, kind: "contribution" | "terminal" | "redemption" }
```

### 9.2 XIRR (primary)

Solve \(r\) such that NPV of cashflows at rate \(r\) is 0, using **actual/365.25** year fractions (or ACT/365 — **fixtures must document the day-count**; recommend **ACT/365.25** for stability with Python reference):

\[
\sum_k \mathrm{CF}_k \, (1+r)^{-y_k} = 0,\quad
y_k = \frac{d_k - d_0}{365.25}
\]

where \(d_0\) is the first cashflow date.

| Rule | Detail |
|------|--------|
| Implementation | Pure `calc/xirr.py` — Newton or Brent; no I/O |
| Failure | Return `null` + reason if no real root / non-convergence |
| Fixture gate | \(\lvert r_{\mathrm{engine}} - r_{\mathrm{ref}} \rvert \le 10^{-4}\) absolute |
| Edge cases | < 2 cashflows → null; all CF same sign → null; document in tests |

**XIRR is the SIP success criterion.** Do not replace it with CAGR for pass/fail.

### 9.3 Secondary metrics

Computed on the **market-value path** and cashflow summary; never override XIRR:

| Metric | Definition | Notes |
|--------|------------|-------|
| `total_invested` | \(\sum\) contribution amounts (positive number) | Sum of SIP outflows’ absolute value |
| `final_value` | \(\mathrm{MV}_T\) | Terminal mark |
| `absolute_gain` | `final_value - total_invested` | Not time-weighted |
| `max_drawdown` | Peak-to-trough on \(\mathrm{MV}_t\) as **negative** fraction | Reuse `calc/risk.max_drawdown` |
| `volatility` | Ann. stdev of **daily MV simple returns** | Optional; interpret carefully under cash inflows |
| `cagr_mv` | CAGR of \(\mathrm{MV}_0 \to \mathrm{MV}_T\) | **Misleading under SIP** (ignores staged capital); expose only with label `not_cashflow_aware` or omit from primary UI |
| `n_sips` | Count of contribution events | — |
| `first_sip` / `last_sip` / `as_of` | dates | — |

Reuse: `max_drawdown`, `volatility`, `summary_metrics` patterns from `calc/risk.py` on the MV series **only for secondary display**. Prefer calendar-aware CAGR helper when dates available (`cagr(..., dates=...)`).

### 9.4 Contribution (SIP context)

Two layers (both useful):

**A. Symbol P&L contribution (MVP)**  
Over \([t_0, T]\), for each symbol:

\[
\text{contribution}_i \approx \sum_{\text{lots / path}} q\text{-path gains}
= \mathrm{MV}_{i,T} - \sum_{\text{buys}} \text{cash allocated to } i
\]

Or simpler period form (aligned with v0 spirit):

| Field | Definition |
|-------|------------|
| `symbol` | Ticker |
| `cash_in` | Sum of SIP (and rebalance buy) cash allocated to symbol |
| `market_value_end` | \(q_{i,T} P_{i,T}\) |
| `contribution` | `market_value_end - cash_in` (approx P&L) |
| `weight_end` | \(\mathrm{MV}_{i,T} / \mathrm{MV}_T\) |

**B. Weight × return contribution (v0 reuse)**  
`contribution_by_symbol` in `calc/returns.py` remains valid for **weight-NAV** analysis of the basket as an index — keep it for composition diagnostics; do **not** claim it equals SIP XIRR attribution.

Residual: portfolio absolute gain − sum symbol contributions (rebalance / gap / rounding).

---

## 10. Extend existing `calc/` (module map)

Keep pure functions (no I/O, no FastAPI, no DuckDB). Notebooks and tests import from `smallcase_finance.calc`.

| Module | Role | SIP Lab action |
|--------|------|----------------|
| `calc/weights.py` | normalize, drift | **Reuse** as-is |
| `calc/nav.py` | `active_weights_on`, weight-NAV | **Reuse** weight resolver only; do not use NAV path as SIP result |
| `calc/returns.py` | simple returns, v0 contribution | **Reuse** for basket diagnostics |
| `calc/risk.py` | CAGR, vol, max DD, Sharpe | **Reuse** for secondary MV metrics |
| `calc/rebalance.py` | weight rebalance + v0 backtest | **Reuse** `rebalance_weights` / turnover; **do not** use `backtest_rebalance_vs_buyhold` as SIP |
| **`calc/sip_schedule.py`** | next trading day, SIP dates | **Add** |
| **`calc/sip_ledger.py`** | buys, units, MV path, rebalance-to-units | **Add** |
| **`calc/sip_cashflows.py`** | CF list from ledger + terminal | **Add** (or fold into ledger) |
| **`calc/xirr.py`** | XIRR solver | **Add** |
| **`calc/sip_engine.py`** | orchestrate pure run: config + prices → result | **Add** (or keep orchestration in `services/sip_service.py` with thin pure core) |

### Suggested pure result type

```text
SipEngineResult
  strategy_id: str
  invest_dates: list[date]
  cashflows: list[Cashflow]
  units_end: dict[str, float]
  market_value: list[{date, mv}]          # session marks from first SIP → T
  xirr: float | None
  metrics: SipMetrics                     # secondary
  contribution: list[SymbolContribution]
  warnings: list[str]                     # gaps, skips, sample source, etc.
  meta: { price_field, costs_zero: true, data_source, fractional_units }
```

### Service layer (Backend, not pure)

`services/sip_service.py` (Phase 1):

1. Load/validate `StrategyConfig`.
2. Resolve basket → weights versions.
3. Read curated prices (DuckDB/Polars) for universe and range.
4. Call pure engine.
5. Optionally persist run artifacts under `data/curated/sip/` (see data dictionary).
6. **Never** call v0 `backtest_service` for SIP XIRR.

---

## 11. Golden tests (Phase 1 gate)

### 11.1 Layout

```
tests/
  test_sip_schedule.py      # calendar → next session
  test_sip_ledger.py        # units, residual, multi-SIP MV
  test_xirr.py              # solver + edge cases
  test_sip_engine.py        # end-to-end pure engine
  fixtures/
    sip/
      schedule_weekend.json
      schedule_holiday.json
      xirr_flat.json
      xirr_known_rate.json
      multi_sip_two_asset.json
```

Synthetic prices in fixtures are fine and preferred (deterministic). Label `source=fixture`.

### 11.2 Required cases

| ID | Case | Assert |
|----|------|--------|
| S1 | Candidate weekday is session | invest date = candidate |
| S2 | Candidate Saturday | next Monday (if in sessions) |
| S3 | Candidate on missing session (holiday hole) | next session with bars |
| S4 | No session after candidate | month skipped + warning |
| L1 | Single SIP, one asset, hold | units = A/P; terminal MV = units×P_T |
| L2 | Multi-asset weights sum 1 | cash allocated matches A; residual < 1e-6 × A |
| L3 | Missing price on one symbol on SIP day | renormalize others; warning |
| X1 | Hand-computed / Excel / numpy-financial reference XIRR | abs err ≤ **1e-4** |
| X2 | Known constant growth synthetic | XIRR matches reference within 1e-4 |
| X3 | Two cashflows only | closed-form check |
| E1 | Full engine: 12 SIPs, 2–4 symbols, fixture prices | XIRR + n_sips + final_value |

### 11.3 Tolerance

| Quantity | Tolerance |
|----------|-----------|
| XIRR | absolute **`1e-4`** |
| Cash amounts / MV | relative `1e-8` or absolute `1e-6` INR for unit tests |
| Units | relative `1e-10` on synthetic prices |

### 11.4 Reference XIRR

Prefer an independent reference in tests (e.g. small Newton implementation in fixture generator, or precomputed constants from a verified spreadsheet committed as JSON). Do not call network or Excel at CI time.

---

## 12. File / Parquet layout (SIP additions)

Under `data/` (extends v0 layout; details in [data-dictionary-sip.md](../data-dictionary-sip.md)):

```
data/
  raw/
    strategies/{strategy_id}.json     # authored StrategyConfig
  curated/
    prices/prices.parquet             # existing — Upstox or sample daily bars
    sip/
      strategy_configs.parquet        # optional flatten of strategies
      sip_runs.parquet                # optional run metadata
      sip_cashflows.parquet           # optional persist of CF series
      sip_units_ledger.parquet        # optional event-level units
      sip_market_value.parquet        # optional MV path
      sip_metrics.parquet             # optional XIRR + secondary
      sip_contribution.parquet        # optional per-symbol SIP P&L
```

**MVP storage policy:** engine may be fully **ephemeral** (API returns result without writing curated SIP tables). Curated SIP tables are for reproducibility/export and analyst DuckDB — implement when service persists runs (P1–P2).

---

## 13. Contracts for other agents

| Agent | May assume |
|-------|------------|
| **Data Engineer** | Prices already in curated form with `symbol`, `date`, `close`; Upstox raw drops immutable; strategies in `data/raw/strategies/` |
| **Backend** | Pure engine entrypoint; StrategyConfig Pydantic; service loads prices; separate route from `POST /backtest` |
| **Data Analyst** | XIRR primary; fixtures ≤ 1e-4; secondary metrics labeled; contribution = cash_in vs MV_end for SIP |
| **Frontend (P2)** | Response includes `xirr`, cashflows, MV series, `data_source`, warnings; demo banner when sample |
| **PO** | Engine before UI; no Coin/MF; no alternate price vendors |

### API sketch (P2; not Phase 1 deliverable)

```http
POST /sip/backtest
```

Body: strategy_id or inline StrategyConfig + optional overrides (`end_date`, `as_of`).  
Response: `SipEngineResult` + `data_source: upstox | sample | fixture`.

---

## 14. Worked micro-example (fixture-shaped)

Assumptions: one asset `AAA`, sessions = all weekdays, `day_of_month=15`, `sip_amount=1000`, prices:

| date | close |
|------|------:|
| 2024-01-15 | 100 |
| 2024-02-15 | 110 |
| 2024-02-16 | 111 |  <!-- if 15 missing would roll here -->

- SIP1 2024-01-15: buy \(1000/100 = 10\) units; CF = −1000  
- SIP2 2024-02-15: buy \(1000/110 ≈ 9.0909\) units; CF = −1000  
- Units end ≈ 19.0909; if as_of 2024-02-15, MV ≈ 19.0909×110 = 2100  
- Cashflows: (−1000, 2024-01-15), (−1000, 2024-02-15), (+2100, 2024-02-15)  
- XIRR solves NPV = 0 on those three flows (same-day net CF may be combined in implementation **or** kept separate — **binding: keep separate rows for audit; solver accepts multiple CF on same date**).

---

## 15. Open items (resolved for MVP vs deferred)

| Item | MVP decision | Deferred |
|------|--------------|----------|
| day_of_month range | **1–28 only** | 29–31 clamp rules |
| Fractional shares | **Yes** | Lot-size rounding |
| Residual cash | Dust only | Explicit cash asset |
| Holiday calendar | **Price calendar next bar** | NSE holiday file |
| Day count for XIRR | **ACT/365.25** | ACT/365 product variant |
| Persist SIP Parquet | Optional | Required for multi-run compare UI |
| Costs | **Zero** | Configured cost model |
| Benchmark SIP | — | Phase 3 |

---

## 16. Definition of done (engine docs + implementability)

- [x] StrategyConfig fields and validation documented  
- [x] SIP cashflow sign convention and terminal CF documented  
- [x] Next-trading-day rule and session calendar defined  
- [x] Units buy formula, fractional policy, zero costs  
- [x] Rebalance modes vs SIP contributions clarified  
- [x] XIRR primary + fixture tolerance 1e-4; secondary metrics listed  
- [x] Contribution definition for SIP context  
- [x] `calc/` extension map (reuse vs new modules)  
- [x] Golden test matrix  
- [x] Companion data dictionary for new entities  

Implementation proceeds against this doc + [data-dictionary-sip.md](../data-dictionary-sip.md); deviations need a short ADR.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-28 | Initial SIP engine architecture (Phase 1 contract) |
