# SIP Lab — Page Spec (`/sip-lab`)

**Audience:** Frontend agent  
**Product:** SIP Lab / Basket Backtest Engine (P2 UI)  
**Job to be done:** *Configure a monthly SIP into my basket, run a backtest, and trust the XIRR + path.*  
**Route:** `/sip-lab` (App Router `app/sip-lab/page.tsx`)  
**Shell:** Global layout (top bar + left nav). See [ui.md](../../architecture/ui.md).  
**Visual language:** [design-system.md](../design-system.md) · [components.md](../components.md)  
**Product rules:** [PRD](../../product/prd-sip-lab.md) · [ADR 004](../../decisions/004-sip-lab-prd-decisions.md) · [ADR 005](../../decisions/005-upstox-sole-market-data.md)

**Primary metric:** **XIRR** (not v0 weight-NAV total return).  
**Data source (binding):** Upstox OHLCV only for real claims; sample/demo must be labeled.

---

## 0. IA & nav changes

### Left nav (extend existing `AppShell` NAV)

| Order | Label | Route | Icon (Lucide suggestion) |
|------:|-------|-------|--------------------------|
| 1 | Dashboard | `/` | `LayoutDashboard` |
| 2 | Holdings | `/holdings` | `PieChart` |
| 3 | Performance | `/performance` | `Activity` |
| 4 | **SIP Lab** | `/sip-lab` | `FlaskConical` or `LineChart` |

- Active state: same as v0 — `bg-[var(--accent-subtle)] text-[var(--accent)]`.
- Optional nav divider above SIP Lab if it reads as a distinct “lab” surface (not required).

### Top bar on SIP Lab

| Control | Behavior on `/sip-lab` |
|---------|------------------------|
| Brand | Unchanged |
| SmallcaseSelect | **Optional seed** for “load basket from smallcase” — not the sole strategy source. Prefer strategy picker inside page when strategies exist. |
| RangeChips / CustomRange | **Hide or disable** on SIP Lab. SIP range is **start/end on the form**, not global performance window. |
| As-of badge | Keep for curated price as-of when available |
| ThemeToggle | Unchanged |
| DataSourceBanner | **Always visible** (global); SIP results also show an in-page source chip (see §6) |

Rationale: SIP is a **run-oriented lab**, not a passive browse of curated NAV. Global range chips would fight SIP start/end.

### Future routes (do not implement this version)

| Route / surface | Status |
|-----------------|--------|
| Coin / MF import | Deferred — Coin last |
| Kite equity holdings import | Phase 4 |
| Live portfolio vs SIP compare | Phase 4 |
| Multi-strategy side-by-side | P3+ |

Note in UI only as muted “Coming later” if empty-state CTAs need a slot — **no fake forms**.

---

## 1. Layout (desktop ≥1280px)

Two-zone lab: **config (left sticky)** + **results (right scroll)**. Desktop-first density.

```
┌─ App shell ──────────────────────────────────────────────────────────────────┐
│ DataSourceBanner (Upstox configured | Sample demo)                           │
│ TopBar: Logo · [optional strategy/smallcase seed] · Theme                    │
├─ LeftNav ─┬─ Main max-w-[1440px] mx-auto px-6 py-6 ──────────────────────────┤
│ Dashboard │                                                                  │
│ Holdings  │  Header: “SIP Lab” · subtitle methodology one-liner              │
│ Perf      │                                                                  │
│ SIP Lab ● │  ┌─ grid grid-cols-12 gap-6 ───────────────────────────────────┐ │
│           │  │                                                             │ │
│           │  │  col-span-4  (sticky top-20 self-start)                     │ │
│           │  │  ┌ StrategyEditor ───────────────────────────────────────┐  │ │
│           │  │  │ Basket select / edit · constituents table · weights   │  │ │
│           │  │  └───────────────────────────────────────────────────────┘  │ │
│           │  │  ┌ SipParamsForm ────────────────────────────────────────┐  │ │
│           │  │  │ Amount · day-of-month · start · end · allocation mode │  │ │
│           │  │  │ [Run backtest]  primary CTA                           │  │ │
│           │  │  │ [Export ▾] disabled until result                      │  │ │
│           │  │  └───────────────────────────────────────────────────────┘  │ │
│           │  │  ┌ MethodologyWarnings (collapsible) ────────────────────┐  │ │
│           │  │  │ Zero costs · day rule · sample vs Upstox · not v0 NAV │  │ │
│           │  │  └───────────────────────────────────────────────────────┘  │ │
│           │  │                                                             │ │
│           │  │  col-span-8                                                 │ │
│           │  │  ┌ Empty | Loading | Error | Results ────────────────────┐  │ │
│           │  │  │ DataSourceStatus chip (result-scoped)                 │  │ │
│           │  │  │ KPI: XIRR (hero) + secondary metrics                  │  │ │
│           │  │  │ Equity / market-value curve                           │  │ │
│           │  │  │ Drawdown (optional secondary)                         │  │ │
│           │  │  │ Contribution / cashflow tables                        │  │ │
│           │  │  │ Assumptions footer                                    │  │ │
│           │  │  └───────────────────────────────────────────────────────┘  │ │
│           │  └─────────────────────────────────────────────────────────────┘ │
└───────────┴──────────────────────────────────────────────────────────────────┘
```

