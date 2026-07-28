# Design System — Smallcase Finance (v0)

Finance-first visual language for the local analysis UI.  
**Default theme: dark mode.** Light mode is supported with the same structure and semantics.  
**Stack:** Tailwind CSS tokens → map to CSS variables for theme switching.  
**Audience:** Single power user scanning NAV, returns, risk, and composition.

Companion architecture: [`docs/architecture/ui.md`](../architecture/ui.md)  
Page specs: [`pages/dashboard.md`](./pages/dashboard.md) · [`pages/holdings.md`](./pages/holdings.md) · [`pages/performance.md`](./pages/performance.md)  
Components: [`components.md`](./components.md)

---

## 1. Design Principles

1. **Density without clutter** — more data per viewport than a marketing site; still clear hierarchy.
2. **Glanceable P&L** — green/red only for performance semantics; never decorative.
3. **Charts & tables are first-class** — chrome stays quiet so data surfaces dominate.
4. **Tabular honesty** — numbers align, decimals consistent, no ornamental fonts on metrics.
5. **Dark-default endurance** — comfortable for long sessions; light mode for daylight/export screenshots.
6. **Desktop primary** — design for 1280–1440px first.

---

## 2. Color Tokens

Use semantic names, not raw hex in components. Hex below are v0 defaults (tweak once in tokens).

### 2.1 Core surfaces (dark default)

| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `bg.app` | `#0B0F14` | `#F4F6F8` | App background |
| `bg.surface` | `#121821` | `#FFFFFF` | Cards, panels, tables |
| `bg.surfaceRaised` | `#1A222D` | `#FFFFFF` | Dropdowns, popovers, modals |
| `bg.muted` | `#1C2430` | `#EEF1F4` | KPI well, chip bg, table header |
| `bg.hover` | `#243041` | `#E8ECF0` | Row / nav hover |
| `border.default` | `#2A3544` | `#D8DEE6` | Card borders, dividers |
| `border.subtle` | `#1E2733` | `#E8EDF2` | Internal grid lines |

### 2.2 Text

| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `text.primary` | `#E8EEF6` | `#0F172A` | Titles, primary values |
| `text.secondary` | `#9AA8B8` | `#5B6B7C` | Labels, axis, metadata |
| `text.muted` | `#6B7A8C` | `#8B98A8` | Placeholders, disabled |
| `text.inverse` | `#0B0F14` | `#FFFFFF` | On solid accent buttons |

### 2.3 Brand / accent (structure, not P&L)

| Token | Value | Usage |
|-------|-------|-------|
| `accent.primary` | `#3B82F6` | Links, active nav, focus rings, primary buttons |
| `accent.primaryHover` | `#60A5FA` | Hover on accent |
| `accent.subtle` | `rgba(59,130,246,0.12)` | Active nav pill, selected chip |

Keep brand blue **out of** return coloring so P&L stays unambiguous.

### 2.4 P&L and risk semantics

| Token | Dark | Light | Meaning |
|-------|------|-------|---------|
| `pnl.positive` | `#22C55E` | `#16A34A` | Gains, up ticks, positive contrib |
| `pnl.negative` | `#EF4444` | `#DC2626` | Losses, down ticks, drawdowns |
| `pnl.positiveMuted` | `rgba(34,197,94,0.12)` | `rgba(22,163,74,0.10)` | Positive row/chip background |
| `pnl.negativeMuted` | `rgba(239,68,68,0.12)` | `rgba(220,38,38,0.10)` | Negative row/chip background |
| `risk.warning` | `#F59E0B` | `#D97706` | Elevated risk, stale data caution |
| `risk.critical` | `#F97316` | `#EA580C` | Severe breach (rare in v0) |
| `neutral.flat` | `#9AA8B8` | `#64748B` | ~0 change, flat P&L |

