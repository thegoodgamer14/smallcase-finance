# Metrics Definitions — Smallcase Finance v0

**Owner:** Data Analyst  
**Code:** `src/smallcase_finance/calc/` (pure; no I/O)  
**Schema:** [data-dictionary.md](../data-dictionary.md) (`nav_series`, `metrics_snapshot`, `contribution`)

All ratios are **decimal fractions** (`0.14` = 14%), never percent points.

---

## Shared assumptions

| Parameter | Default | Notes |
|-----------|---------|-------|
| Trading days / year | **252** | `PERIODS_PER_YEAR` in `calc.risk` and `config` |
| Risk-free rate (Sharpe / Sortino) | **0.0** annual | Override with `rf_rate=0.06` for a rough India-like cash yield |
| Price field for NAV | `close` | Pipeline may switch to `adj_close` via config |
| Max drawdown sign | **Negative** | Worst peak-to-trough as `trough/peak - 1` |
| First-day return | **0.0** | NAV series seeds on day 0; no prior close |
| Gap policy | Exclude + renormalize | Symbol missing a return that day is dropped; remaining weights scale to 1 |

Currency: INR-friendly; no FX conversion in v0.

---

## NAV construction

### Daily asset return

\[
r_{i,t} = \frac{P_{i,t}}{P_{i,t-1}} - 1
\]

### Portfolio daily return (static or scheduled weights)

\[
R_t = \sum_i w_{i,t}\, r_{i,t}
\]

If some constituents lack a valid return on day \(t\) and gap policy is on:

\[
R_t = \frac{\sum_{i \in U_t} w_{i,t}\, r_{i,t}}{\sum_{i \in U_t} w_{i,t}}
\]

where \(U_t\) is the set of usable symbols that day.

### NAV path

- Day 0 (first usable date): \(\mathrm{NAV}_0 = \mathrm{base\_nav}\) (default 100), \(R_0 = 0\).
- Later days: \(\mathrm{NAV}_t = \mathrm{NAV}_{t-1}\,(1 + R_t)\).
- Cumulative return: \(\mathrm{cum\_return}_t = \mathrm{NAV}_t / \mathrm{base\_nav} - 1\).

**Code:** `nav_from_returns`, `build_nav_from_prices` in `calc/nav.py`.

Weights for date \(d\) come from versioned constituents: max `effective_from ≤ d` among rows still active (`effective_to` null or `≥ d`). Helper: `active_weights_on`.

---

## Performance metrics

### Total return

\[
\text{total\_return} = \frac{\mathrm{NAV}_T}{\mathrm{NAV}_0} - 1
\]

### CAGR (annualized return)

\[
\text{CAGR} = \left(\frac{\mathrm{NAV}_T}{\mathrm{NAV}_0}\right)^{1/y} - 1,\quad
y = \frac{n_{\mathrm{obs}}}{252}
\]

- \(n_{\mathrm{obs}}\) = number of daily return observations in the window (length of the NAV slice).
- Returns **null** if \(y < 1/12\) (shorter than ~1 month) or NAV invalid.
- **Limitation:** using observation count (not calendar days) is standard for trading-day series but can differ slightly from ACT/365.

### Volatility (annualized)

Sample standard deviation of daily returns (ddof=1), annualized:

\[
\sigma_{\mathrm{ann}} = \sqrt{\frac{1}{n-1}\sum_t (R_t - \bar R)^2}\;\times\;\sqrt{252}
\]

Null if \(n < 2\).

### Max drawdown

Running peak on NAV; drawdown \(d_t = \mathrm{NAV}_t / \mathrm{peak}_t - 1\); report \(\min_t d_t\) (**≤ 0**).

### Sharpe

\[
\text{Sharpe} = \frac{\mathrm{CAGR} - r_f}{\sigma_{\mathrm{ann}}}
\]

- \(r_f\): **annual** risk-free rate (default `0.0`; document any non-zero choice in `metrics_snapshot.rf_rate`).
- Null if CAGR or vol undefined, or vol ≤ 0.
- **Not** the per-period excess-return Sharpe; we use CAGR in the numerator for a single comparable annual number.

### Sortino (optional)

Same as Sharpe but denominator is annualized **downside deviation** of daily returns below 0 (MAR = 0).

### Calmar (optional)

\[
\text{Calmar} = \frac{\mathrm{CAGR}}{|\text{max\_drawdown}|}
\]

only when max drawdown is strictly negative.

**Code:** `calc/risk.py` → `summary_metrics` bundles the above.

---

## Contribution / attribution (simple)

For a period \([t_0, t_1]\):

| Field | Definition |
|-------|------------|
| `symbol_return` | \(P_{t_1}/P_{t_0} - 1\) |
| `avg_weight` | Average of start/end (or schedule-average) portfolio weight |
| `contribution` | \(\approx \texttt{avg\_weight} \times \texttt{symbol\_return}\) |

**Code:** `contribution_by_symbol` in `calc/returns.py`.

### Residual

\[
\text{residual} = R_{\mathrm{portfolio}} - \sum_i \text{contribution}_i
\]

Non-zero when weights change mid-period (rebalance / drift interaction). Reserved symbol `_RESIDUAL` may store this in curated tables later.

**Not** full multi-period Brinson–Fachler attribution in v0.

---

## Rebalance vs buy-and-hold backtest

**Code:** `backtest_rebalance_vs_buyhold` in `calc/rebalance.py`.

| Strategy | Rule |
|----------|------|
| Rebalanced | Open at target weights; each day weights drift with returns; every `rebalance_every` steps, reset to target (optional turnover `threshold`) |
| Buy-and-hold | Same open; weights drift forever; no reset |

Outputs: both return series, both NAV paths, rebalance indices, end weights, cumulative one-way turnover.

**v0 omissions:** transaction costs, taxes, cash drag, partial fills, corporate actions beyond adjusted prices.

One-way turnover of a trade:

\[
\text{turnover} = \tfrac12 \sum_i |w_i^{\mathrm{to}} - w_i^{\mathrm{from}}|
\]

---

## Window labels (`metrics_snapshot.window`)

| Label | Start rule |
|-------|------------|
| `1M` / `3M` / `6M` / `1Y` | `as_of - {30,91,182,365}` calendar days |
| `YTD` | Jan 1 of `as_of.year` |
| `ITD` | First NAV date |
| `custom` | Caller-supplied bounds |

Slice is inclusive on trading days present in `nav_series`.

---

## Import cheatsheet

```python
from smallcase_finance.calc import (
    nav_from_returns,
    cagr,
    volatility,
    max_drawdown,
    sharpe,
    summary_metrics,
    contribution_by_symbol,
    backtest_rebalance_vs_buyhold,
    normalize_weights,
)
```

Run unit tests: `make test` or `python3 -m pytest -q`.

Sample table over curated data: `python3 scripts/print_sample_metrics.py`.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-28 | Initial definitions aligned with data dictionary + `calc/` implementation |