**Vertical rhythm:** section gap `gap-6` (24px) inside columns; form fields `gap-3`–`gap-4`.

### Breakpoints

| Width | Behavior |
|-------|----------|
| ≥1280 | 4 + 8 columns; config sticky |
| 768–1279 | Single column: config first, results below; sticky off |
| <768 | Full stack; tables horizontal-scroll; CTA full-width |

---

## 2. Page header

```
flex flex-col gap-1 mb-2
h1: text-xl font-semibold text-[var(--text-primary)]  →  “SIP Lab”
p:  text-sm text-[var(--text-secondary)]
    →  “Monthly SIP into a custom equity/ETF basket · XIRR primary · Upstox history”
```

No marketing hero. Optional right-side link: “How SIP differs from Performance NAV →” → expand methodology panel or anchor `#methodology`.

---

## 3. Strategy editor (`StrategyEditor`)

**Purpose:** Define or load the basket the SIP deploys into.

### 3.1 Modes (MVP)

| Mode | UX | Notes |
|------|-----|-------|
| **Load strategy** | Select from `GET /strategies` (or local sample list) | Preferred when API exists |
| **Load from smallcase** | Map v0 smallcase → constituents + weights | Seed only; still a SIP strategy run |
| **Inline edit** | Editable table of symbol + weight | Equity/ETF only |

Do **not** build a full portfolio-import wizard (Kite/Coin).

### 3.2 Anatomy

```
┌─ Strategy ─────────────────────────────────────────────┐
│ Label: Strategy · [Select ▾]  or  “Untitled basket”    │
│                                                        │
│ Allocation mode: (•) Custom weights  ( ) Equal weight  │
│                                                        │
│ ┌ Constituents table ────────────────────────────────┐ │
│ │ Symbol │ Name        │ Weight % │  [×]             │ │
│ │ RELIANCE│ Reliance…  │  25.0    │                  │ │
│ │ …       │            │          │                  │ │
│ └────────────────────────────────────────────────────┘ │
│ [+ Add symbol]   Weight sum: 100.0%  or warning chip   │
│                                                        │
│ Instrument map: N/M resolved · missing → warning list  │
└────────────────────────────────────────────────────────┘
```

### 3.3 Constituent table columns

| Field | Header | Align | Format | Notes |
|-------|--------|-------|--------|-------|
| `symbol` | Symbol | left | mono `text-sm tabular-nums` optional | Required |
| `name` | Name | left | truncate | Optional |
| `weight` | Weight | right | `25.0%` (1 dp) | Hide editable % in equal-weight mode (show computed) |
| actions | — | center | remove icon button | ghost |

- Row height ~36–40px (design-system dense table).
- Header: `bg-[var(--bg-muted)] text-[var(--text-secondary)] sticky` if list long.
- Max visible rows ~8 with internal scroll `max-h-[280px] overflow-y-auto`.

### 3.4 Validation (inline, not blocking page)

| Condition | Treatment |
|-----------|-----------|
| Weight sum ≠ 100% (±0.1%) in custom mode | `Badge warning`: “Weights sum to 98.2%” — disable Run |
| Empty constituents | Disable Run; helper text |
| Duplicate symbols | Highlight row; disable Run |
| Unresolved `instrument_key` | Row-level warning icon + list under table; Run may still fire if API allows partial — prefer **block** until mapped or user confirms skip |
| Non equity/ETF | Reject in UI with helper: “Equities & ETFs only this version” |

### 3.5 Component props (conceptual)

