"""SIP Lab run orchestration — StrategyConfig + curated prices → SipRunResult.

Does **not** call v0 weight-NAV rebalance (``backtest_service``). Dedicated
cashflow path via ``calc.sip_schedule`` + ``calc.sip_sim.run_sip_simulation``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional, Sequence, Union

from smallcase_finance.calc.risk import cagr, volatility
from smallcase_finance.calc.returns import simple_returns
from smallcase_finance.calc.sip_schedule import sip_invest_dates
from smallcase_finance.calc.sip_sim import (
    SipSimulationResult,
    run_sip_simulation,
    symbol_contribution,
)
from smallcase_finance.calc.weights import normalize_weights
from smallcase_finance.data_access import smallcases as sc_da
from smallcase_finance.data_access.exceptions import CuratedDataUnavailable
from smallcase_finance.data_access.price_panel import (
    PricePanel,
    build_price_panel_from_rows,
    load_price_panel,
)
from smallcase_finance.schemas.sip import (
    SipAssumptions,
    SipBacktestRequest,
    SipBacktestResponse,
    SipCashflowDTO,
    SipMarketValueDTO,
    SipMetricsDTO,
    SipRunResult,
    SipSeriesPoint,
    SipSymbolContributionDTO,
)
from smallcase_finance.strategies.loader import (
    StrategyConfigError,
    load_strategy_config,
    strategy_config_from_dict,
)
from smallcase_finance.strategies.models import (
    InlineBasket,
    SmallcaseRefBasket,
    StrategyConfig,
)


class SipServiceError(ValueError):
    """Raised when a SIP run cannot be prepared or executed."""


def _to_strategy(strategy: Union[StrategyConfig, str, Path, dict]) -> StrategyConfig:
    if isinstance(strategy, StrategyConfig):
        return strategy
    if isinstance(strategy, dict):
        try:
            return strategy_config_from_dict(strategy)
        except StrategyConfigError as exc:
            raise SipServiceError(str(exc)) from exc
    if isinstance(strategy, (str, Path)):
        try:
            return load_strategy_config(strategy)
        except StrategyConfigError as exc:
            raise SipServiceError(str(exc)) from exc
    raise SipServiceError(f"unsupported strategy type: {type(strategy)!r}")


def _resolve_target_weights(
    cfg: StrategyConfig,
    *,
    as_of: Optional[date] = None,
) -> tuple[dict[str, float], list[str]]:
    """Return (weights, warnings) for the strategy basket."""
    warnings: list[str] = []
    basket = cfg.basket

    if isinstance(basket, InlineBasket):
        return cfg.resolved_weights(), warnings

    if isinstance(basket, SmallcaseRefBasket):
        sid = basket.smallcase_id
        try:
            rows = sc_da.get_constituents(sid, as_of=as_of or cfg.start_date)
        except Exception as exc:
            raise SipServiceError(
                f"cannot resolve smallcase_ref {sid!r}: {exc}"
            ) from exc
        if not rows:
            raise SipServiceError(
                f"no constituents for smallcase_ref {sid!r} "
                f"as of {as_of or cfg.start_date}"
            )
        raw = {
            str(r["symbol"]).upper(): float(r["target_weight"]) for r in rows
        }
        if cfg.allocation_mode.value == "equal_weight":
            n = len(raw)
            weights = {s: 1.0 / n for s in raw}
        else:
            weights = normalize_weights(raw)
        warnings.append(
            f"smallcase_ref_weights: resolved {len(weights)} symbols from {sid}"
        )
        return weights, warnings

    raise SipServiceError(
        f"unsupported basket kind: {getattr(basket, 'kind', basket)}"
    )


def _xirr_status(sim: SipSimulationResult) -> tuple[str, Optional[str]]:
    if sim.xirr is not None:
        return "ok", None
    if sim.n_sips < 1 or len(sim.cashflows) < 2:
        return "undefined", "insufficient_cashflows"
    return "failed", "no_real_root_or_non_convergence"


def _sim_to_dto(
    *,
    cfg: StrategyConfig,
    sim: SipSimulationResult,
    data_source: str,
    prices_by_symbol: dict[str, dict[date, float]],
    extra_warnings: Sequence[str],
    price_field: str,
) -> SipRunResult:
    warnings = list(extra_warnings) + list(sim.warnings)
    seen: set[str] = set()
    uniq: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq.append(w)

    xirr_status, xirr_msg = _xirr_status(sim)

    # Secondary path metrics (never replace XIRR)
    mv_vals = [p.market_value for p in sim.market_value]
    mv_dates = [p.date for p in sim.market_value]
    vol: Optional[float] = None
    cagr_mv: Optional[float] = None
    if len(mv_vals) >= 3:
        rets = simple_returns(mv_vals)
        vol = volatility(rets[1:]) if len(rets) > 2 else None
    if len(mv_vals) >= 2:
        cagr_mv = cagr(mv_vals, dates=mv_dates)

    first_sip = sim.invest_dates[0] if sim.invest_dates else None
    last_sip = sim.invest_dates[-1] if sim.invest_dates else None

    contrib_rows = symbol_contribution(sim, prices_by_symbol)
    # Enrich with units_end / price_end for DTO
    contrib_dtos: list[SipSymbolContributionDTO] = []
    for row in contrib_rows:
        sym = str(row["symbol"])
        units = float(sim.units_end.get(sym, 0.0))
        pe: Optional[float] = None
        if sim.as_of is not None:
            pe = prices_by_symbol.get(sym, {}).get(sim.as_of)
        contrib_dtos.append(
            SipSymbolContributionDTO(
                symbol=sym,
                cash_in=float(row["cash_in"]),
                units_end=units,
                price_end=pe,
                market_value_end=float(row["market_value_end"]),
                contribution=float(row["contribution"]),
                weight_end=float(row["weight_end"])
                if row.get("weight_end") is not None
                else None,
            )
        )

    invest_set = set(sim.invest_dates)
    # total_invested_to_date for charting (cumulative contributions)
    cum = 0.0
    amount = cfg.sip_amount
    mv_dtos: list[SipMarketValueDTO] = []
    for p in sim.market_value:
        if p.date in invest_set:
            cum += amount
        # clamp: actual invested cannot exceed total_invested
        invested_to_date = min(cum, sim.total_invested)
        mv_dtos.append(
            SipMarketValueDTO(
                date=p.date,
                market_value=p.market_value,
                total_invested_to_date=invested_to_date,
                has_sip=p.date in invest_set,
            )
        )

    meta = {
        "price_field": price_field,
        "costs_zero": True,
        "data_source": data_source,
        "fractional_units": cfg.fractional_units,
        "currency": cfg.currency,
        "rebalance_mode": cfg.rebalance_mode.value
        if hasattr(cfg.rebalance_mode, "value")
        else str(cfg.rebalance_mode),
        "xirr_day_count": "ACT/365.25",
    }

    return SipRunResult(
        strategy_id=cfg.strategy_id,
        name=cfg.name,
        xirr=sim.xirr,
        data_source=data_source,
        invest_dates=list(sim.invest_dates),
        cashflows=[
            SipCashflowDTO(date=c.date, amount=c.amount, kind=c.kind)
            for c in sim.cashflows
        ],
        market_value=mv_dtos,
        units_end=dict(sim.units_end),
        metrics=SipMetricsDTO(
            total_invested=sim.total_invested,
            final_value=sim.final_value,
            absolute_gain=sim.absolute_gain,
            n_sips=sim.n_sips,
            first_sip=first_sip,
            last_sip=last_sip,
            as_of=sim.as_of,
            max_drawdown=sim.max_drawdown,
            volatility=vol,
            cagr_mv=cagr_mv,
            xirr_status=xirr_status,
            xirr_message=xirr_msg,
            xirr_day_count="ACT/365.25",
        ),
        contribution=contrib_dtos,
        warnings=uniq,
        meta=meta,
    )


def apply_sip_overrides(
    cfg: StrategyConfig,
    *,
    amount: Optional[float] = None,
    day_of_month: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    as_of: Optional[date] = None,
) -> StrategyConfig:
    """Return a copy of ``cfg`` with SIP schedule fields overridden."""
    data = cfg.model_dump(mode="python")
    sip = dict(data.get("sip") or {})
    if amount is not None:
        sip["amount"] = amount
    if day_of_month is not None:
        sip["day_of_month"] = day_of_month
    if start is not None:
        sip["start_date"] = start
    if end is not None:
        sip["end_date"] = end
    if as_of is not None:
        sip["as_of"] = as_of
    data["sip"] = sip
    try:
        return strategy_config_from_dict(data)
    except StrategyConfigError as exc:
        raise SipServiceError(str(exc)) from exc


def run_result_to_response(result: SipRunResult) -> SipBacktestResponse:
    """Map service ``SipRunResult`` → HTTP ``SipBacktestResponse``."""
    m = result.metrics
    meta = result.meta or {}
    assumptions = SipAssumptions(
        primary_metric="xirr",
        sip_day_rule=(
            "fixed calendar day-of-month → next trading day if market closed"
        ),
        costs="zero",
        costs_zero=bool(meta.get("costs_zero", True)),
        price_field=str(meta.get("price_field", "close")),
        xirr_day_count=str(meta.get("xirr_day_count", "ACT/365.25")),
        fractional_units=bool(meta.get("fractional_units", True)),
        currency=str(meta.get("currency", "INR")),
        rebalance_mode=str(meta.get("rebalance_mode", "none")),
        not_v0_rebalance=True,
    )
    return SipBacktestResponse(
        strategy_id=result.strategy_id,
        name=result.name,
        xirr=result.xirr,
        total_invested=m.total_invested,
        final_value=m.final_value,
        max_drawdown=m.max_drawdown,
        absolute_gain=m.absolute_gain,
        n_sips=m.n_sips,
        series=[
            SipSeriesPoint(
                date=p.date,
                market_value=p.market_value,
                total_invested_to_date=p.total_invested_to_date,
                has_sip=p.has_sip,
            )
            for p in result.market_value
        ],
        cashflows=list(result.cashflows),
        data_source=result.data_source,
        assumptions=assumptions,
        warnings=list(result.warnings),
        invest_dates=list(result.invest_dates),
        units_end=dict(result.units_end),
        contribution=list(result.contribution),
        metrics=m,
        notes=result.notes,
    )


class SipService:
    """Load strategy + prices, run pure SIP simulation, return API-shaped DTO."""

    def run(
        self,
        strategy: Union[StrategyConfig, str, Path, dict],
        *,
        price_panel: Optional[PricePanel] = None,
        price_rows: Optional[Sequence[dict]] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        as_of: Optional[date] = None,
    ) -> SipRunResult:
        """Execute a SIP backtest.

        Parameters
        ----------
        strategy:
            ``StrategyConfig``, path to YAML/JSON, or raw dict.
        price_panel:
            Prebuilt panel (unit tests / notebooks). Skips curated I/O.
        price_rows:
            Raw row dicts with symbol/date/close[/source]; built into a panel
            when ``price_panel`` is not provided.
        start / end / as_of:
            Optional overrides of strategy SIP bounds.
        """
        cfg = _to_strategy(strategy)
        sip_start = start or cfg.start_date
        sip_end = end if end is not None else cfg.end_date
        sip_as_of = as_of if as_of is not None else cfg.as_of

        weights, weight_warnings = _resolve_target_weights(cfg, as_of=sip_start)
        symbols = sorted(weights.keys())
        price_field = (
            cfg.price_field.value
            if hasattr(cfg.price_field, "value")
            else str(cfg.price_field)
        )

        load_end = sip_as_of or sip_end
        panel_warnings: list[str] = []

        if price_panel is not None:
            panel = price_panel
        elif price_rows is not None:
            panel = build_price_panel_from_rows(
                price_rows,
                symbols,
                price_field=price_field,
                start=sip_start,
                end=load_end,
            )
        else:
            panel = load_price_panel(
                symbols,
                start=sip_start,
                end=load_end,
                price_field=price_field,
                require_table=True,
            )

        panel_warnings.extend(panel.warnings)

        available = set(panel.by_symbol.keys())
        missing = [s for s in symbols if s not in available]
        if missing:
            if set(missing) == set(symbols):
                raise SipServiceError(
                    "no price history for any strategy symbols: "
                    + ", ".join(symbols)
                )
            weights = normalize_weights(
                {s: w for s, w in weights.items() if s in available}
            )
            panel_warnings.append(
                "weights_renormalized_after_missing_prices: dropped "
                + ", ".join(missing)
            )

        if not panel.sessions:
            raise SipServiceError(
                "price panel has no sessions for strategy symbols in range "
                f"[{sip_start} .. {load_end}]"
            )

        schedule, sched_warnings = sip_invest_dates(
            cfg.day_of_month,
            sip_start,
            sip_end,
            panel.sessions,
        )
        panel_warnings.extend(sched_warnings)

        sim = run_sip_simulation(
            weights,
            panel.by_symbol,
            cfg.sip_amount,
            schedule,
            as_of=sip_as_of,
            trading_dates=panel.sessions,
            mark_daily=True,
        )

        extra = list(weight_warnings) + list(panel_warnings)
        return _sim_to_dto(
            cfg=cfg,
            sim=sim,
            data_source=panel.data_source,
            prices_by_symbol=panel.by_symbol,
            extra_warnings=extra,
            price_field=panel.price_field,
        )

    def run_from_path(self, path: str | Path, **kwargs) -> SipRunResult:
        """Convenience: load strategy file then ``run``."""
        return self.run(path, **kwargs)

    def run_request(
        self,
        body: SipBacktestRequest,
        *,
        strategy_config: Optional[StrategyConfig] = None,
        price_panel: Optional[PricePanel] = None,
        price_rows: Optional[Sequence[dict]] = None,
    ) -> SipBacktestResponse:
        """Execute ``POST /backtests/sip`` body → API response.

        Parameters
        ----------
        body:
            Validated request (strategy_id and/or inline strategy + overrides).
        strategy_config:
            Pre-loaded config when the route already resolved ``strategy_id``.
            When omitted and ``body.strategy_id`` is set, falls through to
            ``body.strategy`` inline only (route should load file-backed configs).
        price_panel / price_rows:
            Optional offline price injection (tests).
        """
        cfg = self._resolve_request_config(body, strategy_config=strategy_config)
        try:
            result = self.run(
                cfg,
                price_panel=price_panel,
                price_rows=price_rows,
                start=body.start,
                end=body.end,
                as_of=body.as_of,
            )
        except CuratedDataUnavailable:
            raise
        except SipServiceError:
            raise
        except StrategyConfigError as exc:
            raise SipServiceError(str(exc)) from exc
        except ValueError as exc:
            raise SipServiceError(str(exc)) from exc
        return run_result_to_response(result)

    def _resolve_request_config(
        self,
        body: SipBacktestRequest,
        *,
        strategy_config: Optional[StrategyConfig] = None,
    ) -> StrategyConfig:
        if strategy_config is not None:
            cfg = strategy_config
        elif body.strategy is not None:
            try:
                cfg = strategy_config_from_dict(body.strategy)
            except StrategyConfigError as exc:
                raise SipServiceError(str(exc)) from exc
        elif body.strategy_id:
            # Caller (route) should pass strategy_config for file-backed ids.
            raise SipServiceError(
                f"strategy_id {body.strategy_id!r} was not resolved to a config"
            )
        else:
            raise SipServiceError("provide strategy_id and/or strategy (inline config)")

        # Apply amount / day_of_month overrides onto the config copy.
        # start/end/as_of are also applied via run() kwargs; fold into config
        # so resolved_weights / schedule bounds stay consistent.
        if any(
            v is not None
            for v in (body.amount, body.day_of_month, body.start, body.end, body.as_of)
        ):
            cfg = apply_sip_overrides(
                cfg,
                amount=body.amount,
                day_of_month=body.day_of_month,
                start=body.start,
                end=body.end,
                as_of=body.as_of,
            )
        return cfg
