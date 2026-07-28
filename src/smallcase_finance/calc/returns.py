"""Asset and portfolio return series helpers (pure)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def simple_returns(prices: Sequence[float], *, first_return: float = 0.0) -> list[float]:
    """Close-to-close simple returns aligned with ``prices`` length.

    ``result[0] = first_return`` (default 0.0, matching nav_series convention).
    ``result[t] = prices[t] / prices[t-1] - 1`` for t >= 1.
    """
    if not prices:
        return []
    out = [float(first_return)]
    for i in range(1, len(prices)):
        prev = float(prices[i - 1])
        cur = float(prices[i])
        if prev <= 0.0:
            raise ValueError(f"price at index {i - 1} must be > 0, got {prev}")
        out.append(cur / prev - 1.0)
    return out


def total_return_from_prices(prices: Sequence[float]) -> float:
    """Total simple return from first to last price: ``p_T / p_0 - 1``."""
    if len(prices) < 1:
        raise ValueError("prices must be non-empty")
    p0 = float(prices[0])
    p1 = float(prices[-1])
    if p0 <= 0.0:
        raise ValueError("first price must be > 0")
    return p1 / p0 - 1.0


def portfolio_return(
    asset_returns: Mapping[str, float],
    weights: Mapping[str, float],
    *,
    renormalize: bool = True,
) -> float:
    """Single-period portfolio return ``Σ w_i r_i``.

    If ``renormalize`` is True (default), only symbols present in both maps
    contribute and their weights are scaled to sum to 1 (gap policy).
    """
    if not weights:
        return 0.0

    port = 0.0
    used_w = 0.0
    for sym, w in weights.items():
        if sym not in asset_returns:
            continue
        ww = float(w)
        if ww == 0.0:
            continue
        port += ww * float(asset_returns[sym])
        used_w += ww

    if used_w <= 0.0:
        return 0.0
    if renormalize and abs(used_w - 1.0) > 1e-12:
        return port / used_w
    return port


def portfolio_returns(
    asset_returns: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
) -> list[float]:
    """Weighted sum of aligned simple return series (static weights).

    All series in ``asset_returns`` must share the same length.
    Symbols missing from weights are ignored; missing asset series for a
    weight key contributes 0 that day (caller should pre-align / drop).
    """
    if not weights:
        raise ValueError("weights must be non-empty")
    length: int | None = None
    for series in asset_returns.values():
        n = len(series)
        if length is None:
            length = n
        elif n != length:
            raise ValueError("all asset return series must have equal length")
    if length is None:
        return []

    out: list[float] = []
    for i in range(length):
        day = {
            sym: float(series[i])
            for sym, series in asset_returns.items()
        }
        # no renormalize here — matches static-weight series contract
        r = 0.0
        for sym, w in weights.items():
            if sym in day:
                r += float(w) * day[sym]
        out.append(r)
    return out


def contribution_by_symbol(
    weights: Mapping[str, float],
    symbol_returns: Mapping[str, float],
) -> dict[str, float]:
    """Simple contribution: ``w_i * r_i`` for symbols in both maps."""
    out: dict[str, float] = {}
    for sym, w in weights.items():
        if sym not in symbol_returns:
            continue
        out[sym] = float(w) * float(symbol_returns[sym])
    return out


def residual_contribution(
    portfolio_ret: float,
    contributions: Mapping[str, float],
) -> float:
    """``portfolio_return - sum(contributions)`` (interaction residual)."""
    return float(portfolio_ret) - float(sum(contributions.values()))
