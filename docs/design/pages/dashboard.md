# Dashboard — Page Spec (`/`)

**Audience:** Frontend agent  
**Job to be done:** In ~5 seconds answer *How is this smallcase doing, and should I dig deeper?*  
**Route:** `/` (App Router `app/page.tsx`)  
**Shell:** Global layout (top bar + left nav + Smallcase Switcher). See [ui.md](../../architecture/ui.md).  
**Visual language:** [design-system.md](../design-system.md) · [components.md](../components.md)

---

## 1. Layout (desktop ≥1280px)

```
┌─ App shell ────────────────────────────────────────────────────────────────┐
│ TopBar: Logo | SmallcaseSelect | as-of badge | ThemeToggle                 │
├─ LeftNav ──┬─ Main (max-w-[1440px] mx-auto px-6 py-6 gap-6) ───────────────┤
│ Dashboard● │                                                               │
│ Holdings   │  ┌ ContextStrip ────────────────────────────────────────────┐ │
│ Performance│  │ Name · theme chip · As-of YYYY-MM-DD · RangeChips        │ │
│            │  └──────────────────────────────────────────────────────────┘ │
│            │                                                               │
│            │  ┌ MetricCard ×5  (grid-cols-5 gap-4) ──────────────────────┐ │
│            │  │ NAV │ Total Return │ CAGR │ Max DD │ Volatility [+Sharpe]│ │
│            │  └──────────────────────────────────────────────────────────┘ │
│            │                                                               │
│            │  ┌ grid grid-cols-12 gap-6 ─────────────────────────────────┐ │
│            │  │ col-span-8: PerformanceChart (equity / NAV)              │ │
│            │  │ col-span-4: TopContributors list/table                   │ │
│            │  └──────────────────────────────────────────────────────────┘ │
│            │                                                               │
│            │  ┌ grid grid-cols-12 gap-6 ─────────────────────────────────┐ │
│            │  │ col-span-5: AllocationSnapshot (sector donut/bars)       │ │
│            │  │ col-span-7: PeriodReturnsGrid                            │ │
│            │  └──────────────────────────────────────────────────────────┘ │
└────────────┴───────────────────────────────────────────────────────────────┘
```

**Vertical rhythm:** section gap `gap-6` (24px). Content starts immediately — no hero/marketing whitespace.

### Breakpoints

| Width | Behavior |
|-------|----------|
| ≥1280 | Spec above |
| 768–1279 | KPI `grid-cols-3` or `2`; chart full width; contributors below chart |
| <768 | Single column; tables/charts horizontal-scroll if needed |

---

## 2. Section specs

### 2.1 Context strip

Not a second nav — a compact meta row under the page title area.

| Element | Spec |
|---------|------|
| Smallcase name | `title` 20px / 600; can omit if TopBar switcher is enough — prefer show once in strip for scannability |
| Theme chip | Optional `Badge` neutral: theme string from API |
| As-of | `label` muted: `As-of 31 Dec 2024` |
| RangeChips | Shared control: `1M 3M 6M 1Y 3Y YTD SI` — default **SI** or last available window |

Tailwind: `flex flex-wrap items-center justify-between gap-3 mb-2`

### 2.2 KPI row (MetricCards)

**Order (left → right, fixed for muscle memory):**

| # | Label | Value source | Sentiment | Format |
|---|-------|--------------|-----------|--------|
| 1 | Current NAV | Latest `PerformancePoint.nav` | `none` | `1,248.32` (2 dp; no ₹ on index NAV unless product chooses currency prefix) |
| 2 | Total return | `metrics.total_return` for range | `pos`/`neg`/`flat` | `+18.42%` |
| 3 | CAGR | `metrics.cagr` | `pos`/`neg`/`none` if null | `14.20%` (omit `+` optional; prefer signed) |
| 4 | Max drawdown | `metrics.max_drawdown` | always `neg` when non-null (value ≤ 0) | `−12.10%` |
| 5 | Volatility | `metrics.volatility` | `none` | `16.80%` |
| 6 (optional stretch) | Sharpe | `metrics.sharpe` | `none` | `1.24` |

- Grid: `grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4` (drop Sharpe on narrow; include on xl if space).
- **Click:** Max DD card → navigate to `/performance#drawdown` (or scroll target).
- Return card optional sublabel: `window` label e.g. `1Y` / `SI`.
- Null metrics: show `—`, no fake 0%, no green.

### 2.3 Performance chart (primary visual)

| Prop / detail | Spec |
|---------------|------|
| Component | `PerformanceChart` variant `equity` |
| Height | 360px desktop |
| Series | Portfolio NAV (required); benchmark if `benchmark_series` present |
| X | date; Y left = NAV (or indexed 100); optional dual not needed in v0 |
| Controls | Range already global; chart-local legend toggle Benchmark on/off |
| Tooltip | Date heading; NAV; daily/cum return if available; BM value |
| Empty | “No NAV series for selected range” |

