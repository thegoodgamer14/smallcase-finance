# SIP Lab clarity review — first-time external visitor

**Role:** Design agent  
**Date:** 2026-07-28  
**Scope:** Implemented `/sip-lab` UI + Dashboard callout (actual TSX, not page-spec only)  
**Job to be done:** External visitor understands and runs a monthly SIP basket backtest without prior product knowledge; trusts **XIRR** and does not confuse demo with real history.  
**Primary files read:**

| Surface | Path |
|---------|------|
| SIP Lab page | `apps/web/src/app/sip-lab/page.tsx` |
| Dashboard | `apps/web/src/app/page.tsx` |
| Callout | `apps/web/src/components/sip/SipDashCallout.tsx` |
| Methodology | `apps/web/src/components/sip/MethodologyPanel.tsx` |
| How-to-read | `apps/web/src/components/sip/HowToReadPanel.tsx` |
| Data source | `apps/web/src/components/sip/DataSourceChip.tsx` |
| Cashflows / holdings | `SipCashflowTable.tsx`, `SipHoldingTable.tsx` |
| Shared | `EmptyState.tsx`, `MetricCard.tsx`, `AppShell.tsx` |

**What already works (do not regress):**

- Hero names the job + XIRR in plain language; scope line (equities/ETFs, zero costs, not trading).
- Empty → loading skeletons → error with retry → success path exists.
- Demo vs Upstox chip + banner after run (ADR 005 intent).
- Stale-params warning after edit.
- Methodology accordion forced open when idle/demo.
- XIRR is the visual hero (`text-3xl`, first in KPI strip).
- Dashboard has a visible strip → `/sip-lab`.

---

## Prioritized fixes (max 12)

Severity: **P0** blocks understanding or trust · **P1** causes confusion/misread · **P2** polish that still hurts first-run.

---

### 1. P0 — Cashflow signs read as “losses,” not “money you put in”

**Where:** `SipCashflowTable.tsx` (header + amount cells); How-to-read cashflow bullet.

**Issue:**  
- Header microcopy: *“Outflows negative · terminal positive”* is engine-speak.  
- Type label **“Terminal”** is opaque (means “ending portfolio value counted as inflow for XIRR”).  
- Contribution amounts use `pnl-neg` (red) and terminal uses `pnl-pos` (green). Finance users associate red with loss; a first-timer scans red SIP rows and thinks the basket lost money every month.

**Fix:**

| Element | Suggested copy / behavior |
|---------|---------------------------|
| Table subtitle | `Each monthly SIP is cash you paid in (shown as −). The last row is the ending portfolio value (shown as +). XIRR uses both.` |
| Kind labels | `Contribution` → keep; `Terminal` → **`Ending value`** (or “Final portfolio value”) |
| Color | Prefer **neutral** for contributions (`text-primary` / muted) and green only for ending value; **or** keep sign color but add a legend chip: `− cash in · + ending value` — never imply P&amp;L on contribution rows |
| Optional column | `Role` / plain note: “Cash out of pocket” vs “What the basket is worth” |

**DoD:** Visitor can explain why amounts are negative without reading methodology.

---

### 2. P0 — Dashboard callout still requires product history jargon

**Where:** `SipDashCallout.tsx` body; entry from `app/page.tsx`.

**Issue:** Body copy:

> Dashboard shows **weight-based NAV** for this smallcase. SIP Lab answers a different question: monthly cash SIPs into a basket, with **XIRR** as the result.

“Weight-based NAV” is v0-internal. A visitor who landed on Dashboard first has no definition of NAV, weight rebalance, or XIRR in this strip.

**Fix (plain-language rewrite):**

| Key | Copy |
|-----|------|
| Title | Keep `Try SIP Lab` |
| Body | `This page shows how a rebalanced basket’s index performed. SIP Lab is different: it simulates putting a fixed ₹ amount into a basket every month and reports one annualized return (XIRR).` |
| CTA | Keep `Open SIP Lab` |
| Optional | One-line under CTA: `No orders · equities & ETFs only` |

