"""List / load SIP strategies from config/strategies/*.yaml|json.

File-backed only for MVP — no write API. Never returns secrets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from smallcase_finance.config import STRATEGIES_DIR
from smallcase_finance.schemas.sip import (
    StrategyDetailResponse,
    StrategyListResponse,
    StrategySummary,
)
from smallcase_finance.strategies.loader import (
    StrategyConfigError,
    load_strategy_config,
)
from smallcase_finance.strategies.models import InlineBasket, StrategyConfig


class StrategyNotFound(LookupError):
    """Unknown strategy_id under config/strategies/."""

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Strategy not found: {strategy_id}")


_STRATEGY_SUFFIXES = (".yaml", ".yml", ".json")
_SUMMARY_MAX = 240


def _truncate(text: Optional[str], n: int = _SUMMARY_MAX) -> Optional[str]:
    if text is None:
        return None
    s = " ".join(text.split())
    if not s:
        return None
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _n_constituents(cfg: StrategyConfig) -> Optional[int]:
    if isinstance(cfg.basket, InlineBasket):
        return len(cfg.basket.constituents)
    return None


def _summary_from_cfg(cfg: StrategyConfig) -> StrategySummary:
    return StrategySummary(
        id=cfg.strategy_id,
        name=cfg.name,
        summary=_truncate(cfg.notes),
        currency=cfg.currency,
        sip_amount=cfg.sip_amount,
        day_of_month=cfg.day_of_month,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        allocation_mode=cfg.allocation_mode.value
        if hasattr(cfg.allocation_mode, "value")
        else str(cfg.allocation_mode),
        n_constituents=_n_constituents(cfg),
        version=cfg.version,
    )


def _detail_from_cfg(cfg: StrategyConfig, *, path: Optional[Path] = None) -> StrategyDetailResponse:
    source_path: Optional[str] = None
    if path is not None:
        try:
            # Prefer repo-relative path when under strategies dir parent tree
            source_path = str(path)
            if STRATEGIES_DIR in path.parents or path.parent == STRATEGIES_DIR:
                source_path = f"config/strategies/{path.name}"
        except Exception:
            source_path = path.name

    return StrategyDetailResponse(
        id=cfg.strategy_id,
        name=cfg.name,
        currency=cfg.currency,
        version=cfg.version,
        notes=cfg.notes,
        allocation_mode=cfg.allocation_mode.value
        if hasattr(cfg.allocation_mode, "value")
        else str(cfg.allocation_mode),
        price_field=cfg.price_field.value
        if hasattr(cfg.price_field, "value")
        else str(cfg.price_field),
        rebalance_mode=cfg.rebalance_mode.value
        if hasattr(cfg.rebalance_mode, "value")
        else str(cfg.rebalance_mode),
        fractional_units=cfg.fractional_units,
        basket=cfg.basket.model_dump(mode="json"),
        sip=cfg.sip.model_dump(mode="json"),
        costs=cfg.costs.model_dump(mode="json"),
        source_path=source_path,
    )


def resolve_strategy_path(
    strategy_id: str,
    *,
    strategies_dir: Optional[Path] = None,
) -> Path:
    """Resolve ``strategy_id`` → existing file path.

    Accepts bare id (``example-sip-equity``) matching stem of yaml/yml/json.
    Rejects path traversal.
    """
    sid = (strategy_id or "").strip()
    if not sid:
        raise StrategyNotFound(strategy_id)
    # No path separators / traversal
    if "/" in sid or "\\" in sid or ".." in sid or sid.startswith("."):
        raise StrategyNotFound(strategy_id)

    root = Path(strategies_dir or STRATEGIES_DIR).expanduser().resolve()
    if not root.is_dir():
        raise StrategyNotFound(sid)

    candidates = [root / f"{sid}{suf}" for suf in _STRATEGY_SUFFIXES]
    for p in candidates:
        if p.is_file():
            return p

    # Case-insensitive stem match as fallback
    lower = sid.lower()
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _STRATEGY_SUFFIXES:
            continue
        if p.stem.lower() == lower:
            return p

    raise StrategyNotFound(sid)


class StrategyService:
    """File-backed strategy catalogue under ``config/strategies/``."""

    def __init__(self, strategies_dir: Optional[Path] = None) -> None:
        self.strategies_dir = Path(strategies_dir or STRATEGIES_DIR).expanduser()

    def list_strategies(self) -> StrategyListResponse:
        root = self.strategies_dir
        if not root.is_dir():
            return StrategyListResponse(items=[])

        items: list[StrategySummary] = []
        seen_ids: set[str] = set()
        files = sorted(
            p
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in _STRATEGY_SUFFIXES
        )
        for path in files:
            try:
                cfg = load_strategy_config(path)
            except StrategyConfigError:
                # Skip invalid files rather than failing the whole list
                continue
            if cfg.strategy_id in seen_ids:
                continue
            seen_ids.add(cfg.strategy_id)
            items.append(_summary_from_cfg(cfg))

        items.sort(key=lambda s: s.id)
        return StrategyListResponse(items=items)

    def get_strategy(self, strategy_id: str) -> StrategyDetailResponse:
        path = resolve_strategy_path(strategy_id, strategies_dir=self.strategies_dir)
        try:
            cfg = load_strategy_config(path)
        except StrategyConfigError as exc:
            # Surface as ValueError so API maps to 400 (invalid config)
            raise ValueError(f"invalid strategy config {strategy_id!r}: {exc}") from exc
        return _detail_from_cfg(cfg, path=path)

    def load_config(self, strategy_id: str) -> StrategyConfig:
        """Load validated ``StrategyConfig`` by id (for SIP runs)."""
        path = resolve_strategy_path(strategy_id, strategies_dir=self.strategies_dir)
        try:
            return load_strategy_config(path)
        except StrategyConfigError as exc:
            raise ValueError(f"invalid strategy config {strategy_id!r}: {exc}") from exc