```
StrategyEditor {
  strategyId?: string
  constituents: { symbol: string; name?: string; weight: number }[]
  allocationMode: 'custom_weights' | 'equal_weight'
  instrumentStatus?: { symbol: string; resolved: boolean; instrument_key?: string }[]
  onChange: (patch) => void
  loading?: boolean
  readOnly?: boolean   // when replaying a frozen run result
}
```

Tailwind card:

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 flex flex-col gap-3
```

---

## 4. SIP parameters (`SipParamsForm`)

**Purpose:** Cash contribution schedule. Binding product rules from ADR 004.

### 4.1 Fields

| Field | Control | Default | Validation | Notes |
|-------|---------|---------|------------|-------|
| `amount` | Number input + ₹ prefix | `10000` | > 0 | Format display `en-IN`; store number |
| `day_of_month` | Number 1–28 (or select) | `1` | 1–28 MVP | Label: “SIP day (calendar)” |
| `start_date` | Date input | e.g. 3y ago or strategy default | ≤ end | `YYYY-MM-DD` |
| `end_date` | Date input **or** toggle “To latest price” | latest | ≥ start | Toggle clears explicit end |
| `allocation_mode` | Radio (if not only on strategy) | custom / equal | — | Single source of truth with StrategyEditor |

### 4.2 Layout

```
┌─ SIP parameters ───────────────────────────────────────┐
│ Monthly amount                                         │
│ ┌ ₹ ───────────────────────────────────────────────┐   │
│ │ 10,000                                           │   │
│ └──────────────────────────────────────────────────┘   │
│                                                        │
│ SIP day of month          [ 1 ▾ ]  (1–28)              │
│ helper: Non-trading days → next trading session        │
│                                                        │
│ Start date  [ 2021-01-01 ]                             │
│ End date    [ 2024-12-31 ]  ☑ To latest available      │
│                                                        │
│ ┌────────────────────────────┐  ┌───────────────────┐  │
│ │  Run backtest              │  │ Export ▾          │  │
│ │  primary accent            │  │ secondary, off    │  │
│ └────────────────────────────┘  └───────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 4.3 Field chrome (forms)

| Element | Spec |
|---------|------|
| Label | `text-xs font-medium text-[var(--text-secondary)]` |
| Input height | 40px (`h-10`) |
| Input | `rounded-md border border-[var(--border-default)] bg-[var(--bg-muted)] px-3 text-sm text-[var(--text-primary)] tabular-nums` |
| Focus | `focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50` |
| Prefix ₹ | Absolute left inside amount field; muted |
| Helper | `text-[11px] text-[var(--text-muted)]` under day-of-month |

### 4.4 Primary CTA — Run backtest

| State | Visual |
|-------|--------|
| Ready | `primary` button full width of card: solid `bg-[var(--accent)] text-[var(--text-inverse)] h-10 font-medium` |
| Invalid form | Disabled: `opacity-50 cursor-not-allowed` |
| Running | Spinner + “Running…”; disable double-submit |
| Success | Brief idle; results panel updates (no confetti) |

Label: **“Run backtest”** — not “Invest” / “Trade”.

### 4.5 Export control

| Detail | Spec |
|--------|------|
| Placement | Adjacent to Run (secondary) or results header |
| Formats | CSV cashflows · JSON summary (menu) |
| Disabled | Until successful run |
| Variant | `secondary` border button |

---

## 5. Results panel — states

### 5.1 Idle (no run yet)

Centered empty state inside right column surface:

```
EmptyState
  title: “Run a SIP backtest”
  body:  “Set basket, amount, and dates — results show XIRR, market value path, and cashflows.”
  icon:  Flask / chart (muted)
```

Reuse `EmptyState` patterns from v0 feedback components.

### 5.2 Loading

- Skeleton KPI row (hero XIRR block + 4 small cards)
- Chart skeleton `h-[360px] animate-pulse bg-[var(--bg-muted)] rounded-lg`
- Table skeleton 5 rows
- Config column remains interactive but Run stays in running state

### 5.3 Error

Inline `ErrorBanner` at top of results column:

| Kind | Copy pattern |
|------|----------------|
| 4xx config | “Invalid SIP config: {detail}” |
| Missing prices | “Insufficient price history for {symbols}. Sync Upstox or shorten range.” |
| Engine | “Backtest failed. Retry or check API logs.” |
| Network | “API unreachable at {base}.” |