**DoD:** Callout is understandable without visiting SIP Lab or knowing “NAV.”

---

### 3. P0 — Pre-run data-source copy is pipeline jargon

**Where:** `page.tsx` data-source strip + under Run button; `DataSourceChip` / banner post-run are better.

**Issue:** Pre-run strings:

- *“Run will use curated prices (Upstox sync path).”*  
- *“No Upstox token configured — run will use demo/sample prices.”*

“Curated,” “sync path,” and “token” are operator language. First-timers cannot map these to “real market history vs demo.”

**Fix:**

| State | Chip / helper copy |
|-------|--------------------|
| Upstox ready | `Real history available (Upstox). Results after run will say so.` |
| Demo path | `Demo prices — not live market performance. Connect Upstox for real history.` |
| Global strip | Keep *“Real history: Upstox only. Sample data is labeled Demo.”* (clear) |

Also: **dedupe** — same Upstox/demo sentence appears in the top strip **and** under the Run button (`page.tsx` ~331–353 and ~563–567). Keep one high-visibility strip; under-CTA can be a single short line only when demo risk is high.

**DoD:** No “token / curated / sync path” in visitor-facing UI; demo risk is obvious before first run.

---

### 4. P1 — Empty results: no action control, weak hierarchy

**Where:** Idle branch `EmptyState` in `page.tsx` (~589–599); `EmptyState.tsx` itself.

**Issue:**

- Title/description are good and match locked copy.  
- `action` is **muted static text** (“Results appear here after you run”), not a control.  
- On wide layouts, config is sticky left and empty panel is large — first-timer may not connect the big empty card to **Run backtest**.  
- No visual affordance (icon / numbered 1–2–3) linking to the form.

**Fix:**

1. Primary button in empty state: **`Configure & run →`** that `scrollIntoView` / focuses `#configure` and preferably the Run control (or `document.getElementById('sip-amount')`).  
2. Optional 3-step micro list in empty body: `1 Basket · 2 Monthly amount & dates · 3 Run backtest`.  
3. Keep muted “Results appear here…” as secondary, not the only action.

**DoD:** Idle results column has one obvious next step that moves focus to the form.

---

### 5. P1 — KPI hints only via native `title` (hover); invisible on touch

**Where:** `MetricCard.tsx` (`title={hint}`); XIRR card uses `title` for engineer tooltip including *“Engine fixture tolerance ≤ 0.0001.”*

**Issue:** Hints for Total invested / Final value / Absolute gain / Max drawdown exist in code but only as browser tooltips. Mobile/trackpad users never see them. XIRR tooltip mixes product truth with **fixture tolerance** (builder language).

**Fix:**

| Metric | Visible microcopy (always or via info popover, not `title` alone) |
|--------|-------------------------------------------------------------------|
| XIRR | Keep short definition under value (already good). Drop “fixture tolerance” from visitor tooltip; keep in methodology or docs only. |
| Total invested | One line under value on compact cards **or** shared strip (already have compare helper — elevate it closer to the three money KPIs) |
| Final value / Absolute gain | Same |
| Max drawdown | `Worst drop from a peak — path risk, not XIRR` as visible sublabel |
| Contributions | Add hint: `Number of monthly SIPs in this run` |

**DoD:** Core money metrics are glossed without hover; no engine-fixture language in UI tooltips.

---

### 6. P1 — Basket vs Strategy naming mismatch; no composition preview

**Where:** Config card title **“Basket”** + field label **“Strategy”** (`page.tsx` ~364–404).

**Issue:** Visitor is told they pick a “basket” then sees a control named “Strategy.” Only optional `summary` text appears; **no constituents / weights** before run. They may run without knowing what they SIPed into.

**Fix:**

