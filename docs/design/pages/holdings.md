# Holdings / Composition — Page Spec (`/holdings`)

**Audience:** Frontend agent  
**Job to be done:** *What is inside this smallcase, at what weight, and who drives P&L?*  
**Route:** `/holdings`  
**Shell:** Global layout + SmallcaseSelect + optional range (for return/contrib columns).  
**Visual language:** [design-system.md](../design-system.md) · [components.md](../components.md)

---

## 1. Layout (desktop ≥1280px)

```
┌─ Main ─────────────────────────────────────────────────────────────────────┐
│  Header: “Holdings” · smallcase name muted · RangeChips (for return cols)  │
│                                                                            │
│  ┌ SummaryStrip ─────────────────────────────────────────────────────────┐ │
│  │ 22 names · 4 sectors · Top 10: 62.0% · Cash/other: — · Σw: 100.0%     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Toolbar: [All] [By sector]   Search …………   Sort hint   [Export CSV later] │
│                                                                            │
│  ┌ HoldingsTable (full width, primary) ──────────────────────────────────┐ │
│  │ sticky header · dense rows · weight bar in Weight col · P&L colors    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌ grid-cols-12 gap-6 ───────────────────────────────────────────────────┐ │
│  │ col-span-6: WeightBars (top N horizontal)                             │ │
│  │ col-span-6: SectorBreakdown (bars or donut + legend)                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

**Priority:** Table is first-class. Charts sit **below** full-width table in v0 (not a side column that squeezes the table). On ultra-wide (≥1600), optional later: charts in a right rail — not required.

---

## 2. Summary strip

Computed client-side from holdings response (and optional contrib data).

| Metric | Formula / source | Format |
|--------|------------------|--------|
| Names | `holdings.length` | `22 names` |
| Sectors | distinct non-null `sector` | `4 sectors` or `—` if all null |
| Top 10 weight | sum of top 10 `weight` | `Top 10: 62.0%` |
| Weight sum | `weight_sum` from API | warn chip if `|sum - 1| > 1e-3` |
| Cash | if a CASH-like symbol exists, else omit | optional |

Presentation: single surface row or wrap of `Badge` + muted text.

```
flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border ... bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-secondary)]
```

Strong numbers use `text-[var(--text-primary)] tabular-nums`.

---

## 3. Toolbar

| Control | Spec |
|---------|------|
| View tabs | `Table` (default) · `By sector` (groups rows under sector headers) — v0: Table required; By sector nice-to-have |
| Search | Debounced filter on `symbol` + `name`; height 36px; placeholder “Search ticker or name” |
| Sector filter | Dropdown multi or single “All sectors” when sector data exists |
| Top N | Chip: `All` / `Top 10` / `Top 20` |

No export required for v0 (reserve button slot disabled or omit).

---

## 4. Holdings table

### 4.1 Columns (v0)

| Key | Header | Align | Format | Notes |
|-----|--------|-------|--------|-------|
| `symbol` | Ticker | left | mono-ish, uppercase | Sticky left if horizontal scroll |
| `name` | Name | left | truncate max 28ch + title tooltip | Optional column hide on narrow |
| `weight` | Weight | right | `8.4%` (1 dp) | **Inline weight bar** (see below) |
| `price` | Price | right | INR 2 dp | Only if price join available; else omit column |
| `period_return` | Return | right | signed % + P&L color | Window = global range; omit if no data |
| `contribution` | Contrib | right | signed pp or % + P&L color | From contribution dataset; omit if missing |
| `sector` | Sector | left | text or `—` | |

**Default sort:** `weight` descending.  
**Sortable:** weight, return, contrib, symbol, sector.

### 4.2 Weight bar (in cell)

Anatomy of Weight cell:

```
┌──────────────────────────────────────┐
│  8.4%  ████████░░░░░░░░              │
└──────────────────────────────────────┘
```

- Bar max scale = max weight in current view (or 100% fixed — prefer **max-in-view** so bars spread).
- Bar track: `h-1.5 w-16 md:w-24 rounded-full bg-[var(--bg-muted)]`
- Fill: `bg-[var(--accent)]` (structure color, **not** P&L green)
- Layout: `flex items-center justify-end gap-2` with % then bar (or % above bar on very narrow)

### 4.3 Row & density

| Token | Value |
|-------|-------|
| Row height | ~36–40px (`py-2`) |
| Header | `bg-[var(--bg-muted)]` sticky `top-0 z-10` |
| Hover | `bg-[var(--bg-hover)]` |
| Font | body 14px; numbers `tabular-nums` |
| Borders | row `border-b border-[var(--border-subtle)]` |

Zebra: **off** by default in dark mode (hover only).

### 4.4 P&L cells

- Positive: `text-[var(--pnl-pos)]` + leading `+`
- Negative: `text-[var(--pnl-neg)]` + `−`
- Flat ~0: `text-[var(--text-secondary)]`
- Do **not** fill entire row green/red in v0

### 4.5 Grouped “By sector” (optional)

```
▼ Information Technology          28.4%
  TCS    ... 
  INFY   ...
