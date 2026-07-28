# SIP Lab — External visitor copy & glossary

**Audience:** Frontend (UI strings), Product (tone), anyone writing tooltips/help  
**Goal:** A visitor with **no finance-product background** can understand SIP Lab, run a backtest, and not confuse demo numbers with live market claims.  
**Tone:** Plain language, short sentences, no jargon without a gloss. Calm and precise — finance tool, not marketing site.  
**Companion page spec:** [pages/sip-lab.md](../pages/sip-lab.md)

---

## 1. Product in one breath

| Key | Copy |
|-----|------|
| `product.name` | `SIP Lab` |
| `product.tagline` | `Monthly SIP into a stock/ETF basket — results as XIRR.` |
| `product.one_paragraph` | `SIP Lab shows what would have happened if you invested a fixed amount every month into a custom basket of stocks or ETFs. You set the basket, the monthly amount, and the dates. The main answer is XIRR: one annualized return number that accounts for every contribution and the ending value of the portfolio.` |
| `product.not_this` | `This is a backtest lab, not a broker. It does not place orders, import mutual funds, or promise future returns.` |

---

## 2. Locked UI strings (external-facing)

Use these verbatim in the app where keys match the page spec.

### Hero

| Key | Copy |
|-----|------|
| `hero.title` | `SIP Lab` |
| `hero.subtitle` | `See what a monthly SIP into a stock/ETF basket would have returned.` |
| `hero.metric_line` | `Primary result: XIRR — the annualized return on every contribution plus your ending portfolio value.` |
| `hero.scope_line` | `Equities & ETFs only · Zero transaction costs in this version · Not live trading` |
| `hero.link_methodology` | `How SIP Lab works` |

### XIRR

| Key | Copy |
|-----|------|
| `xirr.definition` | `Annualized return on all SIPs + ending value.` |
| `xirr.definition_long` | `XIRR is the single annualized rate that makes all your SIP cash outflows and the final portfolio value balance out over time.` |
| `xirr.tooltip` | `Uses contribution dates and amounts plus ending portfolio value. Not the same as the Dashboard’s index-style return.` |
| `xirr.kpi_label` | `XIRR` |
| `xirr.null` | `Need at least two cashflows` |

### Invested vs final value

| Key | Copy |
|-----|------|
| `invested.label` | `Total invested` |
| `invested.hint` | `Sum of all monthly SIP contributions (cash you put in).` |
| `final.label` | `Final value` |
| `final.hint` | `Market value of units held at the end date (what the basket is worth).` |
| `gain.label` | `Absolute gain` |
| `gain.hint` | `Final value minus total invested. Positive means the basket grew more than cash put in.` |
| `compare.helper` | `Invested is cash in. Final value is what those units are worth. XIRR annualizes the path between them.` |

### Demo vs Upstox

| Key | Copy |
|-----|------|
| `source.upstox.chip` | `Prices: Upstox (cached)` |
| `source.sample.chip` | `Demo / sample prices — not live market SIP performance` |
| `source.partial.chip` | `Partial Upstox coverage · some symbols sample or missing` |
| `source.sample.banner` | `These results use demo or sample prices. Do not treat them as real market SIP performance. Connect Upstox and sync history for real claims.` |
| `source.upstox.banner` | `Prices from Upstox history (cached). Sole market-data source for real runs.` |
| `source.pre_run.upstox` | `Real history available (Upstox). Results after run will say so.` |
| `source.pre_run.sample` | `Demo prices — not live market performance. Connect Upstox for real history.` |
| `source.pre_run.sample_short` | `Demo prices — not live market performance.` |
| `source.global_note` | `Real history: Upstox only. Sample data is labeled Demo.` |

### Dashboard callout

| Key | Copy |
|-----|------|
| `dash_callout.title` | `Try SIP Lab` |
| `dash_callout.body` | `This page shows how a rebalanced basket’s index performed. SIP Lab is different: it simulates putting a fixed ₹ amount into a basket every month and reports one annualized return (XIRR).` |
| `dash_callout.scope` | `No orders · equities & ETFs only` |
| `dash_callout.cta` | `Open SIP Lab` |

### Empty / loading / error / CTA

