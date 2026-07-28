# Component Specs — Smallcase Finance (v0)

**Audience:** Frontend agent  
**Stack:** Next.js + TypeScript + Tailwind + Recharts  
**Tokens:** [design-system.md](./design-system.md)  
**Pages:** [dashboard](./pages/dashboard.md) · [holdings](./pages/holdings.md) · [performance](./pages/performance.md)

This file is the **implementation contract** for shared UI. No React code here — props, states, variants, and Tailwind recipes only.

---

## Shared conventions

| Concern | Rule |
|---------|------|
| Numbers | Always `tabular-nums`; format fractions→% in presenters, not raw API dump |
| Missing | Em dash `—` |
| P&L color | Via `sentiment` or pure format helpers; never invent green for “ok” system states |
| Loading | Prefer skeleton shapes matching final layout |
| a11y | Visible focus ring; don’t rely on color alone for up/down |
| Theme | CSS variables; components don’t hardcode dark hex |

### Suggested format helpers (frontend util, not components)

```
formatPercent(0.1842) → "+18.42%"   // signed
formatPercentAbs(0.168) → "16.80%"
formatNav(1248.3) → "1,248.30"
formatWeight(0.084) → "8.4%"
formatRatio(1.24) → "1.24"
formatInr(2841.25) → "₹2,841.25"  // en-IN grouping preferred
```

---

## 1. `MetricCard`

**Purpose:** Glanceable KPI for NAV, returns, risk ratios.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | required | e.g. `Total return` |
| `value` | `string \| null` | required | **Pre-formatted** display string or null → `—` |
| `sentiment` | `'pos' \| 'neg' \| 'flat' \| 'none'` | `'none'` | Colors the value (and optional delta) |
| `delta` | `string \| null` | — | Secondary line, e.g. `vs BM +2.1pp` |
| `deltaSentiment` | same as sentiment | inherits / `none` | Optional separate color for delta |
| `hint` | `string` | — | Tooltip / title attribute for methodology |
| `loading` | `boolean` | `false` | Skeleton state |
| `onClick` | `() => void` | — | Makes card interactive |
| `href` | `string` | — | Link behavior (prefer over onClick for nav) |
| `size` | `'default' \| 'compact'` | `'default'` | Compact for dense strips |
| `className` | `string` | — | Escape hatch |

### Variants / states

| State | Visual |
|-------|--------|
| Default | Surface card, border, pad 16 |
| Compact | pad 12, value `kpiSm` (18–20px) |
| Interactive | `hover:border-[var(--accent)] cursor-pointer`; focus ring |
| Loading | Pulse blocks for label + value |
| Null value | `—` in `text.secondary`, sentiment forced `none` |

### Anatomy

```
┌─────────────────────────┐
│ LABEL                   │  text-xs font-medium text-[var(--text-secondary)] uppercase? optional tracking
│ +18.42%                 │  text-2xl font-semibold tabular-nums · sentiment color
│ vs Nifty +2.1pp         │  text-xs text-secondary or deltaSentiment
└─────────────────────────┘
```

### Sentiment → class

| Sentiment | Value color |
|-----------|-------------|
| `pos` | `text-[var(--pnl-pos)]` |
| `neg` | `text-[var(--pnl-neg)]` |
| `flat` | `text-[var(--text-secondary)]` |
| `none` | `text-[var(--text-primary)]` |

### Tailwind recipe

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4
flex flex-col gap-1 min-w-0
```

Interactive add:

```
transition-colors hover:border-[var(--accent)] focus-visible:outline-none
focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50
```

### Usage map

| Page | Cards |
|------|-------|
| Dashboard | NAV, Return, CAGR, Max DD, Vol |
| Performance | Return, CAGR, Vol, Sharpe, Max DD, Obs |

---

## 2. `PerformanceChart`

**Purpose:** First-class time series for equity NAV and drawdown.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `'equity' \| 'drawdown'` | required | Visual mode |
| `title` | `string` | — | Panel title |
| `subtitle` | `string` | — | e.g. `Base NAV 100` |
| `series` | `ChartSeries[]` | required | See below |
| `height` | `number` | `360` equity / `260` dd | px |
| `loading` | `boolean` | `false` | |
| `emptyMessage` | `string` | `"No data for selected range"` | |
| `syncId` | `string` | — | Recharts sync across charts |
| `showLegend` | `boolean` | `true` | |
| `yTickFormatter` | `(n) => string` | smart default | |
| `className` | `string` | — | |

```
ChartSeries {
  id: string
  name: string           // legend
  data: { date: string; value: number }[]
  color?: string         // defaults by role
  role?: 'portfolio' | 'benchmark' | 'drawdown' | 'other'
  strokeDasharray?: string
  type?: 'line' | 'area'
}
```

### Variant rules

| Variant | Series | Chart type | Color |
|---------|--------|------------|-------|
| `equity` | portfolio required; benchmark optional | `Line` (or area light fill under portfolio only if subtle) | portfolio `#60A5FA`, benchmark `#A78BFA` dashed |
| `drawdown` | single series values ≤ 0 | `Area` | stroke/fill `var(--pnl-neg)` |

