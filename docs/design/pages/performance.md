# Performance & Risk — Page Spec (`/performance`)

**Audience:** Frontend agent  
**Job to be done:** *How has it performed over time, and how painful were the drawdowns?*  
**Route:** `/performance`  
**Shell:** Global layout + SmallcaseSelect + range + optional benchmark control.  
**Visual language:** [design-system.md](../design-system.md) · [components.md](../components.md)  
**Metric semantics:** [metrics-definitions.md](../../analytics/metrics-definitions.md) (decimals; max DD ≤ 0)

---

## 1. Layout (desktop ≥1280px)

```
┌─ Main ─────────────────────────────────────────────────────────────────────┐
│  Header: “Performance & Risk”                                              │
│  Controls: RangeChips · BenchmarkSelect (if series exist)                  │
│                                                                            │
│  ┌ MetricCard row (6) ───────────────────────────────────────────────────┐ │
│  │ Return │ CAGR │ Vol │ Sharpe │ Max DD │ n obs / window label          │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌ PerformanceChart equity  h-[360–400px]  id="equity" ─────────────────┐ │
│  │ Portfolio + optional Benchmark (+ optional excess later)              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌ PerformanceChart drawdown  h-[240–280px]  id="drawdown" ─────────────┐ │
│  │ Area ≤ 0 · pnl.negative fill · annotate trough if easy                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌ grid-cols-12 ─────────────────────────────────────────────────────────┐ │
│  │ col-span-5: Monthly returns bars (optional if data)                   │ │
│  │ col-span-7: PeriodReturnsTable (windows + vs BM if any)               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌ Attribution / contribution table (if available) ──────────────────────┐ │
│  │ Symbol · Weight · Return · Contribution  (sortable)                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Footer micro: assumptions (rf, 252d) from metrics.assumptions             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Hierarchy:** Risk KPIs → equity curve → underwater drawdown (always paired) → tables.

Anchor IDs: `#equity`, `#drawdown` for Dashboard deep links.

---

## 2. Controls

| Control | Spec |
|---------|------|
| RangeChips | `1M 3M 6M 1Y 3Y YTD SI` + optional Custom (date inputs) later |
| BenchmarkSelect | Only if backend provides benchmark series or `benchmark_id`; placeholder “None” |
| Sync | Same `smallcase` + `window` query params as other pages |

Control row:

```
flex flex-wrap items-center justify-between gap-3
```

---

## 3. Risk / return KPI strip

| # | Label | Field | Sentiment | Format |
|---|-------|-------|-----------|--------|
| 1 | Total return | `total_return` | pos/neg | `+18.42%` |
| 2 | CAGR | `cagr` | pos/neg or none if null | `14.20%` |
| 3 | Volatility | `volatility` | none | `16.80%` |
| 4 | Sharpe | `sharpe` | none | `1.24` |
| 5 | Max drawdown | `max_drawdown` | neg | `−12.10%` |
| 6 | Observations | `n_observations` | none | `1,248 days` or window chip |

Grid: `grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4`

**Null rules:** CAGR/Sharpe null for short windows → `—` + tooltip “Need ~1 month of data” (from metrics defs).

Optional sublabel on Sharpe: `rf 0%` or `rf 6%` from `assumptions.rf_rate`.

---

## 4. Equity / cumulative chart

| Detail | Spec |
|--------|------|
| Component | `PerformanceChart` `variant="equity"` |
| Height | 380px |
| Y-axis | NAV (base often 100) **or** cumulative return % — pick **one per v0**; recommend **NAV** with subtitle “Base 100” if `base_nav` known |
| Series colors | Portfolio `chart.portfolio` `#60A5FA`; Benchmark `chart.benchmark` `#A78BFA` dashed stroke optional |
| Grid | `border.subtle` horizontal only preferred |
| Tooltip | Date; Portfolio NAV; BM NAV; optional spread |
| Legend | Top-right inside panel |
| Empty | “No performance series for this range” |

**Do not** paint the equity line green/red based on total return — series color is structural; P&L is for KPI/table cells.

---

## 5. Drawdown chart

| Detail | Spec |
|--------|------|
| Component | `PerformanceChart` `variant="drawdown"` |
| Data | Client-compute from NAV: `dd_t = nav_t / peak_t - 1` **or** backend series if provided |
| Height | 260px |
| Visual | Area chart, y domain padded e.g. `[minDd * 1.05, 0]` |
| Fill | `var(--pnl-neg)` at 20–30% opacity |
| Stroke | `var(--pnl-neg)` ~1.5–2px |
| Zero line | subtle `border.default` |
| Annotation | Optional marker at min DD date with label `−12.1%` |
| Tooltip | Date + drawdown % |