▼ Financials                      22.1%
  ...
```

Sector header row: muted bg, weight sum right-aligned, sticky optional.

---

## 5. Weight distribution chart

| Detail | Spec |
|--------|------|
| Component | Horizontal bar chart (Recharts `BarChart` layout vertical) |
| Data | Top 10–15 by weight; leftover as “Other” |
| Color | Single series accent or cycle chart palette — not red/green for names |
| Height | 280px |
| Title | “Weight distribution” |
| Interaction | Hover tooltip: name, weight % |

---

## 6. Sector breakdown

| Detail | Spec |
|--------|------|
| Show when | ≥1 holding has non-null `sector` |
| Chart | Horizontal bars preferred (scannable %) or donut + legend |
| Aggregate | Sum weights by sector; sort desc |
| Other | Sectors beyond top 8 → “Other” |
| Empty | Hide card; expand weight chart to full width |

```
grid grid-cols-1 lg:grid-cols-2 gap-6
```

---

## 7. Data contract

| UI | API | Notes |
|----|-----|-------|
| Table body | `GET /smallcases/{id}/holdings?as_of=` | `symbol`, `name`, `weight` (fraction), `sector` |
| Meta | `as_of`, `weight_sum`, `methodology` | Show as-of near header |
| Prices | optional join / future field | Hide Price col if absent |
| Returns / contrib | metrics window + contribution parquet/API | Hide cols if absent |

**Weight display:** API `0.084` → UI `8.4%`.

---

## 8. States

| State | Treatment |
|-------|-----------|
| Loading | Summary skeleton + table row skeletons (8–10) |
| Empty holdings | “No constituents for this smallcase / as-of” |
| Search no match | “No names match ‘…’” inline in table body |
| Error | Banner + retry |
| Weight sum off | Warning badge `Σ weights 98.2%` with `risk.warning` |

---

## 9. Interactions

1. Sort column headers (aria-sort).
2. Search filters client-side.
3. Sector filter.
4. Row click → **v0 optional** detail drawer (skip unless cheap); default no navigation.
5. Changing SmallcaseSelect reloads table.
6. Range change updates return/contrib columns only.

---

## 10. Tailwind structure sketch

```tsx
<main className="mx-auto max-w-[1440px] px-6 py-6 flex flex-col gap-6">
  <header className="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 className="text-xl font-semibold text-[var(--text-primary)]">Holdings</h1>
      <p className="text-sm text-[var(--text-secondary)]">{/* name · as-of */}</p>
    </div>
    {/* RangeChips */}
  </header>

  {/* SummaryStrip */}

  <div className="flex flex-wrap items-center gap-3">
    {/* search + filters */}
  </div>

  <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] overflow-hidden">
    {/* HoldingsTable */}
  </section>

  <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {/* WeightBars | SectorBreakdown */}
  </section>
</main>
```

---

## 11. Acceptance (Holdings)

- [ ] Full-width sortable table with sticky header
- [ ] Weight shown as % + micro bar
- [ ] Summary strip: count, concentration, weight sum
- [ ] Sector chart only when sector data exists
- [ ] P&L columns color + sign; omitted cleanly when data missing
- [ ] Desktop density ~36–40px rows

---

## 12. Out of scope (v0)

- Drag-and-drop rebalance  
- Inline weight editing  
- Treemap as primary view  
- Per-name price history drawer (nice-to-have)  
