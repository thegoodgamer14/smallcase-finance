"""StrategyConfig / SIPConfig validation and YAML/JSON loaders."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from smallcase_finance.strategies import (
    AllocationMode,
    SIPConfig,
    StrategyConfig,
    StrategyConfigError,
    load_strategy_config,
    strategy_config_from_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_YAML = REPO_ROOT / "config" / "strategies" / "example-sip-equity.yaml"


def _valid_inline_payload(**overrides):
    base = {
        "strategy_id": "test-sip",
        "name": "Test SIP",
        "basket": {
            "kind": "inline",
            "constituents": [
                {"symbol": "TCS", "target_weight": 0.5},
                {"symbol": "INFY", "target_weight": 0.5},
            ],
        },
        "sip": {
            "amount": 5000,
            "day_of_month": 5,
            "start_date": "2023-01-01",
        },
    }
    base.update(overrides)
    return base


def test_example_yaml_loads():
    assert EXAMPLE_YAML.is_file(), f"missing example strategy: {EXAMPLE_YAML}"
    cfg = load_strategy_config(EXAMPLE_YAML)
    assert isinstance(cfg, StrategyConfig)
    assert cfg.strategy_id == "example-sip-equity"
    assert cfg.sip.amount == 5000
    assert cfg.sip.day_of_month == 5
    assert cfg.sip.start_date == date(2023, 1, 1)
    assert cfg.allocation_mode == AllocationMode.custom_weights
    assert cfg.currency == "INR"
    weights = cfg.resolved_weights()
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert set(weights) == {"TCS", "INFY", "RELIANCE", "HDFCBANK"}


def test_nested_sip_config_valid():
    cfg = strategy_config_from_dict(_valid_inline_payload())
    assert cfg.sip_amount == 5000
    assert cfg.day_of_month == 5
    assert cfg.start_date == date(2023, 1, 1)
    assert cfg.end_date is None
    assert cfg.costs.brokerage_bps == 0


def test_flat_fields_normalized_to_sip():
    """Data-dictionary flat shape is accepted."""
    payload = {
        "strategy_id": "flat-sip",
        "name": "Flat SIP",
        "basket": {
            "kind": "inline",
            "constituents": [
                {"symbol": "tcs", "target_weight": 0.5},
                {"symbol": "infy", "target_weight": 0.5},
            ],
        },
        "sip_amount": 10000,
        "day_of_month": 1,
        "start_date": "2022-06-01",
        "end_date": "2024-06-01",
    }
    cfg = strategy_config_from_dict(payload)
    assert cfg.sip.amount == 10000
    assert cfg.sip.day_of_month == 1
    assert cfg.sip.end_date == date(2024, 6, 1)
    # symbols uppercased
    assert cfg.resolved_weights()["TCS"] == 0.5


def test_smallcase_ref_basket():
    cfg = strategy_config_from_dict(
        {
            "strategy_id": "digital-india-sip-5k",
            "name": "Digital India SIP",
            "basket": {"kind": "smallcase_ref", "smallcase_id": "digital-india"},
            "sip": {
                "amount": 5000,
                "day_of_month": 5,
                "start_date": "2022-01-01",
            },
        }
    )
    assert cfg.basket.kind == "smallcase_ref"
    assert cfg.basket.smallcase_id == "digital-india"
    with pytest.raises(ValueError, match="inline"):
        cfg.resolved_weights()


def test_reject_day_of_month_out_of_range():
    with pytest.raises(StrategyConfigError):
        strategy_config_from_dict(
            _valid_inline_payload(sip={"amount": 1000, "day_of_month": 29, "start_date": "2023-01-01"})
        )


def test_reject_non_positive_amount():
    with pytest.raises(StrategyConfigError):
        strategy_config_from_dict(
            _valid_inline_payload(sip={"amount": 0, "day_of_month": 5, "start_date": "2023-01-01"})
        )


def test_reject_weights_not_summing_to_one():
    with pytest.raises(StrategyConfigError, match="sum"):
        strategy_config_from_dict(
            _valid_inline_payload(
                basket={
                    "kind": "inline",
                    "constituents": [
                        {"symbol": "TCS", "target_weight": 0.3},
                        {"symbol": "INFY", "target_weight": 0.3},
                    ],
                }
            )
        )


def test_equal_weight_ignores_missing_weights():
    cfg = strategy_config_from_dict(
        _valid_inline_payload(
            allocation_mode="equal_weight",
            basket={
                "kind": "inline",
                "constituents": [
                    {"symbol": "TCS"},
                    {"symbol": "INFY"},
                    {"symbol": "RELIANCE"},
                ],
            },
        )
    )
    w = cfg.resolved_weights()
    assert len(w) == 3
    assert abs(w["TCS"] - 1 / 3) < 1e-12


def test_reject_exchange_suffix():
    with pytest.raises(StrategyConfigError):
        strategy_config_from_dict(
            _valid_inline_payload(
                basket={
                    "kind": "inline",
                    "constituents": [
                        {"symbol": "INFY.NS", "target_weight": 0.5},
                        {"symbol": "TCS", "target_weight": 0.5},
                    ],
                }
            )
        )


def test_reject_bad_strategy_id():
    with pytest.raises(StrategyConfigError):
        strategy_config_from_dict(_valid_inline_payload(strategy_id="Not A Slug"))


def test_reject_start_after_end():
    with pytest.raises(StrategyConfigError):
        strategy_config_from_dict(
            _valid_inline_payload(
                sip={
                    "amount": 1000,
                    "day_of_month": 5,
                    "start_date": "2024-01-01",
                    "end_date": "2023-01-01",
                }
            )
        )


def test_sip_config_standalone():
    sip = SIPConfig(amount=2500, day_of_month=10, start_date=date(2023, 3, 1))
    assert sip.amount == 2500


def test_missing_file():
    with pytest.raises(StrategyConfigError, match="not found"):
        load_strategy_config("/tmp/does-not-exist-strategy-xyz.yaml")


def test_json_roundtrip(tmp_path: Path):
    path = tmp_path / "strat.json"
    path.write_text(
        """
        {
          "strategy_id": "json-sip",
          "name": "JSON SIP",
          "basket": {
            "kind": "inline",
            "constituents": [
              {"symbol": "TCS", "target_weight": 1.0}
            ]
          },
          "sip_amount": 1000,
          "day_of_month": 15,
          "start_date": "2023-01-15"
        }
        """,
        encoding="utf-8",
    )
    cfg = load_strategy_config(path)
    assert cfg.strategy_id == "json-sip"
    assert cfg.sip.day_of_month == 15