**Rules**
- Never use green/red for navigation or success toasts that are not return-related if avoidable; prefer accent blue for system success.
- Drawdown charts: use `pnl.negative` fill at ~20–30% opacity; line slightly stronger.
- Zero / missing: `neutral.flat` or em dash `—`, never fake green.

### 2.5 Chart series palette

Distinct from P&L; for multi-series composition/equity:

| Series | Color | Notes |
|--------|-------|-------|
| Portfolio | `#60A5FA` | Primary line |
| Benchmark | `#A78BFA` | Secondary line (dashed optional) |
| Excess / alpha | `#2DD4BF` | Optional |
| Sector 1–8 | `#60A5FA`, `#34D399`, `#FBBF24`, `#F472B6`, `#A78BFA`, `#22D3EE`, `#FB923C`, `#94A3B8` | Cycle; avoid pure P&L red/green as sector IDs |

Gridlines: `border.subtle`; axis text: `text.secondary`.

### 2.6 Paste-ready CSS variables (`globals.css`)

Dark is the **default** on `:root`. Light overrides via `data-theme="light"` (or `.light` if preferred).

```css
/* === Smallcase Finance design tokens — paste into app/globals.css === */

:root {
  color-scheme: dark;

  /* Surfaces */
  --bg-app: #0b0f14;
  --bg-surface: #121821;
  --bg-surface-raised: #1a222d;
  --bg-muted: #1c2430;
  --bg-hover: #243041;

  /* Borders */
  --border-default: #2a3544;
  --border-subtle: #1e2733;

  /* Text */
  --text-primary: #e8eef6;
  --text-secondary: #9aa8b8;
  --text-muted: #6b7a8c;
  --text-inverse: #0b0f14;

  /* Brand (structure — not P&L) */
  --accent: #3b82f6;
  --accent-hover: #60a5fa;
  --accent-subtle: rgba(59, 130, 246, 0.12);

  /* P&L / risk */
  --pnl-pos: #22c55e;
  --pnl-neg: #ef4444;
  --pnl-pos-muted: rgba(34, 197, 94, 0.12);
  --pnl-neg-muted: rgba(239, 68, 68, 0.12);
  --risk-warning: #f59e0b;
  --risk-critical: #f97316;
  --neutral-flat: #9aa8b8;

  /* Chart series */
  --chart-portfolio: #60a5fa;
  --chart-benchmark: #a78bfa;
  --chart-excess: #2dd4bf;
  --chart-grid: var(--border-subtle);
  --chart-axis: var(--text-secondary);

  /* Radii */
  --radius-sm: 6px;   /* chips */
  --radius-md: 8px;   /* cards, inputs */
  --radius-lg: 12px;  /* modals */

  /* Shell */
  --nav-width: 220px;
  --nav-width-collapsed: 64px;
  --topbar-height: 56px;
  --content-max: 1440px;
}

[data-theme="light"] {
  color-scheme: light;

  --bg-app: #f4f6f8;
  --bg-surface: #ffffff;
  --bg-surface-raised: #ffffff;
  --bg-muted: #eef1f4;
  --bg-hover: #e8ecf0;

  --border-default: #d8dee6;
  --border-subtle: #e8edf2;

  --text-primary: #0f172a;
  --text-secondary: #5b6b7c;
  --text-muted: #8b98a8;
  --text-inverse: #ffffff;

  --accent: #2563eb;
  --accent-hover: #3b82f6;
  --accent-subtle: rgba(37, 99, 235, 0.1);

  --pnl-pos: #16a34a;
  --pnl-neg: #dc2626;
  --pnl-pos-muted: rgba(22, 163, 74, 0.1);
  --pnl-neg-muted: rgba(220, 38, 38, 0.1);
  --risk-warning: #d97706;
  --risk-critical: #ea580c;
  --neutral-flat: #64748b;

  --chart-portfolio: #2563eb;
  --chart-benchmark: #7c3aed;
  --chart-excess: #0d9488;
}
```

Base body recipe:

```css
body {
  background: var(--bg-app);
  color: var(--text-primary);
  font-feature-settings: "tnum" 1, "lnum" 1;
}
```

### 2.7 Tailwind config extension (optional)

```js
// tailwind.config.ts — theme.extend excerpt
{
  colors: {
    app: "var(--bg-app)",
    surface: {
      DEFAULT: "var(--bg-surface)",
      raised: "var(--bg-surface-raised)",
      muted: "var(--bg-muted)",
      hover: "var(--bg-hover)",
    },
    border: {
      DEFAULT: "var(--border-default)",
      subtle: "var(--border-subtle)",
    },
    ink: {
      DEFAULT: "var(--text-primary)",
      secondary: "var(--text-secondary)",
      muted: "var(--text-muted)",
      inverse: "var(--text-inverse)",
    },
    accent: {
      DEFAULT: "var(--accent)",
      hover: "var(--accent-hover)",
      subtle: "var(--accent-subtle)",
    },
    pnl: {
      pos: "var(--pnl-pos)",
      neg: "var(--pnl-neg)",
      "pos-muted": "var(--pnl-pos-muted)",
      "neg-muted": "var(--pnl-neg-muted)",
    },
    chart: {
      portfolio: "var(--chart-portfolio)",
      benchmark: "var(--chart-benchmark)",
      excess: "var(--chart-excess)",
    },
  },
  borderRadius: {
    sm: "var(--radius-sm)",
    md: "var(--radius-md)",
    lg: "var(--radius-lg)",
  },
  maxWidth: {
    content: "var(--content-max)",
  },
  width: {
    nav: "var(--nav-width)",
    "nav-collapsed": "var(--nav-width-collapsed)",
  },
  height: {
    topbar: "var(--topbar-height)",
  },
}
```

Example utilities after extension:
- Page: `bg-app text-ink`
- Card: `bg-surface border border-border rounded-md p-4`
- Gain: `text-pnl-pos`
- Without extension, use arbitrary values: `bg-[var(--bg-surface)]`

### 2.8 Chart sector cycle (non-token array)

```
#60A5FA #34D399 #FBBF24 #F472B6 #A78BFA #22D3EE #FB923C #94A3B8
```

Do not use pure P&L red/green as sector identity colors.

---

## 3. Typography

### Font stack

| Role | Stack | Rationale |
|------|-------|-----------|
| UI / body | `Inter, ui-sans-serif, system-ui, sans-serif` | Clean, excellent at small sizes |
| Numbers (metrics, tables) | `tabular-nums` on Inter; optional `"JetBrains Mono", ui-monospace` for tickers only | Alignment; tickers feel market-like |
| Fallback | system fonts if Inter not loaded | Local-first, no hard CDN dependency |

Load Inter via `next/font` when frontend is built.

### Scale

| Token | Size / line | Weight | Use |
|-------|-------------|--------|-----|
| `display` | 28–32px / 1.2 | 600 | Rare; page hero numbers only if needed |
| `title` | 20px / 1.3 | 600 | Page title |
| `subtitle` | 16px / 1.4 | 500 | Section titles in cards |
| `body` | 14px / 1.5 | 400 | Default prose, table cells |
| `label` | 12px / 1.4 | 500 | KPI labels, overlines, chips |
| `micro` | 11px / 1.3 | 400–500 | Chart axes, timestamps, legal-ish meta |
| `kpi` | 24–28px / 1.2 | 600 | Primary metric values |
| `kpiSm` | 18–20px / 1.2 | 600 | Secondary metrics in dense strips |

**Always** apply `tabular-nums` (and `lining-nums` if available) to financial figures.

### Number formatting (INR-friendly)

| Kind | Format | Example |
|------|--------|---------|
| NAV / large INR | Indian grouping when locale `en-IN` | `₹12,48,320.50` or compact `₹12.5L` in tight KPI |
| Price | 2 decimals default | `2,841.25` |
| Weight / % | 1 decimal typical; 2 for fine weights | `8.4%` |
| Returns | 1–2 decimals + sign | `+18.42%`, `-3.10%` |
| Ratios (Sharpe) | 2 decimals | `1.24` |
| Counts | integer | `22` names |