Retry button when safe. Preserve last good result below banner if any (optional).

### 5.4 Success

Full results stack (§6–§9). Persist last request params in URL query where practical for reload:

```
?strategy=<id>&amount=10000&day=1&start=2021-01-01&end=2024-12-31
```

Do not put secrets in URL.

---

## 6. Data-source status (result-scoped)

**In addition to** global `DataSourceBanner`.

### 6.1 Chip / banner under results header

| `data_source` (API) | Visual | Copy |
|---------------------|--------|------|
| `upstox` | `Badge info` accent subtle | “Prices: Upstox (cached curated)” |
| `sample` | `Badge warning` risk.warning | “Demo / sample prices — not live market SIP performance” |
| mixed / partial | `Badge warning` | “Partial Upstox coverage · N symbols sample or missing” |

```
flex flex-wrap items-center gap-2 mb-3
```

**Rules (ADR 005):**

- Never imply sample = Upstox.
- Never show tokens, keys, or secrets.
- If sample: hero XIRR still shown but with warning stripe on KPI well optional:

```
border-l-2 border-[var(--risk-warning)]
```

### 6.2 Pre-run status (config column)

Small line under Run button:

- Configured: “Will use curated prices (Upstox sync path).”
- Not configured: “No Upstox token — run will use sample/demo prices.”

Link text to `docs/integrations/upstox.md` is optional in UI (tooltip ok).

---

## 7. KPI strip — XIRR primary

**Hierarchy:** XIRR is the hero; secondary metrics support path risk/size. Do **not** lead with v0 NAV index return as the story.

### 7.1 Layout

```
┌ grid: 1 hero + secondary ─────────────────────────────────────────────┐
│  ┌ XIRR hero (col larger) ─────┐  ┌ Total invested ┐ ┌ Final value ┐  │
│  │ XIRR                        │  │ ₹12,00,000     │  │ ₹18,42,000  │  │
│  │ +14.82%                     │  └────────────────┘  └─────────────┘  │
│  │ n SIPs · date range         │  ┌ Max DD ────────┐ ┌ Contribs ───┐  │
│  └─────────────────────────────┘  │ −18.40%        │  │ 36 months   │  │
│                                   └────────────────┘  └─────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

Tailwind sketch:

```
grid grid-cols-2 lg:grid-cols-6 gap-4
  XIRR card:   col-span-2 lg:col-span-2  (or min-h larger value text-3xl)
  others:      col-span-1 each
```

### 7.2 Cards

| # | Label | Field (conceptual) | Sentiment | Format |
|---|-------|--------------------|-----------|--------|
| 1 | **XIRR** | `xirr` | pos / neg / flat | `+14.82%` (2 dp); **text-3xl font-semibold** |
| 2 | Total invested | `total_invested` | none | `₹12,00,000` en-IN |
| 3 | Final value | `final_value` | none (or pos/neg vs invested as delta) | `₹18,42,310.25` |
| 4 | Absolute gain | `final_value - total_invested` | pos/neg | `+₹6,42,310` + optional `+53.5%` delta line |
| 5 | Max drawdown | `max_drawdown` on MV path | always neg when set | `−18.40%` |
| 6 | # contributions | `n_contributions` | none | `36 SIPs` |

Optional stretch metrics (if API returns): CAGR-like path metric, volatility — **never replace XIRR**.

### 7.3 XIRR card special treatment

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4
  optional: ring-1 ring-[var(--accent)]/20 when source=upstox
label: "XIRR" + hint tooltip
  “Annualized return on SIP cashflows (contributions + terminal value). Fixture tol ≤ 1e-4.”
value: text-3xl font-semibold tabular-nums + sentiment color
sublabel: "Jan 2021 → Dec 2024 · day 1 → next session"
```

Null XIRR: `—` + “Need ≥ 2 cashflows”.

### 7.4 Reuse

- `MetricCard` for secondary KPIs (`size="default"`).
- Hero may be a `MetricCard` with larger value class or thin wrapper `XirrHeroCard`.

---

## 8. Equity / market-value curve

**Not** the same as v0 base-100 NAV story — this is **portfolio market value** (and optionally invested capital) over time.

### 8.1 Panel

