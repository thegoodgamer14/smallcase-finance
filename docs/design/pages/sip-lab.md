# SIP Lab — Page Spec (`/sip-lab`)

**Status:** Implementation-ready (P2 UI)  
**Audience:** Frontend agent  
**Product:** SIP Lab / Basket Backtest Engine  
**Job to be done:** *External visitor (or founder) understands and runs a monthly SIP basket backtest without prior product knowledge — and trusts the XIRR.*  
**Route:** `/sip-lab` → `app/sip-lab/page.tsx`  
**Shell:** Global `AppShell` (top bar + left nav). See [ui.md](../../architecture/ui.md).  
**Visual language:** [design-system.md](../design-system.md) · [components.md](../components.md)  
**External copy / glossary:** [sip-lab-external.md](../copy/sip-lab-external.md)  
**Product rules:** [PRD](../../product/prd-sip-lab.md) · [ADR 004](../../decisions/004-sip-lab-prd-decisions.md) · [ADR 005](../../decisions/005-upstox-sole-market-data.md)

| Binding rule | Value |
|--------------|-------|
| Primary metric | **XIRR** (not v0 weight-NAV total return) |
| SIP day | Fixed calendar day-of-month → **next trading day** if market closed |
| Costs | **Zero** MVP |
| History | **Upstox only** for real claims; sample/synthetic OK if labeled **demo** |
| API | `POST /sip/backtest` only — **never** `POST /backtest` (v0 rebalance) |

---

## 0. First-time visitor journey (top → bottom)

Order is fixed. Desktop-first; config sticky left, results scroll right (≥1280). On narrower screens, stack in this same section order.

| # | Section | Anchor | Purpose for first-timer |
|---|---------|--------|-------------------------|
| 1 | **Hero** | `#hero` | Name the product, one job, primary metric (XIRR) in plain language |
| 2 | **Data source chip strip** | `#data-source` | Immediately show demo vs Upstox so numbers are not misread |
| 3 | **Configure** | `#configure` | Basket + SIP amount/day/dates + **Run backtest** |
| 4 | **Methodology accordion** | `#methodology` | Expandable “How this works” (zero costs, day rule, XIRR, not v0 NAV) |
| 5 | **Results** | `#results` | Empty → loading → error → success (XIRR hero, invested vs final, charts, tables) |
| 6 | **How to read results** | `#how-to-read` | Plain-language guide under results (always visible after first paint of results column) |
| 7 | **Assumptions footer** | `#assumptions` | Micro audit line: day rule, costs 0, source field, source, range |

```
┌─ App shell ──────────────────────────────────────────────────────────────────┐
│ DataSourceBanner (global)                                                    │
│ TopBar: Logo · Theme  (hide global RangeChips on this route)                 │
├─ LeftNav ─┬─ Main max-w-[1440px] mx-auto px-6 py-6 gap-6 ────────────────────┤
│ Dashboard │                                                                  │
│ Holdings  │  §1 HERO                                                         │
│ Perf      │  §2 DATA SOURCE (page-level chip; result chip repeats after run) │
│ SIP Lab ● │                                                                  │
│           │  grid 4+8                                                        │
│           │  ┌ CONFIG (sticky) ──────┐  ┌ RESULTS ────────────────────────┐  │
│           │  │ §3 Strategy + SIP     │  │ Empty | Loading | Error | Data  │  │
│           │  │ Run · Export          │  │ XIRR KPIs · MV chart · tables   │  │
│           │  │ §4 Methodology ▾      │  │ §6 How to read                  │  │
│           │  └───────────────────────┘  │ §7 Assumptions footer           │  │
│           │                             └─────────────────────────────────┘  │
└───────────┴──────────────────────────────────────────────────────────────────┘
```

**Vertical rhythm:** section `gap-6`; form fields `gap-3`–`gap-4`.

### Breakpoints

| Width | Behavior |
|-------|----------|
| ≥1280 | `grid-cols-12`: config `col-span-4` sticky `top-20`; results `col-span-8` |
| 768–1279 | Single column: hero → data source → config → methodology → results |
| <768 | Full stack; tables `overflow-x-auto`; CTA full-width |

---

## 1. Exact copy strings (locked)

Frontend must use these strings (or the glossary file) — do not improvise marketing.

### 1.1 Hero