- Prefer **explicit sign** on returns (`+` / `−`).
- Color + sign together (don’t rely on color alone — accessibility).
- Missing: `—` (em dash), not `0` or `N/A` spam.

---

## 4. Spacing & Layout

### Base unit
**4px grid.** Tailwind scale is the source of truth.

| Token | px | Common use |
|-------|-----|------------|
| `space-1` | 4 | Icon gaps |
| `space-2` | 8 | Chip padding, tight stacks |
| `space-3` | 12 | Compact card padding |
| `space-4` | 16 | Default card padding, nav item |
| `space-5` | 20 | Section internal |
| `space-6` | 24 | Card grid gap |
| `space-8` | 32 | Between major page sections |
| `space-10` | 40 | Page top padding |

### Shell dimensions

| Element | Spec |
|---------|------|
| Left nav width | 220px expanded / 64px collapsed |
| Top bar height | 56px |
| Content max width | 1440px (or full for wide tables) |
| Page padding | 24px desktop |
| Card radius | `rounded-lg` (8px) |
| Chip radius | `rounded-md` (6px) |
| Modal radius | `rounded-xl` (12px) |

### Density

- **Tables:** row height ~36–40px; header 36px; horizontal cell pad 12px.
- **KPI cards:** pad 16px; gap 16px in grid.
- **Forms (later):** 40px control height.

Avoid large empty hero regions. Prefer content starting within one scroll fold.

---

## 5. Elevation & Borders

Dark mode elevation is **border + slight surface step**, not heavy shadows.

| Level | Treatment |
|-------|-----------|
| Flat (app bg) | no border |
| Card | 1px `border.default`, optional `shadow-sm` only in light mode |
| Raised (menu) | `bg.surfaceRaised` + 1px border + soft shadow `0 8px 24px rgba(0,0,0,0.35)` dark |
| Focus | 2px ring `accent.primary` at 40–60% opacity |

---

## 6. Component Specs (design-level)

**Full props/states/file map:** [`components.md`](./components.md)  
Below is the visual summary only.

### 6.1 KPI Card (`MetricCard`)

**Props (conceptual):** `label`, `value`, `delta?`, `deltaLabel?`, `sentiment?: 'pos'|'neg'|'flat'|'none'`, `onClick?`, `loading?`

**Variants**
- `default` — surface card
- `compact` — for secondary strips
- `interactive` — hover border accent, cursor pointer

**Anatomy**
```
┌────────────────────┐
│ Return (1Y)        │  label: text.secondary, label size
│ +18.42%            │  value: kpi size, tabular, pnl color if sentiment
│ vs Nifty +2.1pp    │  delta: micro/label, muted or pnl
└────────────────────┘
```

Tailwind sketch:
`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 flex flex-col gap-1`

### 6.2 Nav item

- Idle: `text.secondary`
- Hover: `bg.hover`, `text.primary`
- Active: `bg` = `accent.subtle`, text = `accent.primary`, optional left bar 2px accent

### 6.3 Smallcase Switcher trigger

- Height 36px; min-width ~200px.
- Content: name (truncate) + chevron; optional return chip with P&L color.
- Open: raised menu, max-height 320px scroll, active row checkmark.

### 6.4 Range chips

- Group of toggles: `1M 3M 6M 1Y 3Y YTD SI`
- Selected: accent subtle fill + accent text
- Unselected: muted border, secondary text
- Height 32px; `text-label`

### 6.5 Data table

- Header: `bg.muted`, `text.secondary`, `label` weight 500, sticky.
- Body: `body` 14px; numeric `text-right tabular-nums`.
- Hover row: `bg.hover`.
- Positive/negative cells: color text only (or muted bg on contribution column if needed).
- Sort indicator: subtle caret in accent or secondary.

