"""Ingest authored smallcase JSON definitions → curated tables."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from smallcase_finance.data_access.paths import iter_raw_smallcase_definitions
from smallcase_finance.schemas.models import SmallcaseDefinitionFile

logger = logging.getLogger(__name__)

SMALLCASE_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "name": pl.Utf8,
    "theme": pl.Utf8,
    "description": pl.Utf8,
    "methodology": pl.Utf8,
    "rebalance_rule": pl.Utf8,
    "base_nav": pl.Float64,
    "currency": pl.Utf8,
    "inception_date": pl.Date,
    "benchmark_id": pl.Utf8,
    "created_at": pl.Datetime("us", "UTC"),
    "updated_at": pl.Datetime("us", "UTC"),
    "notes": pl.Utf8,
}

CONSTITUENT_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "symbol": pl.Utf8,
    "target_weight": pl.Float64,
    "effective_from": pl.Date,
    "effective_to": pl.Date,
    "version_label": pl.Utf8,
    "created_at": pl.Datetime("us", "UTC"),
}

REBALANCE_SCHEMA: dict[str, pl.DataType] = {
    "smallcase_id": pl.Utf8,
    "rebalance_date": pl.Date,
    "reason": pl.Utf8,
    "from_effective_from": pl.Date,
    "to_effective_from": pl.Date,
    "notes": pl.Utf8,
    "created_at": pl.Datetime("us", "UTC"),
}


def _to_frame(rows: list[dict], schema: dict[str, pl.DataType]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=schema)
    df = pl.DataFrame(rows)
    for col, dtype in schema.items():
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))
        else:
            df = df.with_columns(pl.col(col).cast(dtype, strict=False))
    return df.select(list(schema.keys()))


def load_raw_smallcases(
    paths: list[Path] | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Parse definition JSON files → (smallcases, constituents, rebalance_events)."""
    files = paths if paths is not None else iter_raw_smallcase_definitions()
    if not files:
        logger.warning("no smallcase definition JSON under raw/smallcases/")
        return (
            pl.DataFrame(schema=SMALLCASE_SCHEMA),
            pl.DataFrame(schema=CONSTITUENT_SCHEMA),
            pl.DataFrame(schema=REBALANCE_SCHEMA),
        )

    now = datetime.now(timezone.utc)
    sc_rows: list[dict] = []
    c_rows: list[dict] = []
    r_rows: list[dict] = []

    for path in files:
        raw = path.read_text(encoding="utf-8")
        # pydantic parses ISO dates
        defn = SmallcaseDefinitionFile.model_validate_json(raw)
        if path.stem != defn.smallcase_id:
            logger.warning(
                "filename stem %r != smallcase_id %r in %s",
                path.stem,
                defn.smallcase_id,
                path,
            )

        sc = defn.to_smallcase(created_at=now)
        sc_rows.append(sc.model_dump())
        for c in defn.to_constituents(created_at=now):
            c_rows.append(c.model_dump())
        for ev in defn.to_rebalance_events(created_at=now):
            r_rows.append(ev.model_dump())

        logger.info(
            "loaded smallcase %s (%d constituent rows, %d rebalance events) from %s",
            defn.smallcase_id,
            sum(len(v.constituents) for v in defn.versions),
            len(defn.rebalance_events),
            path.name,
        )

    smallcases = _to_frame(sc_rows, SMALLCASE_SCHEMA).sort("smallcase_id")
    constituents = _to_frame(c_rows, CONSTITUENT_SCHEMA).sort(
        ["smallcase_id", "effective_from", "symbol"]
    )
    rebalances = _to_frame(r_rows, REBALANCE_SCHEMA).sort(
        ["smallcase_id", "rebalance_date"]
    )
    return smallcases, constituents, rebalances


def constituent_symbols(constituents: pl.DataFrame) -> set[str]:
    if constituents.height == 0:
        return set()
    return set(constituents["symbol"].unique().to_list())
