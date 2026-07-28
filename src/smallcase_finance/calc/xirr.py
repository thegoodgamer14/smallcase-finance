"""XIRR (extended internal rate of return) — pure solver.

Day-count: ACT/365.25 (sip-engine.md §9.2 / docs/analytics/sip-xirr.md).
Cashflows: contribution outflows negative, terminal inflow positive.

Golden fixture gate: absolute error ≤ 1e-4 vs reference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence, Union

DAYS_PER_YEAR = 365.25
XIRR_TOL = 1e-7
XIRR_MAX_ITER = 100


@dataclass(frozen=True, slots=True)
class Cashflow:
    """One dated cashflow leg for XIRR.

    Sign convention: contribution ``amount < 0``, terminal ``amount > 0``.
    """

    date: date
    amount: float
    kind: str = "contribution"  # contribution | terminal | redemption


CashflowLike = Union[Cashflow, tuple[date, float]]


def _normalize_cashflows(
    cashflows: Sequence[CashflowLike],
) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for cf in cashflows:
        if isinstance(cf, Cashflow):
            out.append((cf.date, float(cf.amount)))
        else:
            d, amt = cf
            out.append((d, float(amt)))
    return out


def year_fraction(d0: date, d: date, *, days_per_year: float = DAYS_PER_YEAR) -> float:
    """Year fraction from ``d0`` to ``d`` using ACT/days_per_year."""
    return (d - d0).days / float(days_per_year)


def npv(
    rate: float,
    cashflows: Sequence[CashflowLike],
    *,
    days_per_year: float = DAYS_PER_YEAR,
) -> float:
    """Net present value of dated cashflows at annual rate ``rate``."""
    cfs = _normalize_cashflows(cashflows)
    if not cfs:
        return 0.0
    cfs = sorted(cfs, key=lambda x: x[0])
    d0 = cfs[0][0]
    total = 0.0
    for d, amt in cfs:
        y = year_fraction(d0, d, days_per_year=days_per_year)
        total += float(amt) / ((1.0 + rate) ** y)
    return total


def xirr(
    cashflows: Sequence[CashflowLike],
    *,
    guess: float = 0.1,
    days_per_year: float = DAYS_PER_YEAR,
    tol: float = XIRR_TOL,
    max_iter: int = XIRR_MAX_ITER,
) -> Optional[float]:
    """Solve for annualized rate r where NPV(cashflows, r) = 0.

    Accepts ``Cashflow`` objects or ``(date, amount)`` tuples.

    Returns
    -------
    float | None
        Annualized rate as a decimal (0.12 = 12%), or None if undefined /
        non-convergent (fewer than 2 flows, all same sign, no real root).
    """
    cfs = _normalize_cashflows(cashflows)
    if len(cfs) < 2:
        return None
    cfs.sort(key=lambda x: x[0])
    amounts = [a for _, a in cfs]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    # Newton with analytic derivative; fall back to bisection bracket
    rate = float(guess)
    for _ in range(max_iter):
        d0 = cfs[0][0]
        f = 0.0
        df = 0.0
        for d, amt in cfs:
            y = year_fraction(d0, d, days_per_year=days_per_year)
            if y == 0.0:
                f += amt
                continue
            base = 1.0 + rate
            if base <= 0.0:
                break
            disc = base**y
            f += amt / disc
            df -= y * amt / (disc * base)
        if abs(f) < tol:
            return rate
        if df == 0.0 or not math.isfinite(df) or not math.isfinite(f):
            break
        step = f / df
        rate_next = rate - step
        if not math.isfinite(rate_next) or rate_next <= -0.999999:
            break
        if abs(rate_next - rate) < tol:
            return rate_next
        rate = rate_next
    else:
        if math.isfinite(rate):
            return rate

    # Bisection fallback over a wide bracket
    lo, hi = -0.9999, 10.0
    flo = npv(lo, cfs, days_per_year=days_per_year)
    fhi = npv(hi, cfs, days_per_year=days_per_year)
    if not (math.isfinite(flo) and math.isfinite(fhi)):
        return None
    if flo * fhi > 0:
        found = False
        grid = [
            -0.99, -0.5, -0.2, 0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 20.0, 50.0
        ]
        prev_r: Optional[float] = None
        prev_f: Optional[float] = None
        for r in grid:
            fr = npv(r, cfs, days_per_year=days_per_year)
            if prev_f is not None and prev_r is not None and math.isfinite(fr) and prev_f * fr <= 0:
                lo, hi = prev_r, r
                flo, fhi = prev_f, fr
                found = True
                break
            prev_r, prev_f = r, fr
        if not found:
            return None

    for _ in range(max_iter * 2):
        mid = 0.5 * (lo + hi)
        fm = npv(mid, cfs, days_per_year=days_per_year)
        if not math.isfinite(fm):
            return None
        if abs(fm) < tol or abs(hi - lo) < tol:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)