| Key | Copy |
|-----|------|
| `hero.title` | `SIP Lab` |
| `hero.subtitle` | `See what a monthly SIP into a stock/ETF basket would have returned.` |
| `hero.metric_line` | `Primary result: XIRR — the annualized return on every contribution plus your ending portfolio value.` |
| `hero.scope_line` | `Equities & ETFs only · Zero transaction costs in this version · Not live trading` |
| `hero.link_methodology` | `How SIP Lab works` → `#methodology` |
| `hero.link_glossary` | `Glossary` → can open methodology panel section or tooltip set; optional |

**Typography**

```
h1: text-xl font-semibold text-[var(--text-primary)]
subtitle: text-sm text-[var(--text-secondary)] max-w-2xl
metric_line: text-sm text-[var(--text-primary)] mt-1
scope_line: text-xs text-[var(--text-muted)] mt-1
```

No marketing illustration. No “Invest now”.

### 1.2 XIRR definition (one-liner)

| Key | Copy |
|-----|------|
| `xirr.definition` | `XIRR is the single annualized rate that makes all your SIP cash outflows and the final portfolio value balance out over time.` |
| `xirr.tooltip` | `Uses contribution dates and amounts plus terminal market value. Engine fixture tolerance ≤ 0.0001. Not the same as a simple “total return” on a rebalanced NAV index.` |
| `xirr.kpi_label` | `XIRR` |
| `xirr.null` | `Need at least two cashflows` |
| `xirr.sublabel_template` | `{start_label} → {end_label} · SIP day {day} → next session if closed` |

### 1.3 Invested vs final value

| Key | Copy |
|-----|------|
| `invested.label` | `Total invested` |
| `invested.hint` | `Sum of all monthly SIP contributions (cash you put in).` |
| `final.label` | `Final value` |
| `final.hint` | `Market value of units held at the end date (what the basket is worth).` |
| `gain.label` | `Absolute gain` |
| `gain.hint` | `Final value minus total invested. Positive means the basket grew more than cash put in.` |
| `compare.helper` | `Invested is cash in. Final value is what those units are worth. XIRR annualizes the path between them.` |

### 1.4 Demo vs Upstox warning

| Key | When | Copy |
|-----|------|------|
| `source.upstox.chip` | `data_source === 'upstox'` | `Prices: Upstox (cached)` |
| `source.sample.chip` | `data_source === 'sample'` | `Demo / sample prices — not live market SIP performance` |
| `source.partial.chip` | partial coverage | `Partial Upstox coverage · some symbols sample or missing` |
| `source.sample.banner` | sample result | `These results use demo or sample prices. Do not treat them as real market SIP performance. Connect Upstox and sync history for real claims.` |
| `source.upstox.banner` | upstox result | `Prices from Upstox-cached curated history. Sole market-data source for real runs.` |
| `source.pre_run.upstox` | token present | `Run will use curated prices (Upstox sync path).` |
| `source.pre_run.sample` | no token / sample only | `No Upstox token configured — run will use demo/sample prices.` |
| `source.global_note` | always (hero or chip strip) | `Real history: Upstox only. Sample data is labeled Demo.` |

**Visual rules (ADR 005)**

- Sample: `Badge warning` + optional left stripe on XIRR card `border-l-2 border-[var(--risk-warning)]`
- Upstox: `Badge info` (accent subtle)
- Never show tokens/keys
- Never imply sample = Upstox

### 1.5 Configure / CTA / empty / error (quick index)

| Key | Copy |
|-----|------|
| `config.strategy_title` | `Basket` |
| `config.sip_title` | `SIP parameters` |
| `config.amount_label` | `Monthly amount` |
| `config.day_label` | `SIP day (calendar)` |
| `config.day_helper` | `If that day is not a trading session, we invest on the next session with prices.` |
| `config.start_label` | `Start date` |
| `config.end_label` | `End date` |
| `config.end_latest` | `To latest available price` |
| `config.allocation_custom` | `Custom weights` |
| `config.allocation_equal` | `Equal weight` |
| `cta.run` | `Run backtest` |
| `cta.running` | `Running…` |
| `cta.export` | `Export` |
| `cta.export_csv` | `Cashflows CSV` |
| `cta.export_json` | `Summary JSON` |
| `stale.banner` | `Parameters changed — re-run to update results.` |

Full empty/error/loading strings: **§5**.

### 1.6 How to read results

