# SIP XIRR Methodology — SIP Lab

**Owner:** Data Analyst  
**Code:** `src/smallcase_finance/calc/sip_schedule.py`, `sip_sim.py`, `xirr.py`  
**Architecture:** [sip-engine.md](../architecture/sip-engine.md)  
**v0 weight-NAV (not SIP):** [metrics-definitions.md](metrics-definitions.md)

Primary success metric for SIP Lab is **XIRR on cashflows**, not CAGR on a unit-capital NAV index.

---

## 1. SIP schedule (fixed day → next session)

```text
sip_schedule(day_of_month, start, end, trading_dates) → list[date]
```

| Step | Rule |
|------|------|
| Candidate | For each month in range: `c = date(year, month, day_of_month)` |
| Session | `s = min { d ∈ trading_dates \| d ≥ c }` |
| Bounds | Keep only invest dates with `start ≤ s ≤ end` (when `end` set) |
| Dedupe | Same session from two candidates → one contribution |
| Missing | No session ≥ `c` → skip month |

- MVP `day_of_month` ∈ **[1, 28]** (config layer).
- Session calendar = price calendar (dates with bars), not an external holiday API.
- **Zero costs:** full SIP amount deploys at session **close**.

---

## 2. Simulation (cash → units → MV)

```text
run_sip_simulation(weights, prices, amount, schedule) → SipSimulationResult
```

On each invest date \(s\), contribution \(A\):

\[
w_i' = \frac{w_i}{\sum_{j \in U_s} w_j},\quad
\Delta q_i = \frac{A \cdot w_i'}{P_{i,s}}
\]

- Fractional units allowed; residual cash ≈ 0 (float dust only).
- Symbol missing price on invest day → **exclude + renormalize** (gap policy).
- Between SIPs, units constant (rebalance modes are optional / later).
- Market value: \(\mathrm{MV}_t = \sum_i q_{i,t} P_{i,t}\).

### Cashflow sign convention (binding)

| Event | Amount | Sign |
|-------|--------|------|
| Monthly SIP | `sip_amount` | **Negative** (outflow) |
| Terminal / exit | \(\mathrm{MV}_T\) | **Positive** (inflow) |

Multiple cashflows on the same date are kept as separate rows for audit; the solver accepts them.

---

## 3. XIRR (primary)

Day-count: **ACT/365.25**

\[
\sum_k \mathrm{CF}_k \, (1+r)^{-y_k} = 0,\quad
y_k = \frac{d_k - d_0}{365.25}
\]

where \(d_0\) is the first cashflow date.

| Item | Detail |
|------|--------|
| Code | `calc/xirr.py` — Newton, then Brent bracket |
| Failure | Returns `None` if &lt; 2 CFs, all same sign, or non-convergence |
| Golden gate | \(\lvert r_{\mathrm{engine}} - r_{\mathrm{ref}} \rvert \le 10^{-4}\) absolute |
| Not used for pass/fail | CAGR on MV path (misleading under staged capital) |

### Secondary metrics (never override XIRR)

| Metric | Definition |
|--------|------------|
| `total_invested` | \(\sum\) contribution amounts (positive) |
| `final_value` | \(\mathrm{MV}_T\) |
| `absolute_gain` | `final_value - total_invested` |
| `max_drawdown` | Peak-to-trough on \(\mathrm{MV}_t\) as **negative** fraction |

---

## 4. Worked micro-example (synthetic / fixture)

One asset `AAA`, `sip_amount=1000`, invest on 15th:

| date | close | event |
|------|------:|-------|
| 2024-01-15 | 100 | buy 10 units; CF −1000 |
| 2024-02-15 | 110 | buy ≈9.0909 units; CF −1000 |
| 2024-02-15 | — | terminal MV ≈ 2100; CF +2100 |

Units end ≈ 19.0909. XIRR solves NPV = 0 on the three cashflows (two contributions + terminal on the last SIP day).

---

## 5. Data source honesty

| Source | Label | May claim real performance? |
|--------|-------|-----------------------------|
| Upstox daily bars (curated) | `upstox` | Yes (with caveats) |
| Sample / synthetic fixtures | `sample` / `fixture` | **No** — demo only |

Do not use yfinance, bhavcopy, or Fyers for SIP Lab history.

---

## 6. Reproducibility

```python
from datetime import date
from smallcase_finance.calc import sip_schedule, run_sip_simulation, xirr

sessions = [...]  # sorted trading dates
sched = sip_schedule(15, date(2024, 1, 1), date(2024, 12, 31), sessions)
result = run_sip_simulation(
    weights={"AAA": 1.0},
    prices={"AAA": {d: px for d, px in ...}},
    amount=1000.0,
    schedule=sched,
)
assert result.xirr is not None
```

Golden tests: `tests/test_sip_xirr.py` (absolute XIRR error ≤ `1e-4`).
