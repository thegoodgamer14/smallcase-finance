"""Atomic Parquet writes and small helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import polars as pl

logger = logging.getLogger(__name__)


def atomic_write_parquet(
    df: pl.DataFrame,
    path: Path,
    *,
    sort_by: Sequence[str] | None = None,
) -> Path:
    """Write DataFrame to Parquet via ``*.tmp`` then rename (idempotent replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df
    if sort_by:
        present = [c for c in sort_by if c in out.columns]
        if present:
            out = out.sort(present)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    out.write_parquet(tmp)
    tmp.replace(path)
    logger.info("wrote %s (%d rows)", path, out.height)
    return path


def empty_frame(schema: dict[str, pl.DataType]) -> pl.DataFrame:
    return pl.DataFrame(schema=schema)