| Detail | Spec |
|--------|------|
| Component | Reuse `PerformanceChart` `variant="equity"` **or** `SipEquityChart` if dual series needs different Y labels |
| Title | “Portfolio value” |
| Subtitle | “Market value of SIP units · zero costs” |
| Height | 360px desktop |
| Series A | Portfolio MV — `chart.portfolio` `#60A5FA` line |
| Series B (recommended) | Cumulative invested — `chart.benchmark` / secondary `#A78BFA` **dashed** |
| Series C (optional P3) | Benchmark index SIP — later |
| X | date |
| Y | INR (`₹` ticks compact: `₹2.5L`) |
| Tooltip | Date · MV · Cum invested · optional units total |
| Legend | Portfolio value · Invested |
| Empty | “No series — run a backtest” |

**Do not** color the MV line green/red from XIRR. Structural series colors only; P&L stays on KPIs/tables.

Panel chrome:

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4
header: flex justify-between items-center mb-3
```

### 8.2 Optional drawdown under curve

| Detail | Spec |
|--------|------|
| Show when | API or client can compute peak-to-trough on MV |
| Height | 220–260px |
| Styling | Same as Performance page: `pnl.negative` area |
| Title | “Drawdown (market value)” |
| syncId | Share with equity chart when both present |

---

## 9. Contribution & cashflows

Two complementary tables; default **tabs** to save vertical space:

```
Tabs: [ Cashflows ] [ By holding ] [ SIP schedule ]
```

Tab chrome: underline or chip group; active = accent text + bottom border.

### 9.1 Cashflows (primary for XIRR trust)

| Column | Align | Format |
|--------|-------|--------|
| Date | left | `YYYY-MM-DD` |
| Type | left | Badge: `Contribution` / `Terminal` / `Residual` |
| Amount | right | Signed INR; contributions negative or shown as outflow with convention matching engine export |
| Note | left | e.g. “SIP day adjusted +1 session” |

- Sort: date ascending.
- Terminal row emphasize with slightly stronger text weight.
- Footer: sum of contributions, terminal value.

**Sign convention (display):** Prefer engine’s export convention; document in assumptions. UI must match API (e.g. contributions as negative cashflows for XIRR). Show helper: “Outflows negative · terminal positive” if that is the model.

### 9.2 By holding (contribution / allocation result)

| Column | Align | Format | Sentiment |
|--------|-------|--------|-----------|
| Symbol | left | mono | — |
| Name | left | truncate | — |
| Weight (target) | right | `12.5%` | none |
| Units (end) | right | 4 dp or integer policy | none |
| MV (end) | right | INR | none |
| Contrib to gain | right | INR or % of total gain | pos/neg |

- Default sort: contrib desc.
- Micro bar optional (accent fill, not P&L green for weight).
- Empty: hide tab if API omits holding attribution in MVP.

### 9.3 SIP schedule (audit)

| Column | Align | Notes |
|--------|-------|-------|
| Calendar day | left | Requested DOM |
| Actual session | left | After next-trading-day rule |
| Amount deployed | right | INR |
| Adjusted? | center | Chip `Yes` warning muted if shifted |

Builds trust in ADR 004 day rule.

### 9.4 Table styling

Reuse holdings/performance dense table tokens:

- Sticky header `bg-[var(--bg-muted)]`
- `tabular-nums` on all money/%
- Hover `bg-[var(--bg-hover)]`
- Max height `max-h-[360px] overflow-auto` for long SIP histories

---

## 10. Methodology warnings (`#methodology`)

Collapsible panel — default **collapsed** after first successful run; **expanded** on first visit or when `data_source=sample`.

### 10.1 Content (fixed MVP copy blocks)

| Warning | Severity | Body |
|---------|----------|------|
| Zero costs | info | “MVP assumes zero brokerage, STT, stamp, slippage, and expense drag. Buys at documented session price for full SIP amount.” |
| SIP day rule | info | “Contributions use a fixed calendar day of month. If that day is not a trading session, invest on the next session with available prices.” |
| XIRR primary | info | “Headline performance is XIRR on cashflows (contributions + terminal). Path CAGR/NAV-style metrics are secondary and are not the SIP success criterion.” |
| Not v0 rebalance NAV | warning | “This is not the Dashboard/Performance weight-NAV rebalance backtest. Do not compare XIRR directly to index-style total return without care.” |
| Sample prices | warning | “Sample/synthetic prices are for demos only. Not live market SIP performance. Configure Upstox env + sync for real history.” |
| Upstox sole source | info | “Equity/ETF history for real runs comes only from Upstox-cached curated data. No yfinance / bhavcopy / multi-vendor fill.” |

