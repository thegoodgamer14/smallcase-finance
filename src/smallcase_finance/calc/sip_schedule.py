"""SIP invest-date schedule: fixed calendar day → next trading session.

Pure functions only (no I/O). Binding rules: docs/architecture/sip-engine.md §6
and docs/analytics/sip-xirr.md.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence


def next_trading_day(
    candidate: date,
    sessions: Sequence[date],
) -> Optional[date]:
    """Smallest session date ``s`` with ``s >= candidate``.

    ``sessions`` should be sorted ascending unique dates.
    """
    if not sessions:
        return None
    lo, hi = 0, len(sessions)
    while lo < hi:
        mid = (lo + hi) // 2
        if sessions[mid] < candidate:
            lo = mid + 1
        else:
            hi = mid
    if lo >= len(sessions):
        return None
    return sessions[lo]


# Alias used by some call sites / docs
next_session_on_or_after = next_trading_day


def _add_month(year: int, month: int, delta: int = 1) -> tuple[int, int]:
    m = month + delta
    y = year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return y, m


def sip_schedule(
    day_of_month: int,
    start: date,
    end: Optional[date],
    trading_dates: Sequence[date],
) -> list[date]:
    """Map monthly calendar candidates to invest sessions.

    Parameters
    ----------
    day_of_month:
        Calendar day 1–28 (MVP). Raises ``ValueError`` outside range.
    start:
        First schedule bound (inclusive for invest dates).
    end:
        Last invest-date bound (inclusive). ``None`` → through last session.
    trading_dates:
        Session calendar (price dates); need not be sorted (will be sorted).

    Returns
    -------
    list[date]
        Deduplicated invest dates (one contribution per session).
    """
    if day_of_month < 1 or day_of_month > 28:
        raise ValueError(f"day_of_month must be in 1..28 (got {day_of_month})")

    if not trading_dates:
        return []

    ordered = sorted(set(trading_dates))
    horizon_end = end if end is not None else ordered[-1]

    y, m = start.year, start.month
    end_y, end_m = horizon_end.year, horizon_end.month

    invest: list[date] = []
    seen: set[date] = set()

    while (y, m) <= (end_y, end_m):
        candidate = date(y, m, day_of_month)
        s = next_trading_day(candidate, ordered)
        if s is None:
            pass  # skip month — no session after candidate
        elif s < start:
            pass
        elif end is not None and s > end:
            pass
        elif s in seen:
            pass  # collapse double mapping (sip-engine.md §6.3)
        else:
            seen.add(s)
            invest.append(s)
        y, m = _add_month(y, m, 1)

    return invest


def sip_invest_dates(
    day_of_month: int,
    start_date: date,
    end_date: Optional[date],
    sessions: Sequence[date],
) -> tuple[list[date], list[str]]:
    """Like ``sip_schedule`` but also returns skip warnings.

    Prefer ``sip_schedule`` for pure schedule tests; service layer may use this
    when it wants ``no_session_after_candidate`` diagnostics.
    """
    if day_of_month < 1 or day_of_month > 28:
        raise ValueError(f"day_of_month must be in 1..28 (got {day_of_month})")

    warnings: list[str] = []
    if not sessions:
        warnings.append("empty_sessions: no trading days in price calendar")
        return [], warnings

    ordered = sorted(set(sessions))
    horizon_end = end_date if end_date is not None else ordered[-1]
    y, m = start_date.year, start_date.month
    end_y, end_m = horizon_end.year, horizon_end.month

    invest: list[date] = []
    seen: set[date] = set()

    while (y, m) <= (end_y, end_m):
        candidate = date(y, m, day_of_month)
        s = next_trading_day(candidate, ordered)
        if s is None:
            warnings.append(f"no_session_after_candidate: {candidate.isoformat()}")
        elif s < start_date:
            pass
        elif end_date is not None and s > end_date:
            pass
        elif s in seen:
            pass
        else:
            seen.add(s)
            invest.append(s)
        y, m = _add_month(y, m, 1)

    return invest, warnings