Layout shell:

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4
header: flex justify-between items-center mb-3
  title: "Equity curve"  text-subtitle
  legend: Portfolio · Benchmark
```

**Grid weight:** `col-span-8` — must dominate the fold.

### 2.4 Top contributors / drags

| Detail | Spec |
|--------|------|
| Title | “Top contributors” |
| Data | Contribution rows if API/curated available; else hide panel or show “Attribution unavailable” |
| Content | Top 5 by contribution desc + Bottom 5 (or single list with pos/neg split) |
| Row | Ticker (mono) · Name truncate · Contrib % with P&L color + optional micro bar |
| Footer link | “View all holdings →” → `/holdings?sort=contrib` |

Height roughly matches chart card (~360px) with internal scroll if >10 rows.

Tailwind list row: `flex items-center gap-2 py-2 border-b border-[var(--border-subtle)] last:border-0`

### 2.5 Allocation snapshot

| Detail | Spec |
|--------|------|
| Title | “Allocation” |
| Chart | Horizontal stacked bar **or** donut (prefer **horizontal bars by sector** for density); max 8 sectors + Other |
| Legend | Sector name + weight % |
| Empty sector | If all `sector` null → show **weight concentration** bars: top 10 names instead |
| Link | “Full composition →” → `/holdings` |

### 2.6 Period returns grid

| Detail | Spec |
|--------|------|
| Title | “Returns by period” |
| Cells | Windows: `1M, 3M, 6M, 1Y, 3Y, YTD, SI` |
| Cell content | Label (muted) + value (kpiSm, P&L color, signed %) |
| Layout | `grid grid-cols-4 lg:grid-cols-7 gap-3` inside surface card |
| Active range | Subtle ring/border on the cell matching global RangeChips selection |
| Click | Selecting a cell sets global range (same as RangeChips) |

---

## 3. Data contract (map to API)

| UI | API / concept | Notes |
|----|---------------|-------|
| Switcher list | `GET /smallcases` | `id`, `name`, `constituent_count`, `as_of` |
| Metrics KPIs | `GET /smallcases/{id}/metrics?window=` | Decimals → format as % in UI |
| Equity series | `GET /smallcases/{id}/performance` | `series[].date`, `nav` |
| Benchmark | `performance.benchmark_series` | Optional; hide legend if null |
| Holdings teaser | `GET /smallcases/{id}/holdings` | Sector weights client-side aggregate |
| Contribution | curated `contribution` / future endpoint | Graceful degrade |

**URL state:** `?smallcase=<id>&from=&to=` or `?smallcase=&window=1y` — changing range updates metrics + chart.

API returns **fractions** (`0.1842` = 18.42%). Frontend formats; never double-scale.

---

## 4. States

| State | Treatment |
|-------|-----------|
| Loading | 5 skeleton MetricCards; chart skeleton block `h-[360px] animate-pulse bg-[var(--bg-muted)]`; list skeletons |
| Empty smallcases | Centered card: “No smallcases loaded” + path hint `data/curated/smallcases/` |
| Empty series | Chart empty copy; KPIs `—` |
| Error | Inline banner under context strip: “Failed to load metrics” + retry |
| Stale | Top bar badge: `Data as-of …` with `risk.warning` if age policy defined later |
| Partial | e.g. no sectors → allocation falls back to top weights |

---

## 5. Interactions

1. **RangeChips / period cell** → refetch metrics + performance for window; keep smallcase.
2. **SmallcaseSelect** → refetch all; stay on `/`.
3. **Max DD MetricCard** → `/performance#drawdown`.
4. **Contributor row** → optional `/holdings` with highlight query (nice-to-have).
5. **Chart hover** → crosshair tooltip; no click-to-zoom required in v0.

---

## 6. Tailwind layout sketch (paste-ready structure)

```tsx
// structural only — not full implementation
<main className="mx-auto max-w-[1440px] px-6 py-6 flex flex-col gap-6">
  <header className="flex flex-wrap items-center justify-between gap-3">
    {/* title + RangeChips */}
  </header>

  <section className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-4">
    {/* MetricCard ×5 */}
  </section>

  <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    <div className="lg:col-span-8">{/* PerformanceChart */}</div>
    <div className="lg:col-span-4">{/* TopContributors */}</div>
  </section>

  <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
    <div className="lg:col-span-5">{/* AllocationSnapshot */}</div>
    <div className="lg:col-span-7">{/* PeriodReturnsGrid */}</div>
  </section>
</main>
```

---

## 7. Acceptance (Dashboard)

- [ ] KPI strip shows NAV, total return, CAGR, max DD, vol with correct P&L coloring
- [ ] Equity curve is the largest visual above the fold
- [ ] Global smallcase + range drive all widgets
- [ ] Missing optional panels degrade without breaking layout
- [ ] Dark default surfaces/borders match design tokens
- [ ] No business logic in presentational components beyond formatting

---

## 8. Out of scope (v0)

- Side-by-side smallcase compare  
- Editable definitions  
- Live price streaming  
- Mobile-optimized multi-column polish  
