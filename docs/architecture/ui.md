# UI Architecture — Smallcase Finance (v0)

Local-first web UI for analyzing Smallcase-style thematic portfolios.  
**Stack assumption:** Next.js App Router + TypeScript + Tailwind + Recharts (or Tremor).  
**Primary viewport:** Desktop (≥1280px). Mobile is usable, not optimized for deep analysis.  
**Non-goals v0:** Auth, multi-user, live trading, broker sync.

---

## 1. Information Architecture

### Global shell

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Logo] Smallcase Finance     [Smallcase Switcher ▾]     [Theme] [Data]   │
├────────────┬─────────────────────────────────────────────────────────────┤
│            │                                                             │
│  Nav       │  Page content (scrollable)                                  │
│  · Dash    │                                                             │
│  · Hold    │                                                             │
│  · Perf    │                                                             │
│            │                                                             │
│  ────────  │                                                             │
│  Meta      │                                                             │
│  · As-of   │                                                             │
│  · Range   │                                                             │
│            │                                                             │
└────────────┴─────────────────────────────────────────────────────────────┘
```

| Zone | Role |
|------|------|
| **Top bar** | Brand, **Smallcase Switcher** (global context), theme toggle, data freshness |
| **Left nav** | Primary pages; sticky; collapsible on narrow desktop |
| **Main** | Page body; max content width ~1440px centered or full-bleed for tables/charts |
| **Context strip** (optional, under top bar) | Active smallcase name, as-of date, selected date range |

### Primary routes (App Router)

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Glanceable health of the active smallcase |
| `/holdings` | Holdings / Composition | Weights, names, sector/theme mix, contribution |
| `/performance` | Performance & Risk | Returns, drawdown, risk metrics, equity curve |
| *(global control)* | Smallcase Switcher | Not a full page — persistent control in top bar |

Future (out of v0 scope, reserved): `/rebalance`, `/compare`, `/settings`.

### Navigation model

- **Left nav** = primary pages (Dashboard, Holdings, Performance).
- **Smallcase Switcher** = global filter; changing it reloads metrics for the selected smallcase on *all* pages without losing the current route.
- **Date range** = secondary global control (preset chips + custom range); defaults to “Since inception” or last available window.
- Deep links should encode: `?smallcase=<id>&from=&to=` so analysis is shareable/bookmarkable locally.

---

## 2. Page Specs

> **Full implementable layouts** (grids, states, API mapping, Tailwind sketches) live under  
> [`docs/design/pages/`](../design/pages/). Summary IA below; do not fork layout rules without updating both.

### 2.1 Dashboard (`/`)

**Detail spec:** [`docs/design/pages/dashboard.md`](../design/pages/dashboard.md)  
**Job:** Answer in 5 seconds — *How is this smallcase doing, and should I dig deeper?*

#### Layout (desktop)

```
┌─ Context: [Momentum Quality ▾]  As-of: 2024-12-31  Range: 1Y ▾ ──────────┐
│                                                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ NAV     │ │ Return  │ │ CAGR    │ │ Max DD  │ │ Vol     │  KPI row   │
│  │ 1,248.3 │ │ +18.4%  │ │ 14.2%   │ │ -12.1%  │ │ 16.8%   │            │
│  │ vs BM   │ │ green   │ │         │ │ red     │ │         │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
│                                                                           │
│  ┌──────────────────────────────────────┐ ┌────────────────────────────┐ │
│  │ Equity curve (NAV vs benchmark)      │ │ Top contributors / drags   │ │
│  │ [chart — primary visual]             │ │ table or bar list          │ │
│  │                                      │ │                            │ │
│  └──────────────────────────────────────┘ └────────────────────────────┘ │
│                                                                           │
│  ┌──────────────────────────┐ ┌────────────────────────────────────────┐ │
│  │ Allocation snapshot      │ │ Recent period returns                  │ │
│  │ donut / stacked bar      │ │ 1M  3M  6M  1Y  YTD  SI                │ │
│  │ (sector or weight bands) │ │ mini sparkline or number grid          │ │
│  └──────────────────────────┘ └────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Hierarchy
1. **KPI strip** — NAV, total return (range), CAGR, max drawdown, volatility (optional: Sharpe).
2. **Equity curve** — dominant chart; portfolio line + optional benchmark.
3. **Attribution teaser** — top 5 contributors / bottom 5 drags (links to Holdings).
4. **Composition teaser** — sector or weight band snapshot (links to Holdings).
5. **Period returns grid** — standard windows for scannability.

#### States
- **Loading:** skeleton KPI cards + chart placeholder.
- **Empty:** no smallcase defined → CTA “Define a smallcase” / point to data pipeline.
- **Error:** data load failure with last successful as-of if known.
- **Stale data:** badge in top bar (“Data as-of … · n days old”).

#### Interactions
- KPI cards: click Max DD → scroll/jump to Performance drawdown section.
- Chart: hover crosshair with date, NAV, return; legend toggle for benchmark.
- Range chips update all Dashboard widgets.