### States

| State | Visual |
|-------|--------|
| Loading | `h-[height] rounded-lg bg-[var(--bg-muted)] animate-pulse` |
| Empty | Centered muted text inside panel chrome |
| Single point | Still render; avoid broken domain — pad y |
| Error | Optional `error` prop → message inside panel |

### Panel chrome

```
┌─ Title ──────────────────── Legend / toggles ─┐
│                                               │
│                 chart body                    │
│                                               │
│  footer micro (optional source)               │
└───────────────────────────────────────────────┘
```

```
rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4
```

### Tooltip

- Container: `bg-[var(--bg-surface-raised)] border border-[var(--border-default)] rounded-md px-3 py-2 shadow-lg text-xs`
- Date as bold heading
- Rows: series name + tabular value
- Drawdown values formatted as signed %

### Recharts notes

- `margin={{ top: 8, right: 12, left: 0, bottom: 0 }}`
- Cartesian grid: horizontal dashed, stroke `var(--border-subtle)`
- Axis tick: `fill: var(--text-secondary)`, fontSize 11
- Active dot radius 4; otherwise strokeWidth 2
- No gradient candy; max one soft area fill

---

## 3. `HoldingsTable`

**Purpose:** Dense composition table with optional P&L columns.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `rows` | `HoldingRow[]` | required | |
| `columns` | `ColumnKey[]` | smart default | Which cols to show |
| `sort` | `{ key; dir: 'asc'\|'desc' }` | weight desc | Controlled or uncontrolled |
| `onSortChange` | fn | — | |
| `loading` | `boolean` | `false` | |
| `emptyMessage` | `string` | `"No holdings"` | |
| `maxWeightForBar` | `number` | max of rows | Scale for micro bars |
| `onRowClick` | `(row) => void` | — | Optional |
| `stickyHeader` | `boolean` | `true` | |
| `compact` | `boolean` | `true` | Finance density |

```
HoldingRow {
  symbol: string
  name?: string | null
  weight: number          // fraction 0–1
  sector?: string | null
  price?: number | null
  periodReturn?: number | null  // fraction
  contribution?: number | null  // fraction or return contrib
}
```

`ColumnKey = 'symbol' | 'name' | 'weight' | 'price' | 'periodReturn' | 'contribution' | 'sector'`

### Column defaults by page

| Context | Columns |
|---------|---------|
| Holdings page | symbol, name, weight, price?, periodReturn?, contribution?, sector |
| Dashboard top contrib | symbol, name, contribution |
| Performance attribution | symbol, name, weight, periodReturn, contribution |

### Cell rules

| Column | Render |
|--------|--------|
| symbol | `font-mono text-sm tracking-tight` |
| name | truncate + `title={name}` |
| weight | `formatWeight` + `WeightBar` |
| price | `formatInr` or plain 2 dp |
| periodReturn / contribution | signed % + sentiment class |

### WeightBar (sub-element)

| Prop | Type |
|------|------|
| `value` | fraction |
| `max` | fraction scale |
| `className` | optional |

```
track: h-1.5 w-20 rounded-full bg-[var(--bg-muted)] overflow-hidden
fill:  h-full rounded-full bg-[var(--accent)]
width: `${(value/max)*100}%`
```

### Table chrome

```
w-full text-sm
thead: bg-[var(--bg-muted)] text-[var(--text-secondary)] text-xs font-medium
th: px-3 py-2 text-left | text-right for nums; cursor-pointer if sortable
td: px-3 py-2 border-b border-[var(--border-subtle)]
tr:hover: bg-[var(--bg-hover)]
```

### States

| State | Behavior |
|-------|----------|
| Loading | 8 skeleton rows |
| Empty | Single row colspan message |
| Sorting | Aria `aria-sort`; caret icon |

---

## 4. `SmallcaseSelect`

**Purpose:** Global context switcher in the top bar (not a page).

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `items` | `SmallcaseOption[]` | required | |
| `value` | `string \| null` | required | active `id` |
| `onChange` | `(id: string) => void` | required | |
| `loading` | `boolean` | `false` | |
| `disabled` | `boolean` | `false` | |
| `periodReturnById` | `Record<string, number>` | — | Optional chip in menu |
| `placeholder` | `string` | `"Select smallcase"` | |
| `className` | `string` | — | |

```
SmallcaseOption {
  id: string
  name: string
  constituentCount?: number | null
  theme?: string | null
  asOf?: string | null
}
```

### Anatomy

**Trigger (closed)**

```
┌────────────────────────────────────┐
│ Momentum Quality            +18.4% ▾│
└────────────────────────────────────┘
```

- Height 36px; min-width 200px; max-width 280px
- Truncate name; optional return chip with sentiment
- Chevron down

