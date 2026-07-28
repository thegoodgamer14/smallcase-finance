"""NAV construction from returns and from weights + prices (pure)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date

from smallcase_finance.calc.returns import portfolio_return, simple_returns
from smallcase_finance.calc.weights import normalize_weights


def nav_from_returns(
    returns: Sequence[float],
    *,
    start_nav: float = 100.0,
) -> list[float]:
    """Build a NAV path via cumulative product of simple returns.

    ``returns[i]`` is the simple return ending on day i.
    Output length equals ``len(returns)``. For an explicit base day with
    return 0 (nav_series convention), pass ``[0.0, r1, r2, …]`` so
    ``nav[0] == start_nav``.
    """
    if start_nav <= 0:
        raise ValueError("start_nav must be > 0")
    nav: list[float] = []
    level = float(start_nav)
    for r in returns:
        level = level * (1.0 + float(r))
        nav.append(level)
    return nav


def cum_return_from_nav(
    nav: Sequence[float], base_nav: float | None = None
) -> list[float]:
    """``nav / base - 1`` for each point. Base defaults to first NAV."""
    if not nav:
        return []
    base = float(nav[0] if base_nav is None else base_nav)
    if base <= 0.0:
        raise ValueError("base_nav must be > 0")
    return [float(v) / base - 1.0 for v in nav]


def active_weights_on(
    versions: Sequence[Mapping[str, object]],
    d: date,
) -> dict[str, float]:
    """Resolve target weights for calendar date ``d``.

    Each version row needs: ``symbol``, ``target_weight``, ``effective_from``,
    optional ``effective_to`` (None = open). Active version = max
    ``effective_from`` among rows with ``effective_from <= d`` and
    (``effective_to`` is None or ``>= d``).
    """
    candidates: list[Mapping[str, object]] = []
    for r in versions:
        ef = r["effective_from"]
        et = r.get("effective_to")
        if ef is None:
            continue
        if ef <= d and (et is None or et >= d):
            candidates.append(r)
    if not candidates:
        return {}
    max_from = max(r["effective_from"] for r in candidates)  # type: ignore[type-var]
    out: dict[str, float] = {}
    for r in candidates:
        if r["effective_from"] == max_from:
            out[str(r["symbol"])] = float(r["target_weight"])  # type: ignore[arg-type]
    return out


def build_nav_from_prices(
    *,
    dates: Sequence[date],
    prices: Mapping[str, Mapping[date, float]],
    weights_for_date: Callable[[date], Mapping[str, float]],
    start_nav: float = 100.0,
    renormalize_gaps: bool = True,
) -> list[dict]:
    """Construct daily NAV from prices and a weight schedule.

    Gap policy (default): exclude symbols missing a return that day and
    renormalize remaining weights.
    """
    if start_nav <= 0.0:
        raise ValueError("start_nav must be > 0")
    if not dates:
        return []

    rows: list[dict] = []
    nav = float(start_nav)
    prev_prices: dict[str, float] = {}
    first = True
    base = float(start_nav)

    for d in dates:
        raw_w = weights_for_date(d)
        if not raw_w:
            continue
        try:
            w = normalize_weights(raw_w)
        except ValueError:
            continue

        asset_rets: dict[str, float] = {}
        n_used = 0
        for sym in w:
            today = prices.get(sym, {}).get(d)
            if today is None or today <= 0.0:
                continue
            if first:
                prev_prices[sym] = float(today)
                n_used += 1
                continue
            prev = prev_prices.get(sym)
            if prev is None or prev <= 0.0:
                prev_prices[sym] = float(today)
                continue
            asset_rets[sym] = float(today) / prev - 1.0
            prev_prices[sym] = float(today)
            n_used += 1

        if first:
            daily_ret = 0.0
            first = False
        else:
            daily_ret = portfolio_return(
                asset_rets, w, renormalize=renormalize_gaps
            )
            nav = nav * (1.0 + daily_ret)

        rows.append(
            {
                "date": d,
                "nav": nav,
                "daily_return": daily_ret,
                "cum_return": nav / base - 1.0,
                "n_constituents": n_used,
            }
        )

    return rows


def nav_series_from_price_list(
    prices: Sequence[float],
    start_nav: float = 100.0,
) -> list[float]:
    """Convenience: single-asset NAV from a price path."""
    rets = simple_returns(prices)
    return nav_from_returns(rets, start_nav=start_nav)