| Key | Copy |
|-----|------|
| `empty.title` | `Run a SIP backtest` |
| `empty.description` | `Pick a basket, set monthly amount and dates, then run. You’ll get XIRR, portfolio value over time, and the cashflows behind the number.` |
| `empty.steps` | `1 Basket · 2 Monthly amount & dates · 3 Run backtest` |
| `empty.cta` | `Configure & run →` |
| `empty.action_hint` | `Results appear here after you run.` |
| `cta.run` | `Run backtest` |
| `cta.running` | `Running…` |
| `cta.export` | `Export` |
| `cta.export_disabled` | `Run a backtest to export.` |
| `cta.export_json` | `Download full results (JSON)` |
| `cta.export_csv` | `Download cashflow list (CSV)` |
| `error.config` | `Invalid SIP config: {detail}` |
| `error.prices` | `Not enough price history for {symbols}. Sync Upstox or shorten the date range.` |
| `error.engine` | `Backtest failed. Retry or check API logs.` |
| `error.network` | `Can’t reach the API at {base}. Is the server running?` |
| `error.timeout` | `Backtest timed out. Try a shorter range or fewer symbols.` |
| `stale.banner` | `Parameters changed — re-run to update results.` |

### How to read

| Key | Copy |
|-----|------|
| `howto.title` | `How to read these results` |
| `howto.xirr` | `Start with XIRR. It answers: “If I had SIP’d this amount every month, what annualized return would I have earned?”` |
| `howto.invested_final` | `Total invested is cash contributed. Final value is what the holdings are worth at the end. The gap is absolute gain or loss — not annualized.` |
| `howto.chart` | `The portfolio value line is market value of units over time. The dashed line (if shown) is cumulative cash invested.` |
| `howto.cashflows` | `The cashflow table is what XIRR uses: each monthly SIP is cash you paid in (shown as −); the last row is ending portfolio value (shown as +).` |
| `howto.drawdown` | `Max drawdown is the worst peak-to-trough drop in portfolio market value — path risk, not XIRR.` |
| `howto.not_v0` | `This is not the same as the Dashboard’s index-style return. Don’t mix the two numbers.` |

### Form labels & helpers

| Key | Copy |
|-----|------|
| `config.strategy_title` | `Basket` |
| `config.strategy_label` | `SIP basket` |
| `config.sip_title` | `SIP parameters` |
| `config.amount_label` | `Monthly amount` |
| `config.amount_error` | `Enter a monthly amount greater than ₹0.` |
| `config.day_label` | `SIP day (calendar)` |
| `config.day_helper` | `If that day is not a trading session, we invest on the next session with prices.` |
| `config.day_error` | `Use a day from 1 to 28 so every month has that date.` |
| `config.run_disabled` | `Fix the fields above to run.` |
| `config.start_label` | `Start date` |
| `config.end_label` | `End date` |
| `config.end_latest` | `To latest available price` |
| `config.allocation_custom` | `Custom weights` |
| `config.allocation_equal` | `Equal weight` |
| `config.weights_sum_warning` | `Weights sum to {pct}% — must be 100% to run.` |
| `config.equities_only` | `Equities & ETFs only in this version.` |
| `config.no_baskets` | `No baskets available` |
| `config.no_baskets_help` | `Start the API and ensure strategy configs are loaded.` |

### Cashflows & holdings

| Key | Copy |
|-----|------|
| `cashflows.subtitle` | `Each monthly SIP is cash you paid in (shown as −). The last row is the ending portfolio value (shown as +). XIRR uses both.` |
| `cashflows.legend` | `− cash in · + ending value` |
| `cashflows.kind.contribution` | `Contribution` |
| `cashflows.kind.terminal` | `Ending value` |
| `cashflows.role.contribution` | `Cash out of pocket` |
| `cashflows.role.terminal` | `What the basket is worth` |
| `holdings.subtitle` | `How each name contributed cash and ending value.` |
| `holdings.weight` | `End weight` |
| `holdings.mv` | `Value (end)` |
| `holdings.cash_in` | `Cash put in` |

### KPI microcopy

| Key | Copy |
|-----|------|
| `kpi.invested.sublabel` | `Cash you put in` |
| `kpi.final.sublabel` | `What basket is worth` |
| `kpi.gain.sublabel` | `Final − invested` |
| `kpi.drawdown.sublabel` | `Worst drop from a peak — path risk, not XIRR` |
| `kpi.sip_count.label` | `SIP count` |
| `kpi.sip_count.sublabel` | `Number of monthly SIPs in this run` |

### Methodology accordion

