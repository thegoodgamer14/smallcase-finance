"""Symbol → Upstox instrument_key resolution for NSE equities.

Upstox historical APIs require an instrument key of the form ``NSE_EQ|<ISIN>``.
We ship a curated map for symbols used in sample smallcases and common large caps.
Override or extend via ``data/raw/instruments/upstox_instrument_map.json``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from smallcase_finance.data_access.paths import raw_root

logger = logging.getLogger(__name__)

# Curated NSE equity map (symbol → instrument_key). ISINs are public identifiers.
# Extend as needed; unknown symbols are skipped with a warning at sync time.
DEFAULT_NSE_INSTRUMENT_KEYS: dict[str, str] = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "INFY": "NSE_EQ|INE009A01021",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "ITC": "NSE_EQ|INE154A01025",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "WIPRO": "NSE_EQ|INE075A01022",
    "TECHM": "NSE_EQ|INE669C01036",
    "LTIM": "NSE_EQ|INE214T01019",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "TITAN": "NSE_EQ|INE280A01028",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "NESTLEIND": "NSE_EQ|INE239A01024",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "NTPC": "NSE_EQ|INE733E01010",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "M&M": "NSE_EQ|INE101A01026",
    "MM": "NSE_EQ|INE101A01026",
}


def _load_override_map() -> dict[str, str]:
    """Optional JSON: {\"TCS\": \"NSE_EQ|INE...\", ...}."""
    candidates = [
        raw_root() / "instruments" / "upstox_instrument_map.json",
        raw_root() / "upstox_instrument_map.json",
    ]
    out: dict[str, str] = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("failed to load instrument map %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("instrument map %s is not an object; ignoring", path)
            continue
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                out[k.strip().upper()] = v.strip()
        logger.info("loaded %d instrument key overrides from %s", len(out), path)
    return out


def instrument_key_map() -> dict[str, str]:
    """Merged default + override map (overrides win)."""
    merged = dict(DEFAULT_NSE_INSTRUMENT_KEYS)
    merged.update(_load_override_map())
    return merged


def resolve_instrument_key(symbol: str, mapping: dict[str, str] | None = None) -> str | None:
    """Return Upstox instrument_key for a trading symbol, or None if unknown."""
    sym = symbol.strip().upper().replace(".NS", "").replace(".NSE", "")
    m = mapping if mapping is not None else instrument_key_map()
    return m.get(sym)