| Key | Copy |
|-----|------|
| `howto.title` | `How to read these results` |
| `howto.xirr` | `Start with XIRR. It answers: “If I had SIP’d this amount every month, what annualized return would I have earned?”` |
| `howto.invested_final` | `Total invested is cash contributed. Final value is what the holdings are worth at the end. The gap is absolute gain or loss — not annualized.` |
| `howto.chart` | `The portfolio value line is market value of units over time. The dashed line (if shown) is cumulative cash invested.` |
| `howto.cashflows` | `The cashflow table is what XIRR uses: each SIP (outflow) and the terminal value (inflow). Sign convention matches the engine export.` |
| `howto.drawdown` | `Max drawdown is the worst peak-to-trough drop in portfolio market value — path risk, not XIRR.` |
| `howto.not_v0` | `Dashboard and Performance show weight-based NAV rebalance demos. Those are not SIP XIRR. Do not compare them directly without care.` |

### 1.7 Methodology accordion body (MVP fixed blocks)

| Id | Severity | Title | Body |
|----|----------|-------|------|
| `zero_costs` | info | `Zero costs` | `This version assumes zero brokerage, STT, stamp duty, slippage, and expense drag. Each SIP buys at the session close (or documented price field) for the full monthly amount.` |
| `sip_day` | info | `SIP day rule` | `Contributions use a fixed calendar day of the month. If markets are closed that day, the SIP invests on the next trading day with available prices.` |
| `xirr_primary` | info | `XIRR is primary` | `Headline performance is XIRR on cashflows (contributions + terminal value). Path metrics (drawdown, market-value curve) support the story but do not replace XIRR.` |
| `not_v0` | warning | `Not the Dashboard NAV backtest` | `SIP Lab is not the weight-NAV rebalance backtest used on Dashboard/Performance. Do not treat those total returns as SIP XIRR.` |
| `sample` | warning | `Demo prices` | `Sample or synthetic prices are for demos only — not live market SIP performance. Configure Upstox and sync for real history.` |
| `upstox_only` | info | `Upstox only` | `Equity/ETF history for real runs comes only from Upstox-cached curated data. No yfinance, bhavcopy, or multi-vendor fill.` |

**Accordion chrome**

- Title: `How SIP Lab works`
- Default: **expanded** on first visit or when `data_source=sample`; **collapsed** after first successful Upstox run (optional `localStorage` key `sf-sip-methodology-open`)
- Place: config column bottom; compact sample warning strip also under KPIs when sample

---

## 2. Nav order & shell behavior

### 2.1 Left nav + mobile bottom nav (`AppShell` `NAV`)

| Order | Label | Route | Icon (Lucide) |
|------:|-------|-------|---------------|
| 1 | Dashboard | `/` | `LayoutDashboard` |
| 2 | Holdings | `/holdings` | `PieChart` |
| 3 | Performance | `/performance` | `Activity` |
| 4 | **SIP Lab** | `/sip-lab` | `FlaskConical` |

Active: existing `bg-[var(--accent-subtle)] text-[var(--accent)]`.  
Mobile bottom nav: same four items (label may truncate to “SIP” if space tight — prefer full “SIP Lab”).

### 2.2 Top bar on `/sip-lab`

| Control | Behavior |
|---------|----------|
| Brand | Unchanged; optional product rename later — keep current brand string |
| SmallcaseSelect | **Optional seed only** for “load basket from smallcase”; primary strategy picker lives in page form |
| RangeChips / CustomRange | **Hide** in left-nav range panel when `pathname` starts with `/sip-lab` (SIP uses form start/end) |
| As-of badge | Keep if curated prices have as-of |
| ThemeToggle | Unchanged |
| DataSourceBanner | Always on (global) |

### 2.3 Dashboard callout → SIP Lab

Add a compact callout on **Dashboard** (`/`) so first-time visitors discover SIP Lab without hunting nav.

**Placement:** Below context strip / above KPI row (or immediately under KPI row if fold is tight). Full width of main content.

| Key | Copy |
|-----|------|
| `dash_callout.title` | `Try SIP Lab` |
| `dash_callout.body` | `Dashboard shows weight-based NAV for this smallcase. SIP Lab answers a different question: monthly cash SIPs into a basket, with XIRR as the result.` |
| `dash_callout.cta` | `Open SIP Lab` |
| `dash_callout.href` | `/sip-lab` |