**Menu (open)**

```
┌──────────────────────────────────────────┐
│ 🔍 Filter…                               │  // if items.length > 5
│ ● Momentum Quality   22 · +18.4%         │
│   Digital India      18 · +12.1%         │
│ ──────────────────────────────────────── │
│ No manage actions in v0                  │
└──────────────────────────────────────────┘
```

- Max height 320px scroll
- Active row: check / accent text + `bg-[var(--accent-subtle)]`
- Raised surface + shadow

### States

| State | Visual |
|-------|--------|
| Loading | Trigger skeleton / spinner |
| Empty items | Trigger disabled; menu “No smallcases loaded” |
| Open | Focus trap light; Esc closes; typeahead optional |
| Error list | Inline error in menu |

### Tailwind trigger

```
inline-flex items-center gap-2 h-9 min-w-[200px] max-w-[280px]
rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)]
px-3 text-sm text-[var(--text-primary)]
hover:bg-[var(--bg-hover)]
focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50
```

### Behavior contract

1. `onChange` → parent updates URL `?smallcase=` and refetches.
2. Persist last id in `localStorage` key `sf-smallcase` (optional, recommended).
3. Do not navigate away from current route.

---

## 5. Supporting components (brief)

### 5.1 `RangeChips`

| Prop | Type |
|------|------|
| `value` | `WindowKey` (`'1M'\|'3M'\|'6M'\|'1Y'\|'3Y'\|'YTD'\|'SI'`) |
| `onChange` | `(w) => void` |
| `options` | `WindowKey[]` default all above |

Selected: `bg-[var(--accent-subtle)] text-[var(--accent)] border-transparent`  
Idle: `border border-[var(--border-default)] text-[var(--text-secondary)]`  
Size: `h-8 px-2.5 text-xs font-medium rounded-md`

### 5.2 `Badge`

`variant: 'neutral' | 'positive' | 'negative' | 'warning' | 'info'`  
`children: ReactNode`  
Padding `px-2 py-0.5 text-xs rounded-md`

### 5.3 `AppShell`

| Slot | Content |
|------|---------|
| `topBar` | Logo, SmallcaseSelect, as-of, ThemeToggle |
| `nav` | Links: Dashboard `/`, Holdings `/holdings`, Performance `/performance` |
| `children` | Page |

Nav active: accent subtle bg + accent text.  
Left width: `w-[220px]` expanded.

### 5.4 `ThemeToggle`

Cycles dark/light; sets `data-theme` on `<html>`; reads `localStorage sf-theme`. Default **dark**.

### 5.5 `EmptyState` / `ErrorBanner`

- Empty: icon optional, title, description, optional action text (no marketing art)
- Error: `border` + `risk.warning` or subtle red border; message + Retry button secondary

### 5.6 `PeriodReturnsGrid`

Dashboard cells: label + formatted return; `onSelectWindow`; `activeWindow`.

### 5.7 `SectorBreakdown` / `WeightBars`

Thin wrappers around Recharts bar lists; accept `{ label: string; weight: number }[]`.

---

## 6. Component inventory vs routes

| Component | Dashboard | Holdings | Performance | Shell |
|-----------|:---------:|:--------:|:-----------:|:-----:|
| MetricCard | ● | | ● | |
| PerformanceChart | ● | | ● | |
| HoldingsTable | teaser | ● | attribution | |
| SmallcaseSelect | | | | ● |
| RangeChips | ● | ● | ● | optional |
| SectorBreakdown | ● | ● | | |
| WeightBars | | ● | | |
| AppShell | | | | ● |

---

## 7. File map suggestion (Frontend)

```
components/
  shell/AppShell.tsx
  shell/ThemeToggle.tsx
  smallcase/SmallcaseSelect.tsx
  filters/RangeChips.tsx
  kpis/MetricCard.tsx
  charts/PerformanceChart.tsx
  charts/SectorBreakdown.tsx
  charts/WeightBars.tsx
  tables/HoldingsTable.tsx
  feedback/EmptyState.tsx
  feedback/ErrorBanner.tsx
lib/
  format.ts
  sentiment.ts
  theme.ts
```

---

## 8. Implementation order (recommended)

1. Tokens in `globals.css` + dark default  
2. AppShell + ThemeToggle + RangeChips  
3. SmallcaseSelect (mock list OK)  
4. MetricCard  
5. PerformanceChart (equity, then drawdown)  
6. HoldingsTable + WeightBar  
7. Wire pages to API  

---

## 9. DoD for components package

- [ ] All four primaries (MetricCard, PerformanceChart, HoldingsTable, SmallcaseSelect) match props above  
- [ ] Dark default readable; light theme doesn’t break charts  
- [ ] Loading/empty/error states exist  
- [ ] P&L colors only on performance semantics  
- [ ] No calc/business logic beyond formatting & drawdown-from-NAV helper  