| Key | Title | Body |
|-----|-------|------|
| `zero_costs` | `Zero costs` | `This version assumes zero brokerage, STT, stamp duty, slippage, and expense drag. Each SIP buys at the session close (or documented price field) for the full monthly amount.` |
| `sip_day` | `SIP day rule` | `Contributions use a fixed calendar day of the month. If markets are closed that day, the SIP invests on the next trading day with available prices.` |
| `xirr_primary` | `XIRR is primary` | `Headline performance is XIRR on cashflows (contributions + ending portfolio value). Path metrics (drawdown, market-value curve) support the story but do not replace XIRR.` |
| `not_v0` | `Not the same as the Dashboard return` | `This is not the same as the Dashboard’s index-style return. Don’t mix the two numbers.` |
| `sample` | `Demo prices` | `Sample or synthetic prices are for demos only — not live market SIP performance. Configure Upstox and sync for real history.` |
| `upstox_only` | `Upstox only for real history` | `Equity/ETF history for real runs comes only from Upstox. Sample/demo prices are labeled separately.` |

Accordion chrome title: **`How SIP Lab works`**.

---

## 3. Glossary for non-experts

Short definitions suitable for tooltips, methodology, or a small “Terms” list. Keep under ~40 words each.

### Core product terms

| Term | Plain definition |
|------|------------------|
| **SIP** | Systematic Investment Plan: investing a fixed amount on a schedule (here, monthly) instead of one lump sum. |
| **SIP Lab** | This tool’s name for running a **historical simulation** of monthly SIPs into a custom basket and reporting **XIRR**. |
| **Basket** | A set of stocks and/or ETFs with target weights (or equal weights). Same idea as a thematic portfolio / smallcase-style list. |
| **Backtest** | A “what if” run on past prices. Not a forecast and not a live portfolio. |
| **Contribution** | One monthly cash amount the SIP puts into the basket on a given date. |
| **Units** | How many shares (or fractions of shares, if the engine allows) you hold after each purchase. |
| **Market value (portfolio value)** | What your units are worth on a day: units × prices. Moves with the market even when you don’t add cash. |
| **Total invested** | Cash you put in: sum of all SIP contributions. Not the same as market value. |
| **Final value** | Market value of holdings on the end date of the backtest. |
| **Absolute gain** | Final value − total invested. Rupees made or lost before annualizing. |
| **Terminal value** | The ending portfolio value treated as a final “inflow” when calculating XIRR (as if you cashed out on the end date). |
| **Cashflow** | A dated money movement used by XIRR: usually each SIP (money out of your pocket) and the terminal value (money “back” at the end). |
| **Allocation / weights** | How each SIP amount is split across names (e.g. 25% each of four stocks). Equal weight means each name gets the same share. |
| **Rebalance (v0 / Dashboard)** | Adjusting weights over time for an index-style **NAV**. Different engine from monthly cash SIP — do not mix the stories. |
| **NAV (Dashboard)** | Net asset value path of a weight-based portfolio demo. Useful for composition performance; **not** SIP XIRR. |

### Primary metric

| Term | Plain definition |
|------|------------------|
| **XIRR** | Extended Internal Rate of Return. One annualized % that fits **multiple** cash amounts on **different dates** (your SIPs) plus the ending value. Better for SIPs than a simple start-to-end return. |
| **Annualized** | Expressed as a yearly rate, even if the backtest spans several years or only part of a year. |
| **Simple / total return** | (End − start) / start for a single pot of money. Misleading for SIPs because money enters over time. SIP Lab leads with XIRR instead. |
| **CAGR** | Compound annual growth rate for a path that assumes one starting value. May appear as a secondary path metric; **XIRR remains primary** for SIP success. |

### Risk & path

| Term | Plain definition |
|------|------------------|
| **Drawdown** | How far portfolio value has fallen from its previous peak. Always a “down” story. |
| **Max drawdown** | The worst peak-to-trough drop during the backtest. Path risk, not the same number as XIRR. |
| **Volatility** | How bumpy returns are over time. Secondary if shown; not the SIP headline. |

### Schedule & markets

| Term | Plain definition |
|------|------------------|
| **SIP day (calendar)** | The day of the month you choose for the SIP (e.g. the 1st). |
| **Trading day / session** | A day the market is open and we have a price. Weekends and holidays are not trading days. |
| **Next trading day rule** | If your SIP day falls on a closed market day, this lab invests on the **next** session that has prices. |
| **As-of date** | The latest date of prices used in curated data — “numbers are current as of …”. |