---

### 2.2 Holdings / Composition (`/holdings`)

**Detail spec:** [`docs/design/pages/holdings.md`](../design/pages/holdings.md)  
**Job:** *What is inside this smallcase, at what weight, and who drives P&L?*

#### Layout (desktop)

```
┌─ Holdings · Momentum Quality ─────────────────────────────────────────────┐
│  Summary: 22 names · 4 sectors · Top 10 weight: 62% · Cash: 2.1%          │
│                                                                           │
│  [Table view] [By sector] [By weight band]          Search  [Export CSV]  │
│                                                                           │
│  ┌─ Holdings table (primary) ───────────────────────────────────────────┐ │
│  │ Ticker │ Name        │ Weight │ Price  │ 1D%  │ Contrib │ Sector    │ │
│  │ RELIANCE│ Reliance   │  8.4%  │ 2,841  │ +0.6 │ +0.12   │ Energy    │ │
│  │ ...     │            │        │        │      │         │           │ │
│  │         │            │ sortable columns · sticky header · denser rows│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─ Weight distribution ────────┐  ┌─ Sector / theme mix ──────────────┐ │
│  │ horizontal bar or treemap    │  │ stacked bar or donut + legend     │ │
│  └──────────────────────────────┘  └───────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Table columns (v0 recommended)

| Column | Notes |
|--------|-------|
| Ticker | Monospace-ish, sticky left if horizontal scroll |
| Name | Truncate with tooltip |
| Weight % | 1 decimal; bar micro-indicator optional |
| Price | INR formatting; 2 decimals for most equities |
| Period return % | Color-coded P&L |
| Contribution | Weight × return (or explicit contrib); color-coded |
| Sector / Theme | Group key |
| (optional) Target weight, Drift | For rebalance readiness later |

#### Hierarchy
1. Composition summary strip (count, concentration, cash).
2. **Holdings table** — first-class; densest scannable surface.
3. Distribution + sector charts below or right (on wide screens, charts can sit above fold to the right of a shortened table — prefer table full-width first for v0).

#### Interactions
- Sort by weight, contribution, return.
- Filter by sector / search ticker or name.
- Row click → optional detail drawer (price history mini-chart) — nice-to-have, not v0 required.
- Toggle “show only top N / all”.

---

### 2.3 Performance & Risk (`/performance`)

**Detail spec:** [`docs/design/pages/performance.md`](../design/pages/performance.md)  
**Job:** *How has it performed over time, and how painful were the drawdowns?*

#### Layout (desktop)

```
┌─ Performance & Risk ──────────────────────────────────────────────────────┐
│  Range: [1M] [3M] [6M] [1Y] [3Y] [SI] [Custom]     Benchmark: [Nifty 50]  │
│                                                                           │
│  ┌ KPI: Return │ CAGR │ Vol │ Sharpe │ Max DD │ Calmar / Sortino ─────┐  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─ Equity / cumulative return chart ─────────────────────────────────┐  │
│  │ multi-series: portfolio, benchmark, optional excess                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─ Drawdown chart ───────────────────────────────────────────────────┐  │
│  │ area under 0; annotate peak DD period                              │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─ Returns distribution ──────┐  ┌─ Rolling metrics (optional v0.1) ┐  │
│  │ monthly bar or histogram    │  │ rolling vol / rolling return     │  │
│  └─────────────────────────────┘  └──────────────────────────────────┘  │
│                                                                           │
│  ┌─ Period returns table ─────────────────────────────────────────────┐  │
│  │ Year │ Jan … Dec │ Annual │ vs BM                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Hierarchy
1. Risk/return KPI strip (same visual language as Dashboard, more complete).
2. **Equity curve** — primary chart.
3. **Underwater / drawdown** — second chart, always paired with equity.
4. Calendar / period returns table.
5. Distribution or rolling series as secondary.

#### Interactions
- Sync tooltip date across equity + drawdown when possible.
- Benchmark selector (local list: Nifty 50, Sensex, custom series if present).
- Export chart data / metrics JSON optional later.

---

### 2.4 Smallcase Switcher (global control)

**Job:** *Pick which thematic portfolio I’m analyzing right now.*

Not a standalone page. Lives in the **top bar**, always visible.

#### Anatomy

```
┌─────────────────────────────────────────────┐
│  Momentum Quality                        ▾  │
│  ─────────────────────────────────────────  │
│  ● Momentum Quality     22 names · +18.4%   │
│    Quality Compounders  15 names · +12.1%   │
│    Dividend Aristocrats 18 names ·  +8.6%   │
│  ─────────────────────────────────────────  │
│  Compare (soon) · Manage definitions…       │
└─────────────────────────────────────────────┘
```

#### Behavior
- Shows **active** smallcase name + optional sparkline or period return chip.
- Dropdown list: name, holding count, period return (current global range).
- Keyboard: typeahead filter when many smallcases.
- On change: update URL query, refetch page data, keep route + range.
- Empty state: “No smallcases loaded” → link to docs / data path.