1. Align label: `Basket` (or `SIP basket`) for the select; keep internal id as strategy.  
2. Under select, when strategy loads: **mini list** (top 5 symbols + weights, “+N more”) or “N equities/ETFs · equal weight / custom” from API fields.  
3. If strategies empty: empty control already says “No strategies available” — add recovery line: *“Start the API and ensure strategy configs are loaded.”* (operator-facing is OK here).

**DoD:** Field name matches section title; visitor sees what is inside the basket before Run.

---

### 7. P1 — Holdings table abbreviations and missing loading state

**Where:** `SipHoldingTable.tsx`; tab switch on results.

**Issue:**

- Headers: **Weight end**, **MV end**, **Cash in** — abbreviations and “end” without “as of end date.”  
- No `loading` prop: during run, if user is on “By holding,” table shows *“No holding breakdown for this run”* (false empty).  
- No plain-language intro under title.

**Fix:**

| Header | Label |
|--------|--------|
| Weight end | `Weight (end)` or `End weight` |
| Units | keep |
| MV end | `Value (end)` |
| Cash in | `Cash put in` |

Add one-line subtitle: `How each name contributed cash and ending value.`  
Pass `loading={runState === "loading"}` and skeleton rows like cashflows.

**DoD:** Headers readable without finance slang; no false empty during load.

---

### 8. P1 — Success assumptions footer dumps engine fields

**Where:** `page.tsx` success footer (~824–837).

**Issue:** Renders raw assumption keys:

> Day rule: {sip_day_rule}. Costs: … Price field: close. XIRR day count: actual/365. … Not v0 rebalance NAV.

Looks like a log line. “v0 rebalance NAV” is product-history jargon. Idle footer is clearer than the success footer.

**Fix:** Human sentence template:

> SIPs on calendar day **{n}** (next trading day if closed) · **No costs** in this version · Prices: **session close** · XIRR uses **actual/365** day count · Currency **INR** · Headline metric: **XIRR** (not the Dashboard index return).

**DoD:** Footer readable as prose; no “v0” in visitor UI.

---

### 9. P1 — Form invalid states are silent

**Where:** `formValid` + `aria-invalid` on amount/day/strategy; Run `disabled` when invalid (`page.tsx` ~192–198, ~508–514).

**Issue:** Disabled **Run backtest** with no visible reason. `aria-invalid` alone does not surface “day must be 1–28” or “amount must be &gt; 0” to sighted users. End date vs “To latest” is clear; amount/day are not.

**Fix:**

- Inline helper when `dayOfMonth` outside 1–28: `Use a day from 1 to 28 so every month has that date.`  
- When `amount ≤ 0`: `Enter a monthly amount greater than ₹0.`  
- When Run disabled: optional one-line under button in muted/warning: `Fix the fields above to run.`  
- Keep day helper that already explains next-session rule (good).

**DoD:** User never stares at a dead primary button without knowing why.

---

### 10. P2 — How-to-read + methodology overload on first paint

**Where:** `MethodologyPanel` `forceOpen={demoResult || !result}` (open by default idle); `HowToReadPanel` always under results; six methodology blocks include **yfinance/bhavcopy** and **“Not the Dashboard NAV backtest.”**

**Issue:** First visit stacks: hero XIRR explanation + methodology (6 blocks, often expanded) + empty state + full how-to-read list. Dense for “just run something.” Some methodology lines are competitive-policy (good for trust) but **“Not the Dashboard NAV backtest”** assumes they used Dashboard.

**Fix:**

1. Default methodology **collapsed** after first successful non-demo run (already partially via localStorage); on idle, keep open **or** open only first 2 blocks (zero costs + SIP day) with “Show more.”  
2. How-to-read: collapse behind summary on idle (`How to read results` accordion); expand by default after success.  
3. Soften not-v0 line: *“This is not the same as the Dashboard’s index-style return. Don’t mix the two numbers.”*  
4. Keep Upstox-only / demo warnings high priority; move vendor denylist (yfinance…) to last or docs-only if space is tight.

**DoD:** First screen prioritizes Configure + Run; help is one click away, not a wall of text.

