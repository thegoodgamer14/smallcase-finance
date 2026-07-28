"""Weight normalization and static portfolio helpers (pure)."""

from __future__ import annotations

from typing import Mapping


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Return non-negative weights renormalized to sum to 1.0.

    Raises
    ------
    ValueError
        If ``weights`` is empty or total mass is zero (or non-positive).
    """
    if not weights:
        raise ValueError("weights must be non-empty")
    cleaned = {str(k): float(v) for k, v in weights.items() if float(v) > 0.0}
    if not cleaned:
        raise ValueError("weights must contain at least one positive value")
    total = sum(cleaned.values())
    if total <= 0.0:
        raise ValueError("weight sum must be positive")
    return {k: v / total for k, v in cleaned.items()}


def weights_sum(weights: Mapping[str, float]) -> float:
    """Sum of weight values (no validation)."""
    return float(sum(float(v) for v in weights.values()))


def weight_drift(
    weights: Mapping[str, float],
    asset_returns: Mapping[str, float],
) -> dict[str, float]:
    """Apply one period of returns to weights and renormalize (buy-and-hold step).

    Symbols present in ``weights`` but missing from ``asset_returns`` keep return 0.
    Extra symbols in ``asset_returns`` are ignored.
    """
    if not weights:
        raise ValueError("weights must be non-empty")
    next_w: dict[str, float] = {}
    for sym, w in weights.items():
        r = float(asset_returns.get(sym, 0.0))
        next_w[sym] = float(w) * (1.0 + r)
    return normalize_weights(next_w)