### 10.2 Visual

```
┌─ Methodology & assumptions  [▾] ───────────────────────┐
│ ⚠ Sample prices — demo only                            │  ← only if sample
│ · Zero transaction costs (MVP)                         │
│ · SIP day → next trading day                           │
│ · XIRR primary (fixture tol 1e-4 engine-side)          │
│ · Not v0 NAV rebalance                                 │
└────────────────────────────────────────────────────────┘
```

- Container: `rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]`
- Warning rows: left border `border-l-2 border-[var(--risk-warning)]` when severity warning
- Info rows: muted bullet list `text-xs text-[var(--text-secondary)]`
- Place: **config column bottom** always; **repeat compact strip** under KPIs when sample

---

## 11. Assumptions footer (results)

Micro text under tables:

```
text-[11px] text-[var(--text-muted)]

SIP day: calendar D → next session · Costs: 0 · Currency: INR
Price field: close (or API-documented) · Source: upstox|sample
Range: 2021-01-01 → 2024-12-31 · Generated: local run (no curated write)
```

Align with API `notes` / `assumptions` when present.

---

## 12. Data contract (map to API — conceptual P2)

Frontend formats; API returns fractions for rates (`0.1482` → `+14.82%`).

| UI | API / concept | Notes |
|----|---------------|-------|
| Strategy list | `GET /strategies` or file-backed list | Optional if only POST body |
| Load smallcase seed | `GET /smallcases`, `GET /smallcases/{id}/holdings` | Weights as fractions |
| Run | `POST /sip/backtest` (name TBD backend) | Body: strategy or inline constituents, amount, day, start, end |
| XIRR + KPIs | `result.xirr`, `total_invested`, `final_value`, `max_drawdown`, `n_contributions` | |
| MV series | `result.market_value_series[]` `{date, value}` | |
| Invested series | `result.invested_series[]` optional | |
| Cashflows | `result.cashflows[]` | |
| Holding contrib | `result.holdings[]` optional MVP | |
| Schedule audit | `result.sip_dates[]` optional | |
| Source | `result.data_source`: `upstox` \| `sample` | **Required for banner** |
| Warnings | `result.warnings[]` | Surface in methodology / banner |
| Export | Client serialize response **or** `GET` export URL | CSV/JSON |

**Do not** call `POST /backtest` (v0 rebalance) for SIP Lab results.

### Upstox status

| UI | API |
|----|-----|
| Global banner | Existing `GET` upstox status (configured flag, years) |
| Result chip | `data_source` on SIP response |

---

## 13. Interactions

1. **Edit strategy / SIP params** → dirty state; results show stale overlay optional: “Params changed — re-run to update” (muted banner).
2. **Run backtest** → POST; loading; replace results; scroll results into view on mobile.
3. **Export** → download cashflows CSV / summary JSON from last response.
4. **Equal weight toggle** → recompute displayed weights; mark dirty.
5. **Add/remove symbol** → validate sum; instrument resolve async if API supports.
6. **Methodology expand** → localStorage `sf-sip-methodology-open` optional.
7. **Theme toggle** → charts re-read CSS variables (same as v0).

No live order placement. No broker OAuth UI in this version (token is env/CLI).

---

## 14. Component inventory (new vs reuse)

| Component | Status | Notes |
|-----------|--------|-------|
| `AppShell` nav item | extend | Add SIP Lab link |
| `DataSourceBanner` | reuse | Global |
| `MetricCard` | reuse | Secondary KPIs |
| `PerformanceChart` | reuse / extend | MV + invested series |
| `EmptyState` / `ErrorBanner` | reuse | |
| `StrategyEditor` | **new** | Form + table |
| `SipParamsForm` | **new** | Amount, DOM, dates, CTA |
| `XirrHeroCard` | **new** or MetricCard variant | Emphasized XIRR |
| `SipResultsPanel` | **new** | State machine wrapper |
| `SipCashflowTable` | **new** | |
| `SipContributionTable` | **new** | Optional MVP |
| `MethodologyPanel` | **new** | Collapsible warnings |
| `DataSourceChip` | **new** (tiny) | Result-scoped source |

---

## 15. Tailwind structure sketch