---

### 11. P2 — Export is technical and unexplained when disabled

**Where:** Export menu in `page.tsx` (~526–560); `export.ts`.

**Issue:**

- Menu: **“Summary JSON”** / **“Cashflows CSV”** — developer artifact names.  
- Button disabled pre-run with no helper (“Export available after a successful run”).  
- CSV headers `date,kind,amount` with raw `kind` values — OK for power users; UI labels should still be plain.

**Fix:**

| Menu item | Label |
|-----------|--------|
| JSON | `Download full results (JSON)` |
| CSV | `Download cashflow list (CSV)` |

Disabled state title/helper: `Run a backtest to export.`  
Optional: short note that CSV matches the cashflow table (including signs).

**DoD:** Export purpose clear to non-developers; disabled reason visible.

---

### 12. P2 — XIRR hero definition competes with the number; secondary KPIs cramped

**Where:** KPI grid `grid-cols-2 lg:grid-cols-6` with XIRR `col-span-2` + five compact `MetricCard`s (`page.tsx` ~635–748).

**Issue:**

- Under XIRR: long definition paragraph **plus** date/SIP-day sublabel — good content, but on first success the eye jumps between giant % and a multi-line essay before seeing ₹ invested/final.  
- On `lg`, five compact cards share remaining columns; labels wrap; “Contributions” as `N SIPs` is unclear vs “cashflows.”  
- Compare helper sits **below** the entire KPI row — easy to miss.

**Fix:**

1. XIRR card: **value first**, one short line: `Annualized return on all SIPs + ending value.` Move long definition to info popover or How-to-read only.  
2. Group money trio (Invested · Final · Gain) visually (shared border or subgrid) with the compare helper **immediately under that group**.  
3. Rename Contributions → **`# of SIPs`** or **`SIP count`**.  
4. Consider `lg:grid-cols-12` with XIRR span 4, money trio span 5, risk/count span 3 for clearer hierarchy.

**DoD:** Glance path is XIRR % → invested vs final → chart; prose does not bury the number.

---

## Out of scope / non-issues for this review

- Engine correctness, XIRR tolerance, API shapes.  
- Adding Coin/MF, Kite import, live orders (product non-goals).  
- Reusing `POST /backtest` rebalance for SIP (correctly separate path).  
- Global AppShell correctly hides range chips on `/sip-lab`.

---

## Suggested implementation order (frontend)

1. Cashflow labels + colors (#1)  
2. Dashboard callout + pre-run source copy (#2, #3)  
3. Empty-state CTA (#4)  
4. Visible KPI gloss + assumptions prose (#5, #8)  
5. Basket naming + composition peek (#6)  
6. Holdings headers + loading (#7)  
7. Form validation messages (#9)  
8. Progressive disclosure + export labels + KPI layout (#10–12)

---

## Traceability

| Fix | Components / lines (approx.) |
|-----|------------------------------|
| 1 | `SipCashflowTable.tsx` 27–32, 10–15, 74–83 |
| 2 | `SipDashCallout.tsx` 22–29 |
| 3 | `page.tsx` 331–353, 563–567; optionally `DataSourceChip.tsx` |
| 4 | `page.tsx` 589–599; `EmptyState.tsx` |
| 5 | `MetricCard.tsx`; `page.tsx` 642–674, 684–747 |
| 6 | `page.tsx` 363–410 |
| 7 | `SipHoldingTable.tsx` |
| 8 | `page.tsx` 824–847 |
| 9 | `page.tsx` 192–198, 418–505, 508–514 |
| 10 | `MethodologyPanel.tsx`; `HowToReadPanel.tsx`; forceOpen in `page.tsx` 572 |
| 11 | `page.tsx` 526–560 |
| 12 | `page.tsx` 634–753 |

**Companion locked copy:** `docs/design/copy/sip-lab-external.md` — update callout/source strings there when frontend lands so copy stays single-sourced.