### Data sources (trust)

| Term | Plain definition |
|------|------------------|
| **Upstox** | The **only** broker API used for real equity/ETF price history in this product. |
| **Cached / curated prices** | History downloaded and stored locally (Parquet) so runs are reproducible. |
| **Demo / sample prices** | Fake or sample series for trying the UI. **Labeled Demo** — not real market SIP performance. |
| **Data source chip** | The small badge that says whether this run used Upstox or demo prices. Always read it before trusting XIRR. |

### Costs & scope

| Term | Plain definition |
|------|------------------|
| **Zero costs (MVP)** | Simulation ignores brokerage, taxes (e.g. STT), stamp duty, and slippage. Real investing costs money; this version does not model that yet. |
| **Equity / ETF only** | Stocks and exchange-traded funds. Mutual funds (Coin) are out of scope for now. |
| **Not live trading** | Running a backtest does not buy or sell anything in a broker account. |

### Indian market formatting (display)

| Topic | Guidance |
|-------|----------|
| Currency | INR with `₹`; prefer `en-IN` grouping (`₹12,00,000`) |
| Percents | Signed on performance: `+14.82%`, `−18.40%` |
| Missing | Em dash `—`, never fake `0%` |
| Dates | ISO in forms (`YYYY-MM-DD`); human labels ok in subtitles (`Jan 2021`) |

---

## 4. Micro-copy patterns

### Do

- Lead with the **question** the number answers (“what annualized return on my SIPs?”).
- Pair **invested** and **final value** whenever XIRR is shown.
- Say **Demo** or **sample** whenever prices are not Upstox.
- Use **Run backtest** — never “Invest”, “Buy”, or “Start SIP”.
- Prefer “basket” or “stocks/ETFs” over unexplained “smallcase” for first-time external visitors; “smallcase” is fine as a seed source label for users who already know the Dashboard.

### Don’t

- Imply past XIRR predicts future returns.
- Call sample runs “live”, “real”, or “market performance” without the demo warning.
- Equate Dashboard NAV total return with SIP XIRR.
- Use green/red for “success” of a system action; reserve P&L colors for returns/gain/drawdown.
- Mention yfinance, bhavcopy, or other vendors as price sources.

### Reading order we teach

1. Data source chip (demo vs Upstox)  
2. XIRR  
3. Total invested vs final value  
4. Portfolio value chart  
5. Cashflows (trust the math)  
6. Drawdown / risk  
7. Methodology details  

---

## 5. FAQ-style blurbs (optional UI)

Short answers if the frontend adds an FAQ fold later.

**What is XIRR in one sentence?**  
`The annualized return that fits all your monthly SIP amounts and the ending portfolio value.`

**Why isn’t total invested the same as final value?**  
`Invested is cash you contributed. Final value is what those holdings are worth after market moves.`

**What happens if my SIP day is a holiday?**  
`We invest on the next trading day that has prices.`

**Are costs included?**  
`Not in this version — brokerage and taxes are assumed zero.`

**Can I trust demo results?**  
`Only for learning the tool. Real claims need Upstox-synced history.`

**Is this the same as the Dashboard chart?**  
`No. Dashboard is a weight-based NAV demo. SIP Lab is monthly cash SIPs with XIRR.`

---

## 6. Voice checklist for new copy

- [ ] Could a non-expert understand without googling?  
- [ ] Is XIRR defined or linked when first used on a surface?  
- [ ] Are demo vs Upstox states impossible to miss?  
- [ ] Does any string imply live trading or guaranteed returns? (reject)  
- [ ] Does any string treat NAV total return as SIP performance? (reject)  
- [ ] Numbers: sign + `tabular-nums` + consistent decimals (implementation, not prose)

---

## 7. References

- Page layout & components: [pages/sip-lab.md](../pages/sip-lab.md)  
- PRD: [prd-sip-lab.md](../../product/prd-sip-lab.md)  
- ADR 004 (SIP rules, XIRR, costs): [004-sip-lab-prd-decisions.md](../../decisions/004-sip-lab-prd-decisions.md)  
- ADR 005 (Upstox sole source): [005-upstox-sole-market-data.md](../../decisions/005-upstox-sole-market-data.md)  
- Design tokens: [design-system.md](../design-system.md)  