### 6.6 Chart panel

```
┌─ Title ────────────────────────── Controls/Legend ─┐
│                                                     │
│                   [ chart body ]                    │
│                                                     │
│  source / as-of footer (micro, muted)               │
└─────────────────────────────────────────────────────┘
```

- Padding 16px; title `subtitle`.
- Tooltip: raised surface, 12–13px, tabular numbers, date as heading.
- No chart junk: skip heavy gradients; 1–2px strokes; limited markers.

### 6.7 Buttons

| Variant | Use |
|---------|-----|
| `primary` | Solid accent; inverse text |
| `secondary` | Border default; primary text |
| `ghost` | No border; hover muted |
| `danger` | Rare; destructive local actions only |

Height 36px default; icon buttons 32px.

### 6.8 Badges / chips

- `neutral` — muted bg  
- `positive` / `negative` — pnl muted bg + pnl text  
- `warning` — risk.warning soft bg  
- `info` — accent subtle  

---

## 7. Iconography

- Use a single set (e.g. Lucide) at 16px / 20px.
- Stroke icons, 1.5–2px weight to match Inter.
- Avoid filled multicolor icons in nav.
- Directional P&L: small caret up/down next to returns (redundant with color).

---

## 8. Motion

- Keep minimal for data trust.
- Theme toggle: instant or ≤150ms fade on surfaces.
- Chart draw: optional short mount animation; prefer static on re-filter for snappiness.
- Dropdowns: 100–150ms ease-out.
- No celebratory confetti on green days.

---

## 9. Accessibility

- Contrast: primary text on app/surface ≥ WCAG AA.
- P&L: never color-only — include `+`/`−` or icons.
- Focus visible on all controls (keyboard switcher, chips, nav).
- Tables: proper `<th>` / scope when implemented; sortable buttons not clickable bare text only.
- Theme: respect `data-theme` or `class="dark"`; optional `prefers-color-scheme` for first visit, then persist user choice in `localStorage`.

---

## 10. Theme Behavior

| Item | Spec |
|------|------|
| Default | Dark |
| Toggle | Top bar sun/moon (or “Theme”) |
| Persistence | `localStorage` key e.g. `sf-theme` |
| Charts | Re-read CSS variables or theme-aware palette on toggle so grid/series stay legible |

---

## 11. Do / Don’t

**Do**
- Right-align numbers; left-align names.
- Put the equity curve where the eye lands first on Dashboard/Performance.
- Use muted chrome so green/red pop only on P&L.
- Prefer Indian locale number formatting when market is IN.

**Don’t**
- Use green backgrounds for “success” navigation states.
- Mix 3+ decimal styles on the same page without reason.
- Add illustration-heavy empty states; short copy + path to data is enough.
- Gold-plate gradients, glassmorphism, or dense marketing cards.

---

## 12. Handoff Checklist (Frontend)

- [ ] Paste §2.6 CSS variables into `globals.css`; dark default on `:root`
- [ ] Optional §2.7 Tailwind theme extend
- [ ] Inter via `next/font` + `tabular-nums` / `font-feature-settings: "tnum"` on metrics
- [ ] Implement primaries per [`components.md`](./components.md): MetricCard, PerformanceChart, HoldingsTable, SmallcaseSelect
- [ ] Pages per `docs/design/pages/*`
- [ ] P&L tokens used only for performance semantics
- [ ] Shell spacing matches §4
- [ ] No business logic in design tokens file

---

## 13. Open design decisions (non-blocking)

| Topic | v0 recommendation |
|-------|-------------------|
| Table density toggle | Ship compact only |
| Number grouping | `en-IN` when currency INR |
| Benchmark stroke | Dashed benchmark, solid portfolio |
| Contribution cell bg | Text color only (no muted fill) |
| Equity Y-axis | NAV (base 100) over cumulative % |
| Recharts vs Tremor | Recharts for series; plain Tailwind for chrome |