#### Why not a page?
Switcher is context, not content. A dedicated “library” page can come later if definitions become editable in-UI.

---

## 3. Primary User Flows

### Flow A — Morning scan (most common)

1. Open app → lands on **Dashboard** with last-used smallcase + default range.
2. Read KPI strip (return / DD).
3. Skim equity curve vs benchmark.
4. If return looks off → switch range (1M vs 1Y).
5. If curious about drivers → **Holdings** sorted by contribution.
6. If risk concern → **Performance** drawdown section.

### Flow B — Understand composition

1. Select smallcase via **Switcher**.
2. Go to **Holdings**.
3. Sort by weight; check concentration (top 10).
4. Filter sector; validate theme purity.
5. Optional: note drift vs target (when available).

### Flow C — Risk deep-dive

1. From Dashboard click Max DD KPI (or nav to Performance).
2. Set range SI or full history.
3. Inspect equity + underwater charts together.
4. Read vol / Sharpe / max DD.
5. Check calendar returns for bad months/years.

### Flow D — Switch theme and compare mentally

1. Note key numbers on Dashboard for smallcase A.
2. Open Switcher → select B.
3. Same page reloads metrics (user compares mentally).  
   *True side-by-side compare is post-v0.*

---

## 4. Shared UI Patterns

### KPI card
- Label (muted, 12px) → value (semibold, 22–28px tabular nums) → delta/sublabel (12–13px, P&L color).
- Optional vs-benchmark micro line.
- Min width ~140px; 4–6 cards per row on desktop.

### Chart panel
- Card shell: title left, legend/controls right, body chart.
- Height defaults: primary chart 320–400px; secondary 200–280px.
- Empty: “No series for selected range”.

### Data table
- Sticky header, zebra optional (prefer subtle row hover only in dark mode).
- Tabular numbers, right-align numerics, left-align names.
- Density: `py-2` row padding desktop; compact mode preferred for finance.

### Global filters
- Smallcase (required context).
- Date range presets: 1M, 3M, 6M, 1Y, 3Y, YTD, SI.
- Benchmark (Performance-heavy; optional on Dashboard).

### Feedback
- Prefer inline empty/error over full-page dead ends.
- Toasts only for explicit user actions (export, copy).

---

## 5. Responsive Notes (secondary)

| Breakpoint | Behavior |
|------------|----------|
| ≥1280px | Full shell: left nav + multi-column grids |
| 768–1279px | Collapsible left nav (icons); KPI wrap 2–3 cols; charts stack |
| <768px | Bottom or hamburger nav; single column; tables horizontal scroll |

Do not block v0 on mobile polish.

---

## 6. Data Dependencies (for frontend/backend contract)

| UI surface | Expected data concepts |
|------------|------------------------|
| Switcher | `smallcase_id`, name, holding_count, summary return |
| Dashboard KPIs | NAV, returns, CAGR, max_dd, vol, sharpe |
| Equity curve | date, nav or cumulative_return [, benchmark] |
| Holdings table | ticker, name, weight, price, returns, contrib, sector |
| Sector mix | sector, weight |
| Drawdown series | date, drawdown_pct |
| Period returns | window or month/year matrix |

Exact schemas live with Data Architect / API; UI should tolerate missing optional series (hide panel, don’t break).

---

## 7. Implementation Map (for Frontend agent — no code yet)

Suggested App Router sketch:

```
app/
  layout.tsx          # shell: top bar, nav, switcher, theme
  page.tsx            # Dashboard
  holdings/page.tsx
  performance/page.tsx
components/
  shell/
  kpis/
  charts/
  tables/
  smallcase-switcher/
```

Design tokens and visual rules: see [`docs/design/design-system.md`](../design/design-system.md).

### Detailed design handoff (implement from these)

| Artifact | Path |
|----------|------|
| Design system + paste-ready tokens | [`docs/design/design-system.md`](../design/design-system.md) |
| Component props / states | [`docs/design/components.md`](../design/components.md) |
| Dashboard layout | [`docs/design/pages/dashboard.md`](../design/pages/dashboard.md) |
| Holdings layout | [`docs/design/pages/holdings.md`](../design/pages/holdings.md) |
| Performance layout | [`docs/design/pages/performance.md`](../design/pages/performance.md) |

This architecture doc stays the IA + flow source of truth; page/component files are Frontend-ready specs (Tailwind structure, API field mapping, states). No React implementation in design docs.

---

## 8. v0 Acceptance (UI architecture)

- [x] Four concerns covered: Dashboard, Holdings, Performance, Switcher
- [x] Navigation + global smallcase context defined
- [x] Primary flows A–C implementable without new pages
- [x] Charts and tables called out as first-class layout anchors
- [x] Desktop-first; no auth/multi-user assumptions
- [x] Detailed page + component specs under `docs/design/` (no React in design docs)

**Frontend build acceptance** is tracked on each page spec + `components.md` DoD.
