"""Resolve curated Parquet paths under DATA_CURATED_ROOT.

Layout matches ADR 001 / docs/data-dictionary.md / docs/data/file-layout.md.
"""

from __future__ import annotations

from pathlib import Path

from smallcase_finance.config import DATA_CURATED_ROOT

# Repo root: src/smallcase_finance/data_access/paths.py → parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_RAW_ROOT: Path = _REPO_ROOT / "data" / "raw"

# Relative paths from curated root → parquet files (logical name → path)
CURATED_FILES: dict[str, str] = {
    "instruments": "instruments/instruments.parquet",
    "prices": "prices/prices.parquet",
    "smallcases": "smallcases/smallcases.parquet",
    "smallcase_constituents": "smallcases/smallcase_constituents.parquet",
    "rebalance_events": "rebalances/rebalance_events.parquet",
    "holdings_snapshots": "holdings/holdings_snapshots.parquet",
    "nav_series": "nav/nav_series.parquet",
    "metrics_snapshot": "metrics/metrics_snapshot.parquet",
    "contribution": "metrics/contribution.parquet",
}


def curated_root() -> Path:
    return DATA_CURATED_ROOT


def raw_root() -> Path:
    return DATA_RAW_ROOT


def parquet(name: str) -> Path:
    """Return absolute path for a logical curated table name.

    Raises KeyError if ``name`` is unknown.
    """
    rel = CURATED_FILES[name]
    return curated_root() / rel


def raw_smallcase_definition(smallcase_id: str) -> Path:
    """Path to authored JSON: data/raw/smallcases/{smallcase_id}.json."""
    slug = smallcase_id.strip().lower().replace(" ", "-")
    return raw_root() / "smallcases" / f"{slug}.json"


def iter_raw_smallcase_definitions() -> list[Path]:
    """All ``*.json`` definition files under data/raw/smallcases/."""
    folder = raw_root() / "smallcases"
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.json"))
