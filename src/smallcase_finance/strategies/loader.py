"""Load and validate StrategyConfig from YAML or JSON files / dicts.

Supports two authoring shapes (normalized before Pydantic validation):

1. **Nested** (preferred for YAML under ``config/strategies/``)::

       sip:
         amount: 5000
         day_of_month: 5
         start_date: 2023-01-01

2. **Flat** (data-dictionary / sip-engine.md)::

       sip_amount: 5000
       day_of_month: 5
       start_date: 2023-01-01
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from smallcase_finance.strategies.models import StrategyConfig

_FLAT_SIP_KEYS = ("sip_amount", "day_of_month", "start_date", "end_date", "as_of")


class StrategyConfigError(ValueError):
    """Raised when a strategy file cannot be loaded or validated."""


def normalize_strategy_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a dict with nested ``sip`` suitable for ``StrategyConfig``.

    Flat fields are folded into ``sip``; nested ``sip`` wins if both present
    for the same key (nested keys take precedence only when already set).
    """
    if not isinstance(data, Mapping):
        raise StrategyConfigError("strategy payload must be a mapping/object")

    out: dict[str, Any] = dict(data)

    has_flat = any(k in out for k in _FLAT_SIP_KEYS)
    sip_obj = out.get("sip")
    if sip_obj is not None and not isinstance(sip_obj, Mapping):
        raise StrategyConfigError("'sip' must be an object when provided")

    if has_flat or sip_obj is not None:
        nested: dict[str, Any] = dict(sip_obj) if isinstance(sip_obj, Mapping) else {}
        # Flat → nested aliases
        if "sip_amount" in out and "amount" not in nested:
            nested["amount"] = out.pop("sip_amount")
        elif "sip_amount" in out:
            out.pop("sip_amount")

        for key in ("day_of_month", "start_date", "end_date", "as_of"):
            if key in out and key not in nested:
                nested[key] = out.pop(key)
            elif key in out:
                out.pop(key)

        # Also accept flat "amount" at top level as SIP amount
        if "amount" in out and "amount" not in nested:
            nested["amount"] = out.pop("amount")

        out["sip"] = nested

    return out


def strategy_config_from_dict(data: Mapping[str, Any]) -> StrategyConfig:
    """Validate a mapping into ``StrategyConfig``."""
    try:
        normalized = normalize_strategy_payload(data)
        return StrategyConfig.model_validate(normalized)
    except StrategyConfigError:
        raise
    except Exception as exc:  # pydantic ValidationError and others
        raise StrategyConfigError(str(exc)) from exc


def load_strategy_config(path: str | Path) -> StrategyConfig:
    """Load YAML (``.yaml``/``.yml``) or JSON (``.json``) strategy file."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise StrategyConfigError(f"strategy file not found: {p}")

    suffix = p.suffix.lower()
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise StrategyConfigError(f"cannot read strategy file {p}: {exc}") from exc

    if suffix in {".yaml", ".yml"}:
        data = _parse_yaml(text, source=str(p))
    elif suffix == ".json":
        data = _parse_json(text, source=str(p))
    else:
        # Try JSON first, then YAML
        try:
            data = _parse_json(text, source=str(p))
        except StrategyConfigError:
            data = _parse_yaml(text, source=str(p))

    if not isinstance(data, Mapping):
        raise StrategyConfigError(f"strategy root must be an object: {p}")

    return strategy_config_from_dict(data)


def _parse_json(text: str, *, source: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StrategyConfigError(f"invalid JSON in {source}: {exc}") from exc


def _parse_yaml(text: str, *, source: str) -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise StrategyConfigError(
            "PyYAML is required to load YAML strategy files. "
            "Install with: pip install pyyaml"
        ) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise StrategyConfigError(f"invalid YAML in {source}: {exc}") from exc