**Visual**

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]
px-4 py-3 flex flex-wrap items-center justify-between gap-3
title: text-sm font-medium
body:  text-xs text-[var(--text-secondary)] max-w-xl
cta:   secondary or primary small button / Link
```

Optional dismiss: `localStorage` `sf-sip-dash-callout-dismissed` — not required for MVP.

**Do not** put SIP XIRR on Dashboard KPI row in this version (separate product surfaces).

---

## 3. Configure column

### 3.1 Strategy editor (`StrategyEditor`) — new

| Mode | UX |
|------|-----|
| Load strategy | Select from `GET /strategies` or file-backed list when available |
| Load from smallcase | Seed from `GET /smallcases` + holdings (weights as fractions) |
| Inline edit | Symbol + weight table; equity/ETF only |

**Card title copy:** `Basket`

Constituent columns: Symbol · Name · Weight % · remove.  
Equal-weight mode: show computed weights read-only.  
Weight sum ≠ 100% (±0.1%): warning badge + disable Run.  
Max ~8 rows visible, `max-h-[280px] overflow-y-auto`.

```
StrategyEditor {
  strategyId?: string
  constituents: { symbol: string; name?: string; weight: number }[]
  allocationMode: 'custom_weights' | 'equal_weight'
  instrumentStatus?: { symbol: string; resolved: boolean }[]
  onChange: (patch) => void
  loading?: boolean
  readOnly?: boolean
}
```

### 3.2 SIP parameters (`SipParamsForm`) — new

| Field | Control | Default | Validation |
|-------|---------|---------|------------|
| `amount` | Number + ₹ prefix | `10000` | > 0 |
| `day_of_month` | 1–28 | `1` | 1–28 MVP |
| `start_date` | Date | e.g. 3y ago | ≤ end |
| `end_date` | Date or “to latest” | latest | ≥ start |
| `allocation_mode` | Radio if not only on strategy | custom / equal | single source of truth |

**CTA**

| State | Visual / copy |
|-------|----------------|
| Ready | Primary full-width: `Run backtest` |
| Invalid | Disabled `opacity-50` |
| Running | Spinner + `Running…`; `aria-busy` |
| Export | Secondary; disabled until success; menu CSV/JSON |

Pre-run source line under CTA: `source.pre_run.*` from §1.4.

---

## 4. Results panel — state machine

States: `idle` → `loading` → `success` | `error`. Dirty params after success → optional stale banner without clearing last result.

### 4.1 Idle / empty (no run yet)

Reuse `EmptyState`:

| Prop | Value |
|------|-------|
| `title` | `Run a SIP backtest` |
| `description` | `Pick a basket, set monthly amount and dates, then run. You’ll get XIRR, portfolio value over time, and the cashflows behind the number.` |
| `action` | Optional muted text: `Results appear here after you run.` |

Container: fill results column min-height ~360px so layout doesn’t collapse.

### 4.2 Loading

| Element | Treatment |
|---------|-----------|
| KPI strip | Skeleton: 1 large XIRR block + 4 small `MetricCard` loading |
| Chart | `h-[360px] animate-pulse rounded-lg bg-[var(--bg-muted)]` |
| Tables | 5 skeleton rows |
| How-to-read | Keep visible (static copy) |
| Config | Interactive; Run stays `Running…` |

### 4.3 Error

Reuse `ErrorBanner` at top of results column (`role="alert"`).

| Kind | `message` pattern |
|------|-------------------|
| 4xx config | `Invalid SIP config: {detail}` |
| Missing prices | `Not enough price history for {symbols}. Sync Upstox or shorten the date range.` |
| Engine | `Backtest failed. Retry or check API logs.` |
| Network | `Can’t reach the API at {base}. Is the server running?` |
| Timeout | `Backtest timed out. Try a shorter range or fewer symbols.` |

`onRetry` → re-POST last valid body when safe.  
Optional: keep last good success below banner.

### 4.4 Success

1. Result-scoped `DataSourceChip` (§1.4)  
2. KPI strip — XIRR hero first  
3. Portfolio value chart (+ invested dashed)  
4. Optional drawdown  
5. Tabs: Cashflows · By holding · SIP schedule  
6. How to read (§1.6)  
7. Assumptions footer  

URL query (no secrets):

```
?strategy=<id>&amount=10000&day=1&start=2021-01-01&end=2024-12-31
```

---

## 5. KPI strip — XIRR primary

**Hierarchy:** XIRR is largest / first-read. Never lead with v0 NAV total return.

```
grid grid-cols-2 lg:grid-cols-6 gap-4
  XIRR: col-span-2  value text-3xl font-semibold tabular-nums
  others: col-span-1 each  MetricCard size default|compact
