"""Price panel loader for SIP Lab — curated Parquet → engine-ready frame.

Reads ``data/curated/prices/prices.parquet`` (via DuckDB). No live network.
Classifies ``data_source`` from the Parquet ``source`` column so UI/API can
label demo (sample) vs Upstox-backed history (ADR 005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Optional, Sequence

from smallcase_finance.data_access.duck import read_parquet_sql, table_exists
from smallcase_finance.data_access.exceptions import CuratedDataUnavailable
from smallcase_finance.data_access.paths import parquet

# Normalized labels returned to API / service layer
DATA_SOURCE_UPSTOX = "upstox"
DATA_SOURCE_SAMPLE = "sample"
DATA_SOURCE_FIXTURE = "fixture"
DATA_SOURCE_MIXED = "mixed"
DATA_SOURCE_UNKNOWN = "unknown"

_UPSTOX_TOKENS = frozenset({"upstox", "upstox_api", "upstox-api"})
_SAMPLE_TOKENS = frozenset({"sample", "demo", "synthetic", "generated"})
_FIXTURE_TOKENS = frozenset({"fixture", "test", "golden"})


def _coerce_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return None


def list_curated_symbols() -> list[str]:
    """Distinct symbols in curated prices.parquet (sorted). Empty if missing."""
    path = parquet("prices")
    if not table_exists(path):
        return []
    try:
        rows = read_parquet_sql(
            path,
            columns="DISTINCT symbol",
            order_by="symbol",
        )
    except Exception:
        return []
    out: list[str] = []
    for row in rows:
        v = row.get("symbol")
        if v is None:
            continue
        s = str(v).strip().upper()
        if s:
            out.append(s)
    return out


def classify_data_source(sources: Sequence[str] | set[str] | frozenset[str]) -> str:
    """Map raw ``source`` column values → product label.

    Rules (binding for SIP Lab labels):
    - all empty / missing → ``unknown``
    - every token is Upstox-like → ``upstox``
    - every token is sample/demo/synthetic → ``sample``
    - every token is fixture/test → ``fixture``
    - otherwise → ``mixed``
    """
    cleaned: set[str] = set()
    for s in sources:
        if s is None:
            continue
        t = str(s).strip().lower()
        if t:
            cleaned.add(t)
    if not cleaned:
        return DATA_SOURCE_UNKNOWN

    def _bucket(token: str) -> str:
        if token in _UPSTOX_TOKENS or token.startswith("upstox"):
            return DATA_SOURCE_UPSTOX
        if token in _SAMPLE_TOKENS or token.startswith("sample"):
            return DATA_SOURCE_SAMPLE
        if token in _FIXTURE_TOKENS or token.startswith("fixture"):
            return DATA_SOURCE_FIXTURE
        # Dated drop folders like ``2026-07-28_sample`` already normalized by
        # ingest; treat remaining non-upstox as sample-class for safety.
        if "sample" in token or "demo" in token:
            return DATA_SOURCE_SAMPLE
        if "upstox" in token:
            return DATA_SOURCE_UPSTOX
        return DATA_SOURCE_UNKNOWN

    buckets = {_bucket(t) for t in cleaned}
    if len(buckets) == 1:
        return next(iter(buckets))
    # pure unknown + one real label → that label
    real = buckets - {DATA_SOURCE_UNKNOWN}
    if len(real) == 1:
        return next(iter(real))
    return DATA_SOURCE_MIXED


@dataclass
class PricePanel:
    """Sparse price panel for a strategy universe over a date range.

    ``by_symbol[symbol][date] = price`` for bars that exist.
    ``sessions`` = sorted unique dates with **any** requested symbol bar
    (SIP session calendar per sip-engine.md §6.1 MVP).
    """

    symbols: list[str]
    by_symbol: dict[str, dict[date, float]]
    sessions: list[date]
    sources: frozenset[str]
    data_source: str
    missing_symbols: list[str]
    price_field: str
    start: Optional[date] = None
    end: Optional[date] = None
    warnings: list[str] = field(default_factory=list)

    def price_on(self, symbol: str, d: date) -> Optional[float]:
        series = self.by_symbol.get(symbol.upper())
        if not series:
            return None
        return series.get(d)

    def prices_on(self, d: date) -> dict[str, float]:
        """Symbol → price for all symbols with a bar on ``d``."""
        out: dict[str, float] = {}
        for sym, series in self.by_symbol.items():
            p = series.get(d)
            if p is not None and p > 0:
                out[sym] = p
        return out

    @property
    def available_symbols(self) -> list[str]:
        return sorted(self.by_symbol.keys())


def build_price_panel_from_rows(
    rows: Sequence[Mapping[str, Any]],
    symbols: Sequence[str],
    *,
    price_field: str = "close",
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> PricePanel:
    """Build a ``PricePanel`` from already-loaded row dicts (tests / fixtures).

    No I/O. Rows need at least ``symbol``, ``date``, and the price field.
    Optional ``source`` drives ``data_source`` classification.
    """
    wanted = [s.strip().upper() for s in symbols if s and str(s).strip()]
    wanted_set = set(wanted)
    field = (price_field or "close").strip().lower()
    if field not in {"close", "adj_close"}:
        field = "close"

    # When live Upstox bars exist for this universe, ignore sample/demo rows so
    # SIP Lab does not report data_source=mixed after a successful sync.
    scoped: list[Mapping[str, Any]] = []
    for r in rows:
        sym = str(r.get("symbol", "")).strip().upper()
        if sym not in wanted_set:
            continue
        d = _coerce_date(r.get("date"))
        if d is None:
            continue
        if start is not None and d < start:
            continue
        if end is not None and d > end:
            continue
        scoped.append(r)

    def _is_upstox_src(r: Mapping[str, Any]) -> bool:
        s = str(r.get("source") or "").strip().lower()
        return "upstox" in s

    has_upstox = any(_is_upstox_src(r) for r in scoped)
    if has_upstox:
        scoped = [r for r in scoped if _is_upstox_src(r)]

    by_symbol: dict[str, dict[date, float]] = {s: {} for s in wanted}
    source_vals: set[str] = set()
    session_set: set[date] = set()
    warnings: list[str] = []

    for r in scoped:
        sym = str(r.get("symbol", "")).strip().upper()
        d = _coerce_date(r.get("date"))
        if d is None:
            continue
        raw = r.get(field)
        if raw is None and field == "adj_close":
            raw = r.get("close")
        if raw is None:
            continue
        try:
            px = float(raw)
        except (TypeError, ValueError):
            continue
        if px <= 0.0:
            continue
        by_symbol[sym][d] = px
        session_set.add(d)
        src = r.get("source")
        if src is not None and str(src).strip():
            source_vals.add(str(src).strip().lower())

    # Drop empty series; track missing
    missing = [s for s in wanted if not by_symbol.get(s)]
    by_symbol = {s: series for s, series in by_symbol.items() if series}

    if missing:
        warnings.append(
            "missing_symbols: no prices for " + ", ".join(missing)
        )

    # Simple gap diagnostics: symbols with far fewer bars than the densest
    if by_symbol:
        counts = {s: len(series) for s, series in by_symbol.items()}
        max_n = max(counts.values())
        sparse = [s for s, n in counts.items() if max_n > 0 and n < max_n * 0.5]
        if sparse:
            warnings.append(
                "sparse_history: " + ", ".join(sorted(sparse))
                + f" have <50% of max bars ({max_n})"
            )

    data_source = classify_data_source(source_vals)
    if data_source in {DATA_SOURCE_SAMPLE, DATA_SOURCE_FIXTURE, DATA_SOURCE_UNKNOWN}:
        warnings.append(
            f"data_source={data_source}: demo/synthetic prices — not live market SIP"
        )
    elif data_source == DATA_SOURCE_MIXED:
        warnings.append(
            "data_source=mixed: price rows include more than one source label"
        )

    sessions = sorted(session_set)
    return PricePanel(
        symbols=wanted,
        by_symbol=by_symbol,
        sessions=sessions,
        sources=frozenset(source_vals),
        data_source=data_source,
        missing_symbols=missing,
        price_field=field,
        start=start,
        end=end,
        warnings=warnings,
    )


def load_price_panel(
    symbols: Sequence[str],
    *,
    start: Optional[date] = None,
    end: Optional[date] = None,
    price_field: str = "close",
    require_table: bool = True,
) -> PricePanel:
    """Load a price panel for ``symbols`` from curated Parquet.

    Parameters
    ----------
    symbols:
        Tickers (case-insensitive; uppercased).
    start / end:
        Inclusive date filters (optional).
    price_field:
        ``close`` (default) or ``adj_close``.
    require_table:
        If True (default), missing Parquet raises ``CuratedDataUnavailable``.
        If False, returns an empty panel with a warning.
    """
    path = parquet("prices")
    wanted = [s.strip().upper() for s in symbols if s and str(s).strip()]
    field = (price_field or "close").strip().lower()

    if not wanted:
        return PricePanel(
            symbols=[],
            by_symbol={},
            sessions=[],
            sources=frozenset(),
            data_source=DATA_SOURCE_UNKNOWN,
            missing_symbols=[],
            price_field=field,
            start=start,
            end=end,
            warnings=["no_symbols_requested"],
        )

    if not table_exists(path):
        msg = (
            "Curated table 'prices' is missing; run the data pipeline first "
            f"(expected {path})"
        )
        if require_table:
            raise CuratedDataUnavailable(msg)
        return PricePanel(
            symbols=wanted,
            by_symbol={},
            sessions=[],
            sources=frozenset(),
            data_source=DATA_SOURCE_UNKNOWN,
            missing_symbols=list(wanted),
            price_field=field,
            start=start,
            end=end,
            warnings=[f"prices_table_missing: {msg}", "missing_symbols: " + ", ".join(wanted)],
        )

    placeholders = ", ".join(["?"] * len(wanted))
    clauses = [f"symbol IN ({placeholders})"]
    params: list[Any] = list(wanted)
    if start is not None:
        clauses.append("date >= ?")
        params.append(start)
    if end is not None:
        clauses.append("date <= ?")
        params.append(end)

    # Prefer selecting source when present; DuckDB will error if column missing
    # so we try full select first, fall back without source.
    try:
        rows = read_parquet_sql(
            path,
            columns=f"symbol, date, {field}, source",
            where=" AND ".join(clauses),
            order_by="symbol, date",
            params=params,
        )
    except Exception:
        # Column set may lack source or adj_close — retry broader
        try:
            rows = read_parquet_sql(
                path,
                where=" AND ".join(clauses),
                order_by="symbol, date",
                params=params,
            )
        except Exception as exc:
            raise CuratedDataUnavailable(
                f"Failed to read curated prices: {exc}"
            ) from exc

    for r in rows:
        r["date"] = _coerce_date(r.get("date"))

    return build_price_panel_from_rows(
        rows,
        wanted,
        price_field=field,
        start=start,
        end=end,
    )
