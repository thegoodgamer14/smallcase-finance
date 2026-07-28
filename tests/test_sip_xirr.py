"""Golden tests for SIP schedule, simulation, and XIRR (tolerance abs ≤ 1e-4).

All prices here are **synthetic / fixture** (source=fixture) — not real claims.
Day-count for XIRR: ACT/365.25 (calc.xirr.DAYS_PER_YEAR).
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from smallcase_finance.calc.sip_schedule import next_trading_day, sip_schedule
from smallcase_finance.calc.sip_sim import allocate_sip_buy, run_sip_simulation
from smallcase_finance.calc.xirr import DAYS_PER_YEAR, Cashflow, npv, xirr, year_fraction

XIRR_TOL = 1e-4
CASH_TOL = 1e-6
UNITS_RTOL = 1e-10


# ---------------------------------------------------------------------------
# Helpers — synthetic calendars / prices (fixture)
# ---------------------------------------------------------------------------


def _weekdays(start: date, end: date) -> list[date]:
    """Mon–Fri sessions (synthetic calendar; no holiday holes unless removed)."""
    out: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _reference_xirr_newton(
    cashflows: list[tuple[date, float]],
    *,
    guess: float = 0.1,
    tol: float = 1e-14,
    max_iter: int = 200,
) -> float:
    """Independent Newton reference (ACT/365.25) for golden asserts.

    Separate implementation from production solver so tests do not tautologically
    compare the function to itself.
    """
    cfs = sorted(cashflows, key=lambda x: x[0])
    d0 = cfs[0][0]

    def f_df(r: float) -> tuple[float, float]:
        if r <= -1.0 + 1e-15:
            r = -1.0 + 1e-15
        f = 0.0
        df = 0.0
        for d, amt in cfs:
            y = (d - d0).days / DAYS_PER_YEAR
            if y == 0.0:
                f += amt
                continue
            base = 1.0 + r
            f += amt * base ** (-y)
            df += amt * (-y) * base ** (-y - 1.0)
        return f, df

    r = guess
    for _ in range(max_iter):
        f, df = f_df(r)
        if abs(f) < tol:
            return r
        if abs(df) < 1e-18:
            break
        r = r - f / df
        if r <= -0.999999:
            r = -0.999999
    f, _ = f_df(r)
    if abs(f) > 1e-6:
        raise RuntimeError(f"reference XIRR did not converge; residual={f}")
    return r


# ---------------------------------------------------------------------------
# S1–S4: SIP schedule
# ---------------------------------------------------------------------------


def test_s1_candidate_weekday_is_session():
    """S1: candidate weekday that is a session → invest on candidate."""
    sessions = _weekdays(date(2024, 1, 1), date(2024, 3, 31))
    # 2024-01-15 is Monday
    assert date(2024, 1, 15).weekday() == 0
    sched = sip_schedule(15, date(2024, 1, 1), date(2024, 3, 31), sessions)
    assert date(2024, 1, 15) in sched
    assert sched[0] == date(2024, 1, 15)


def test_s2_candidate_saturday_rolls_to_monday():
    """S2: candidate Saturday → next Monday (if in sessions)."""
    sessions = _weekdays(date(2024, 6, 1), date(2024, 6, 30))
    # 2024-06-15 is Saturday
    assert date(2024, 6, 15).weekday() == 5
    monday = date(2024, 6, 17)
    assert monday in sessions
    sched = sip_schedule(15, date(2024, 6, 1), date(2024, 6, 30), sessions)
    assert sched == [monday]


def test_s3_holiday_hole_rolls_forward():
    """S3: candidate on missing session (holiday hole) → next session with bars."""
    sessions = _weekdays(date(2024, 1, 1), date(2024, 1, 31))
    # 2024-01-15 is Monday — remove it as a "holiday"
    holiday = date(2024, 1, 15)
    sessions = [d for d in sessions if d != holiday]
    sched = sip_schedule(15, date(2024, 1, 1), date(2024, 1, 31), sessions)
    assert sched == [date(2024, 1, 16)]  # Tuesday


def test_s4_no_session_after_candidate_skips_month():
    """S4: no session ≥ candidate → month skipped."""
    # Only sessions in early January; day_of_month=28 has nothing after in range
    sessions = [date(2024, 1, 2), date(2024, 1, 3)]
    sched = sip_schedule(28, date(2024, 1, 1), date(2024, 1, 31), sessions)
    assert sched == []


def test_next_trading_day_helper():
    sessions = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 5)]
    assert next_trading_day(date(2024, 1, 3), sessions) == date(2024, 1, 3)
    assert next_trading_day(date(2024, 1, 4), sessions) == date(2024, 1, 5)
    assert next_trading_day(date(2024, 1, 6), sessions) is None


def test_schedule_respects_start_and_end():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 6, 30))
    sched = sip_schedule(15, date(2024, 2, 1), date(2024, 4, 30), sessions)
    assert all(date(2024, 2, 1) <= d <= date(2024, 4, 30) for d in sched)
    assert sched[0] >= date(2024, 2, 1)
    # Feb 15 2024 is Thursday
    assert date(2024, 2, 15) in sched


def test_schedule_empty_sessions():
    assert sip_schedule(5, date(2024, 1, 1), date(2024, 12, 31), []) == []


def test_schedule_day_of_month_bounds():
    sessions = _weekdays(date(2024, 1, 1), date(2024, 1, 31))
    with pytest.raises(ValueError):
        sip_schedule(29, date(2024, 1, 1), date(2024, 1, 31), sessions)
    with pytest.raises(ValueError):
        sip_schedule(0, date(2024, 1, 1), date(2024, 1, 31), sessions)


# ---------------------------------------------------------------------------
# L1–L3: ledger / simulation
# ---------------------------------------------------------------------------


def test_l1_single_sip_one_asset_hold():
    """L1: single SIP, one asset, hold → units = A/P; terminal MV = units×P_T."""
    # source=fixture synthetic
    prices = {
        "AAA": {
            date(2024, 1, 15): 100.0,
            date(2024, 1, 16): 101.0,
            date(2024, 1, 17): 105.0,
        }
    }
    result = run_sip_simulation(
        weights={"AAA": 1.0},
        prices=prices,
        amount=1000.0,
        schedule=[date(2024, 1, 15)],
        as_of=date(2024, 1, 17),
        trading_dates=sorted(prices["AAA"].keys()),
    )
    assert result.n_sips == 1
    assert abs(result.units_end["AAA"] - 10.0) <= UNITS_RTOL * 10
    assert abs(result.final_value - 1050.0) < CASH_TOL
    assert abs(result.total_invested - 1000.0) < CASH_TOL
    assert result.cashflows[0].amount == -1000.0
    assert result.cashflows[0].kind == "contribution"
    assert result.cashflows[-1].kind == "terminal"
    assert abs(result.cashflows[-1].amount - 1050.0) < CASH_TOL


def test_l2_multi_asset_weights_full_deploy():
    """L2: multi-asset weights sum 1 → cash allocated matches A; residual &lt; 1e-6×A."""
    d = date(2024, 3, 15)
    prices = {
        "A": {d: 50.0},
        "B": {d: 200.0},
    }
    amount = 1000.0
    units, cash, w_use, gap = allocate_sip_buy(
        amount, {"A": 0.4, "B": 0.6}, {"A": 50.0, "B": 200.0}
    )
    assert gap == []
    assert abs(sum(cash.values()) - amount) < 1e-6 * amount
    assert abs(units["A"] - (400.0 / 50.0)) < UNITS_RTOL * units["A"]
    assert abs(units["B"] - (600.0 / 200.0)) < UNITS_RTOL * units["B"]
    assert abs(sum(w_use.values()) - 1.0) < 1e-12

    result = run_sip_simulation(
        weights={"A": 0.4, "B": 0.6},
        prices=prices,
        amount=amount,
        schedule=[d],
        as_of=d,
        trading_dates=[d],
    )
    assert abs(result.final_value - amount) < CASH_TOL  # flat mark same day
    assert abs(result.total_invested - amount) < CASH_TOL


def test_l3_missing_price_renormalize():
    """L3: missing price on one symbol on SIP day → renormalize others + warning."""
    d = date(2024, 4, 15)
    prices = {
        "A": {d: 100.0},
        "B": {},  # missing entirely on invest day
    }
    result = run_sip_simulation(
        weights={"A": 0.5, "B": 0.5},
        prices=prices,
        amount=1000.0,
        schedule=[d],
        as_of=d,
        trading_dates=[d],
    )
    assert "B" not in result.units_end
    assert abs(result.units_end["A"] - 10.0) < UNITS_RTOL * 10
    assert any("gap_symbols" in w for w in result.warnings)


def test_architecture_micro_example_two_sips():
    """sip-engine.md §14 micro-example (AAA, two SIPs)."""
    prices = {
        "AAA": {
            date(2024, 1, 15): 100.0,
            date(2024, 2, 15): 110.0,
        }
    }
    result = run_sip_simulation(
        weights={"AAA": 1.0},
        prices=prices,
        amount=1000.0,
        schedule=[date(2024, 1, 15), date(2024, 2, 15)],
        as_of=date(2024, 2, 15),
        trading_dates=[date(2024, 1, 15), date(2024, 2, 15)],
    )
    expected_units = 1000.0 / 100.0 + 1000.0 / 110.0
    assert abs(result.units_end["AAA"] - expected_units) < UNITS_RTOL * expected_units
    expected_mv = expected_units * 110.0
    assert abs(result.final_value - expected_mv) < CASH_TOL
    assert abs(result.final_value - 2100.0) < CASH_TOL
    assert result.n_sips == 2
    assert len(result.cashflows) == 3  # 2 contrib + terminal


# ---------------------------------------------------------------------------
# X1–X3: XIRR solver
# ---------------------------------------------------------------------------


def test_x3_two_cashflows_closed_form():
    """X3: two cashflows only — closed-form check.

    CF0 = -100 at t0, CF1 = +110 one year later (365 days ≈ 365/365.25 years)
    (1+r)^y = 110/100 → r = (1.1)^(1/y) - 1
    """
    d0 = date(2020, 1, 1)
    d1 = date(2021, 1, 1)  # 366 days in 2020 leap year
    days = (d1 - d0).days
    y = days / DAYS_PER_YEAR
    expected = (1.1) ** (1.0 / y) - 1.0
    cfs = [Cashflow(d0, -100.0), Cashflow(d1, 110.0)]
    rate = xirr(cfs)
    assert rate is not None
    assert abs(rate - expected) <= XIRR_TOL
    # residual NPV ~ 0
    assert abs(npv(rate, cfs)) < 1e-6


def test_x1_hand_computed_reference():
    """X1: multi-CF series vs independent Newton reference (abs ≤ 1e-4)."""
    cfs = [
        (date(2023, 1, 15), -5000.0),
        (date(2023, 2, 15), -5000.0),
        (date(2023, 3, 15), -5000.0),
        (date(2023, 4, 15), -5000.0),
        (date(2023, 6, 15), 22000.0),
    ]
    ref = _reference_xirr_newton(cfs)
    rate = xirr([Cashflow(d, a) for d, a in cfs])
    assert rate is not None
    assert abs(rate - ref) <= XIRR_TOL


def test_x2_known_constant_growth_synthetic():
    """X2: known constant growth synthetic SIP → XIRR matches reference ≤ 1e-4.

    Monthly SIP of 1000 into an asset that grows so that terminal MV is
    constructed from explicit cashflows; compare engine XIRR to reference.
    """
    # Build explicit cashflows with a known rate ≈ 12% ACT/365.25
    # Working backwards is hard; instead use forward cashflows and ref solver.
    d0 = date(2022, 1, 10)
    cfs: list[tuple[date, float]] = []
    for i in range(12):
        # approx monthly: add 30 days each (fixture, not calendar SIP)
        d = d0 + timedelta(days=30 * i)
        cfs.append((d, -1000.0))
    # Terminal one year after first: grow total so XIRR is near 12%
    # Use reference to solve after setting terminal via a known r
    target_r = 0.12
    # Find terminal T such that NPV(target_r)=0
    # NPV = sum -1000/(1+r)^y_i + T/(1+r)^y_T = 0
    t_end = d0 + timedelta(days=365)
    pv_contrib = 0.0
    for d, amt in cfs:
        y = (d - d0).days / DAYS_PER_YEAR
        pv_contrib += amt / ((1.0 + target_r) ** y)
    y_t = (t_end - d0).days / DAYS_PER_YEAR
    # pv_contrib + T / (1+r)^y_t = 0 → T = -pv_contrib * (1+r)^y_t
    terminal = -pv_contrib * ((1.0 + target_r) ** y_t)
    cfs.append((t_end, terminal))

    rate = xirr([Cashflow(d, a) for d, a in cfs])
    assert rate is not None
    assert abs(rate - target_r) <= XIRR_TOL


def test_xirr_edge_fewer_than_two():
    assert xirr([Cashflow(date(2024, 1, 1), -100.0)]) is None
    assert xirr([]) is None


def test_xirr_edge_same_sign():
    cfs = [
        Cashflow(date(2024, 1, 1), -100.0),
        Cashflow(date(2024, 6, 1), -50.0),
    ]
    assert xirr(cfs) is None


def test_year_fraction_act_365_25():
    d0 = date(2024, 1, 1)
    d1 = date(2024, 1, 1) + timedelta(days=365)
    assert abs(year_fraction(d0, d1) - 365 / 365.25) < 1e-15


# ---------------------------------------------------------------------------
# E1: end-to-end engine (schedule + sim + xirr)
# ---------------------------------------------------------------------------


def test_e1_full_engine_12_sips_two_assets():
    """E1: 12 SIPs, 2 symbols, fixture prices → XIRR + n_sips + final_value."""
    # source=fixture: deterministic synthetic prices
    sessions = _weekdays(date(2023, 1, 1), date(2023, 12, 31))
    # Mild upward drift with different slopes
    prices: dict[str, dict[date, float]] = {"AAA": {}, "BBB": {}}
    for i, d in enumerate(sessions):
        prices["AAA"][d] = 100.0 * (1.0 + 0.0005) ** i
        prices["BBB"][d] = 200.0 * (1.0 + 0.0003) ** i

    sched = sip_schedule(15, date(2023, 1, 1), date(2023, 12, 31), sessions)
    assert len(sched) == 12

    result = run_sip_simulation(
        weights={"AAA": 0.5, "BBB": 0.5},
        prices=prices,
        amount=5000.0,
        schedule=sched,
        as_of=date(2023, 12, 29),  # last weekday of 2023 is Fri Dec 29
        trading_dates=sessions,
    )

    assert result.n_sips == 12
    assert abs(result.total_invested - 12 * 5000.0) < CASH_TOL
    assert result.final_value > 0
    assert result.xirr is not None

    # Independent reference on the same cashflows
    pairs = [(cf.date, cf.amount) for cf in result.cashflows]
    ref = _reference_xirr_newton(pairs)
    assert abs(result.xirr - ref) <= XIRR_TOL

    # Residual NPV at engine rate
    assert abs(npv(result.xirr, result.cashflows)) < 1e-4

    # Max drawdown is negative or zero
    assert result.max_drawdown <= 0.0
    assert result.absolute_gain == pytest.approx(
        result.final_value - result.total_invested, abs=CASH_TOL
    )


def test_e1_flat_prices_near_zero_xirr():
    """Flat prices → XIRR ≈ 0 (money in = money out, no time growth)."""
    sessions = _weekdays(date(2024, 1, 1), date(2024, 6, 30))
    prices = {"X": {d: 50.0 for d in sessions}}
    sched = sip_schedule(10, date(2024, 1, 1), date(2024, 6, 30), sessions)
    result = run_sip_simulation(
        weights={"X": 1.0},
        prices=prices,
        amount=1000.0,
        schedule=sched,
        trading_dates=sessions,
    )
    # Terminal MV equals total invested on flat prices
    assert abs(result.final_value - result.total_invested) < CASH_TOL
    assert result.xirr is not None
    assert abs(result.xirr) <= XIRR_TOL


def test_max_drawdown_on_mv_path():
    """Secondary max_drawdown on MV when prices dip mid-horizon."""
    sessions = [
        date(2024, 1, 15),
        date(2024, 1, 16),
        date(2024, 1, 17),
        date(2024, 2, 15),
    ]
    prices = {
        "AAA": {
            date(2024, 1, 15): 100.0,
            date(2024, 1, 16): 120.0,  # peak after first SIP
            date(2024, 1, 17): 90.0,  # trough
            date(2024, 2, 15): 100.0,
        }
    }
    result = run_sip_simulation(
        weights={"AAA": 1.0},
        prices=prices,
        amount=1000.0,
        schedule=[date(2024, 1, 15), date(2024, 2, 15)],
        trading_dates=sessions,
    )
    # After first SIP: 10 units; peak MV=1200, trough=900 → dd = 900/1200 - 1 = -0.25
    # Then second SIP adds more units — peak may update. At least mdd ≤ 0.
    assert result.max_drawdown <= 0.0
    assert result.max_drawdown <= -0.2  # saw at least ~25% dip on first lot path


def test_tuple_cashflows_accepted():
    d0 = date(2020, 1, 1)
    d1 = date(2021, 1, 1)
    rate = xirr([(d0, -100.0), (d1, 110.0)])
    assert rate is not None
    assert rate > 0