```

| # | Label (copy key) | Source | Sentiment | Format |
|---|------------------|--------|-----------|--------|
| 1 | `XIRR` | `result.xirr` | pos/neg/flat | `+14.82%` (2 dp) |
| 2 | `Total invested` | `total_invested` | none | `₹12,00,000` en-IN |
| 3 | `Final value` | `final_value` | none | `₹18,42,310.25` |
| 4 | `Absolute gain` | final − invested | pos/neg | `+₹6,42,310` + optional `%` delta |
| 5 | `Max drawdown` | MV path | neg when set | `−18.40%` |
| 6 | Contributions | `n_contributions` | none | `36 SIPs` |

XIRR card: label + tooltip `xirr.tooltip`; sublabel from template; null → `—` + `xirr.null`.  
Sample source: warning left border on hero card.

**Reuse:** secondary cards = `MetricCard`. Hero = `MetricCard` with larger value class **or** thin `XirrHeroCard` wrapper.

---

## 6. Charts & tables

### 6.1 Portfolio value curve

| Detail | Spec |
|--------|------|
| Reuse | `PerformanceChart` `variant="equity"` **or** `SipEquityChart` if dual Y labels need it |
| Title | `Portfolio value` |
| Subtitle | `Market value of SIP units · zero costs` |
| Height | 360px |
| Series A | Portfolio MV — `var(--chart-portfolio)` solid |
| Series B | Cumulative invested — `var(--chart-benchmark)` **dashed** |
| Y | INR compact ticks (`₹2.5L`) |
| Tooltip | Date · MV · Cum invested |
| Empty | `No series — run a backtest` |

Do **not** color MV line green/red from XIRR. P&L stays on KPIs/tables.

### 6.2 Drawdown (optional)

Title: `Drawdown (market value)`. Height 220–260px. `variant="drawdown"` / `pnl.negative` area. `syncId` with equity chart.

### 6.3 Tabs

```
[ Cashflows ] [ By holding ] [ SIP schedule ]
```

| Tab | Columns (summary) |
|-----|-------------------|
| Cashflows | Date · Type (Contribution / Terminal) · Amount (engine sign) · Note (e.g. day adjusted) |
| By holding | Symbol · Name · Weight · Units end · MV end · Contrib to gain |
| SIP schedule | Calendar day · Actual session · Amount · Adjusted? chip |

Dense table tokens from design system; sticky header; `max-h-[360px] overflow-auto`.  
Cashflow helper under table if signs are XIRR-style: `Outflows negative · terminal positive` (only if engine uses that convention).

---

## 7. Component inventory (map to existing)

### 7.1 Reuse as-is

| Component | Path | SIP Lab use |
|-----------|------|-------------|
| `AppShell` | `components/shell/AppShell.tsx` | Extend `NAV` (+ hide range panel on `/sip-lab`) |
| `DataSourceBanner` | `components/shell/DataSourceBanner.tsx` | Global demo/config banner |
| `ThemeToggle` | `components/shell/ThemeToggle.tsx` | Unchanged |
| `MetricCard` | `components/kpis/MetricCard.tsx` | Total invested, final value, gain, max DD, # SIPs; optional XIRR if sized up |
| `PerformanceChart` | `components/charts/PerformanceChart.tsx` | MV equity + optional drawdown |
| `EmptyState` | `components/feedback/EmptyState.tsx` | Idle results |
| `ErrorBanner` | `components/feedback/ErrorBanner.tsx` | Run failures |
| `SmallcaseSelect` | `components/smallcase/SmallcaseSelect.tsx` | Optional basket seed only |
| Format helpers | `lib/format.ts` | INR, %, dates |
| Sentiment helpers | `lib/sentiment.ts` | XIRR / gain / DD colors |

### 7.2 New (SIP-specific)

| Component | Responsibility |
|-----------|----------------|
| `StrategyEditor` | Basket load/edit, weights, validation |
| `SipParamsForm` | Amount, day, dates, Run/Export, pre-run source line |
| `XirrHeroCard` | Emphasized XIRR (or MetricCard + `className`) |
| `SipResultsPanel` | idle/loading/error/success state machine |
| `DataSourceChip` | Result-scoped sample/Upstox chip |
| `MethodologyPanel` | Accordion §1.7 |
| `HowToReadPanel` | Static §1.6 under results |
| `SipCashflowTable` | Cashflows tab |
| `SipHoldingTable` | By-holding tab (omit tab if API empty) |
| `SipScheduleTable` | Schedule audit tab |
| `SipDashCallout` | Dashboard → SIP Lab strip (§2.3) |
| `SipEquityChart` | Only if `PerformanceChart` cannot dual-series MV + invested cleanly |

### 7.3 Do not reuse for wrong semantics

| Avoid | Why |
|-------|-----|
| `POST /backtest` client helper | v0 rebalance NAV — wrong engine |
| Dashboard KPI set as SIP story | NAV/CAGR ≠ SIP XIRR |
| Global RangeChips driving SIP window | Form owns start/end |
| Coin / Kite import UI | Out of scope this version |

### 7.4 File map suggestion

```
app/sip-lab/page.tsx
components/sip/
  StrategyEditor.tsx
  SipParamsForm.tsx
  XirrHeroCard.tsx
  SipResultsPanel.tsx
  DataSourceChip.tsx
  MethodologyPanel.tsx
  HowToReadPanel.tsx
  SipCashflowTable.tsx
  SipHoldingTable.tsx
  SipScheduleTable.tsx
  SipDashCallout.tsx   // also import on app/page.tsx