**Pairing:** Place immediately under equity with same x-domain and, if feasible, **shared brush/tooltip date** (nice-to-have: Recharts syncId).

Panel title: “Drawdown” · subtitle “Peak-to-trough from running NAV high”.

---

## 6. Period returns table

Simpler than full calendar matrix for v0:

### 6.1 Window table (required)

| Window | Portfolio | Benchmark | Excess |
|--------|-----------|-----------|--------|
| 1M | +2.1% | +1.4% | +0.7pp |
| 3M | … | … | … |
| … | | | |

- Excess = port − bm when both exist; else hide Benchmark/Excess columns.
- P&L color on all three numeric cols.
- Highlight row matching active range: `bg-[var(--accent-subtle)]` or left border.

### 6.2 Calendar year × month (optional v0.1)

If monthly aggregation is cheap:

| Year | Jan | … | Dec | Annual |
|------|-----|---|-----|--------|
| 2024 | +1.2 | | | +18.4 |

- Cell bg: muted pos/neg tint at low opacity **or** text-only (prefer **text-only** in v0 for less noise).
- Skip if not in API yet.

---

## 7. Monthly returns bars (optional)

- Bar per month for selected range (or last 12–36 months).
- Positive bars `pnl.pos`, negative `pnl.neg`.
- Hide if insufficient history.

---

## 8. Attribution / contribution section

| Detail | Spec |
|--------|------|
| Show when | Contribution data available for smallcase + window |
| Title | “Return contribution” |
| Columns | Symbol · Name · Weight · Return · Contribution |
| Sort default | Contribution ascending (drags first) **or** absolute contribution — recommend **contrib desc** with separate “Largest drags” mini list if space |
| Component | Reuse `HoldingsTable` column subset or dedicated compact table |
| Empty | Omit entire section (no empty chrome) |

Link: “Open in Holdings →” with sort query.

---

## 9. Assumptions footer

Micro text, muted:

```
Assumptions: 252 trading days/year · rf = 0.0 · max DD from NAV peaks · currency INR
As-of: 2024-12-31 · window: SI
```

Source: `MetricsResponse.assumptions` + range bounds.

---

## 10. Data contract

| UI | API | Notes |
|----|-----|-------|
| KPIs | `GET /smallcases/{id}/metrics` | Fractions; format in UI |
| Equity | `GET /smallcases/{id}/performance` | `series`, optional `benchmark_series` |
| Drawdown | derived from NAV client-side | Keep pure; no extra endpoint required |
| Contribution | curated / future route | Optional section |
| Assumptions | `metrics.assumptions` | Footer |

---

## 11. States

| State | Treatment |
|-------|-----------|
| Loading | KPI skeletons + two chart skeletons |
| Empty series | Both charts empty copy; KPIs `—` |
| Short window nulls | Partial KPIs with `—` |
| Error | Inline alert; preserve last good data if cached |
| No benchmark | Single series; hide BM columns in table |

---

## 12. Interactions

1. Range / smallcase change → refetch metrics + performance; recompute drawdown.
2. Legend toggle hide/show benchmark.
3. Hover sync between equity and drawdown when `syncId` used.
4. Click Max DD KPI on Dashboard lands on `#drawdown` with scroll-margin.
5. Attribution sort.

---

## 13. Tailwind structure sketch

```tsx
<main className="mx-auto max-w-[1440px] px-6 py-6 flex flex-col gap-6">
  <header className="flex flex-wrap items-end justify-between gap-3">
    <h1 className="text-xl font-semibold">Performance &amp; Risk</h1>
    <div className="flex flex-wrap items-center gap-3">
      {/* RangeChips · BenchmarkSelect */}
    </div>
  </header>

  <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
    {/* MetricCards */}
  </section>

  <section id="equity" className="scroll-mt-20">
    {/* PerformanceChart equity */}
  </section>

  <section id="drawdown" className="scroll-mt-20">
    {/* PerformanceChart drawdown */}
  </section>

  <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    <div className="lg:col-span-5">{/* monthly bars optional */}</div>
    <div className="lg:col-span-7">{/* PeriodReturnsTable */}</div>
  </section>

  {/* Attribution table optional */}

  <p className="text-[11px] text-[var(--text-muted)]">{/* assumptions */}</p>
</main>
```

---

## 14. Acceptance (Performance)

- [ ] Full risk KPI strip with correct null handling
- [ ] Equity + drawdown stacked; drawdown uses negative P&L styling
- [ ] Period returns table scannable; BM columns optional
- [ ] Deep link `#drawdown` works with offset under sticky top bar
- [ ] Assumptions visible for trust
- [ ] Attribution section only when data exists

---

## 15. Out of scope (v0)

- Rolling Sharpe/vol multi-panel  
- Full Brinson attribution  
- Custom benchmark upload  
- Chart PNG export  