```tsx
// structural only — not full implementation
<main className="mx-auto max-w-[1440px] px-6 py-6 flex flex-col gap-6">
  <header className="flex flex-col gap-1">
    <h1 className="text-xl font-semibold">SIP Lab</h1>
    <p className="text-sm text-[var(--text-secondary)]">
      Monthly SIP into a custom equity/ETF basket · XIRR primary · Upstox history
    </p>
  </header>

  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    {/* Config */}
    <aside className="lg:col-span-4 flex flex-col gap-6 lg:sticky lg:top-20 lg:self-start">
      {/* StrategyEditor */}
      {/* SipParamsForm + Run + Export */}
      {/* MethodologyPanel */}
    </aside>

    {/* Results */}
    <section className="lg:col-span-8 flex flex-col gap-6 min-w-0">
      {/* DataSourceChip */}
      {/* KPI strip: XIRR hero + secondaries */}
      {/* PerformanceChart MV (+ invested) */}
      {/* optional drawdown */}
      {/* tabs: cashflows / holdings / schedule */}
      {/* assumptions footer */}
    </section>
  </div>
</main>
```

---

## 16. Color & type quick reference (finance dark)

| Use | Token / class |
|-----|----------------|
| App / cards | `--bg-app` / `--bg-surface` / `--border-default` |
| XIRR / gains | `--pnl-pos` with explicit `+` |
| Losses / DD | `--pnl-neg` |
| Sample warning | `--risk-warning` |
| Run CTA / nav active | `--accent` (structure, not P&L) |
| Chart MV | `--chart-portfolio` |
| Chart invested | `--chart-benchmark` dashed |
| Labels | `text-[var(--text-secondary)]` |
| Values | `tabular-nums` + consistent decimals |

Typography: Inter (or system stack already in app); KPI hero 30–32px; body 14px; micro 11–12px.

---

## 17. Accessibility

- Form labels associated with inputs; errors announced (`aria-invalid`, `aria-describedby`).
- Run button `aria-busy` while loading.
- XIRR and P&L never color-only — signs required.
- Tables: `<th scope="col">`; sort buttons keyboard accessible.
- Focus rings on all controls (`ring-[var(--accent)]/50`).
- Sticky config must not trap focus; mobile order = form then results.

---

## 18. Acceptance (SIP Lab UI)

- [ ] Nav includes **SIP Lab** → `/sip-lab`
- [ ] Strategy editor: load/edit constituents + weights/equal mode with validation
- [ ] SIP params: amount, day-of-month (1–28), start/end or “to latest”
- [ ] Helper text documents **calendar day → next trading day**
- [ ] **Run backtest** posts SIP endpoint (not v0 `/backtest` rebalance)
- [ ] **XIRR** is the largest, first-read KPI; secondary size/risk metrics present
- [ ] Equity chart shows portfolio **market value** (+ cumulative invested if available)
- [ ] Cashflow table matches engine export convention; export CSV/JSON works
- [ ] Contribution-by-holding section when API provides data; else omitted cleanly
- [ ] Methodology panel covers zero costs, day rule, XIRR primary, not-v0-NAV
- [ ] **Upstox vs sample** visible globally and on result (`data_source`)
- [ ] Sample runs never look like live market claims (warning badge + methodology)
- [ ] No Coin / Kite / portfolio-import screens this version
- [ ] Dark default tokens; light mode still readable
- [ ] Loading / empty / error states implemented without layout collapse

---

## 19. Out of scope (this version)

| Item | When |
|------|------|
| Coin / MF import UI | Later (after equity path) |
| Kite holdings import / live-vs-SIP compare | Phase 4 |
| Cost model toggles (brokerage, STT) | P3 optional |
| Benchmark index SIP overlay | P3 |
| Multi-strategy compare grid | P3 |
| Live trading / order tickets | Never (product non-goal) |
| OAuth UI for Upstox inside web app | Optional later; MVP is env + CLI |
| Treating Dashboard NAV as SIP performance | Forbidden |

---

## 20. References

- Design system: [design-system.md](../design-system.md)
- Shared components: [components.md](../components.md)
- v0 pages (patterns only): [dashboard.md](./dashboard.md) · [performance.md](./performance.md) · [holdings.md](./holdings.md)
- PRD / ADRs: [prd-sip-lab.md](../../product/prd-sip-lab.md) · [004](../../decisions/004-sip-lab-prd-decisions.md) · [005](../../decisions/005-upstox-sole-market-data.md)
- Upstox: [upstox.md](../../integrations/upstox.md)
- Backlog item: **P2-04** in [backlog-phase-0-2.md](../../product/backlog-phase-0-2.md)