lib/api.ts             // postSipBacktest → POST /sip/backtest
```

---

## 8. Data contract (UI ↔ API)

| UI | API concept |
|----|-------------|
| Run | **`POST /sip/backtest`** only |
| XIRR + KPIs | `xirr`, `total_invested`, `final_value`, `max_drawdown`, `n_contributions` |
| Series | `market_value_series[]`, optional `invested_series[]` |
| Tables | `cashflows[]`, optional `holdings[]`, optional `sip_dates[]` |
| Source | **`data_source`: `upstox` \| `sample`** required |
| Warnings | `warnings[]` → methodology / banners |
| Rates | API fractions (`0.1482`) → UI `+14.82%` |

Rates/XIRR: presenters format; never dump raw API into KPI value.

---

## 9. Accessibility

- Labels on all inputs; errors via `aria-invalid` / `aria-describedby`
- Run: `aria-busy` while loading
- XIRR / P&L: sign + color (never color alone)
- Tables: `<th scope="col">`
- Focus rings: `ring-[var(--accent)]/50`
- Mobile order: hero → configure → results (no focus trap in sticky aside)

---

## 10. Acceptance checklist (UI)

- [ ] Nav order: Dashboard · Holdings · Performance · **SIP Lab** (`/sip-lab`)
- [ ] Dashboard shows **Try SIP Lab** callout with locked copy → `/sip-lab`
- [ ] Hero uses locked title/subtitle/metric_line/scope_line
- [ ] XIRR definition one-liner + tooltip present on hero KPI
- [ ] Invested vs final labels/hints match §1.3
- [ ] Demo vs Upstox chip + sample banner match §1.4
- [ ] Configure: basket, amount, day 1–28, start/end, day helper copy
- [ ] **Run backtest** → `POST /sip/backtest` only (never v0 `/backtest`)
- [ ] XIRR is largest first KPI; secondary size/risk cards present
- [ ] MV chart (+ invested if available); cashflow table; export when success
- [ ] Methodology accordion covers zero costs, day rule, XIRR, not-v0, sample, Upstox
- [ ] How-to-read section uses §1.6 strings
- [ ] Empty / loading / error states without layout collapse
- [ ] Global range chips hidden on SIP Lab route
- [ ] No Coin / Kite / live order UI
- [ ] Dark default; light still readable

---

## 11. Out of scope (this version)

| Item | When |
|------|------|
| Coin / MF | Later |
| Kite holdings import / live-vs-SIP | Phase 4 |
| Cost model toggles | P3 |
| Benchmark index SIP overlay | P3 |
| Multi-strategy compare | P3 |
| Live trading | Never |
| Treating Dashboard NAV as SIP performance | Forbidden |

---

## 12. References

- Glossary / external copy: [sip-lab-external.md](../copy/sip-lab-external.md)
- Design system: [design-system.md](../design-system.md)
- Components: [components.md](../components.md)
- v0 patterns: [dashboard.md](./dashboard.md) · [performance.md](./performance.md)
- PRD / ADRs: [prd-sip-lab.md](../../product/prd-sip-lab.md) · [004](../../decisions/004-sip-lab-prd-decisions.md) · [005](../../decisions/005-upstox-sole-market-data.md)
- Backlog: **P2-04+** in [backlog-phase-0-2.md](../../product/backlog-phase-0-2.md)
