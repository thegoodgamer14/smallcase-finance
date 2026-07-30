"""Decision Lab orchestration: candidate SIP + optional benchmark + weight gap."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from smallcase_finance.config import DEFAULT_BENCHMARK_SYMBOL, STRICT_MARKET_DATA
from smallcase_finance.data_access.price_panel import (
    classify_data_source,
    list_curated_symbols,
    load_price_panel,
)
from smallcase_finance.data_access.exceptions import CuratedDataUnavailable
from smallcase_finance.schemas.decision import (
    CoverageSummary,
    DecisionLegResult,
    DecisionRunRequest,
    DecisionRunResponse,
    DecisionSeriesPoint,
    PriceCoverageResponse,
    SymbolCoverage,
    WeightGapRow,
)
from smallcase_finance.services.portfolio_service import (
    PortfolioService,
    PortfolioServiceError,
)
from smallcase_finance.services.sip_service import SipService, SipServiceError
from smallcase_finance.strategies.models import (
    AllocationMode,
    BasketConstituent,
    InlineBasket,
    SIPConfig,
    StrategyConfig,
)


class DecisionServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str = "DECISION_ERROR",
        http_status: int = 400,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.details = details or {}


def _downsample_series(
    points: Sequence[DecisionSeriesPoint],
    max_points: int = 400,
) -> list[DecisionSeriesPoint]:
    if len(points) <= max_points:
        return list(points)
    step = max(1, len(points) // max_points)
    out = list(points[::step])
    if points and out[-1].date != points[-1].date:
        out.append(points[-1])
    return out


class DecisionService:
    def __init__(
        self,
        *,
        sip_service: SipService | None = None,
        portfolio_service: PortfolioService | None = None,
    ) -> None:
        self.sip = sip_service or SipService()
        self.portfolio = portfolio_service or PortfolioService()

    def price_coverage(self, symbols: Sequence[str]) -> PriceCoverageResponse:
        syms = [s.strip().upper() for s in symbols if s and s.strip()]
        if not syms:
            return PriceCoverageResponse(data_source="unknown", symbols=[])

        curated = set(list_curated_symbols())
        try:
            panel = load_price_panel(syms)
        except CuratedDataUnavailable:
            return PriceCoverageResponse(
                data_source="unknown",
                symbols=[
                    SymbolCoverage(symbol=s, has_prices=s in curated) for s in syms
                ],
            )
        except Exception:
            return PriceCoverageResponse(
                data_source="unknown",
                symbols=[
                    SymbolCoverage(symbol=s, has_prices=s in curated) for s in syms
                ],
            )

        out: list[SymbolCoverage] = []
        for sym in syms:
            series = panel.by_symbol.get(sym) or {}
            if series:
                dates = sorted(series.keys())
                out.append(
                    SymbolCoverage(
                        symbol=sym,
                        has_prices=True,
                        start=dates[0],
                        end=dates[-1],
                    )
                )
            else:
                out.append(
                    SymbolCoverage(symbol=sym, has_prices=False, start=None, end=None)
                )
        data_source = panel.data_source or classify_data_source(panel.sources or [])
        return PriceCoverageResponse(data_source=data_source, symbols=out)

    def run(self, req: DecisionRunRequest) -> DecisionRunResponse:
        strict = (
            STRICT_MARKET_DATA
            if req.strict_market_data is None
            else bool(req.strict_market_data)
        )
        bench_sym = (
            (req.benchmark_symbol or DEFAULT_BENCHMARK_SYMBOL).strip().upper()
        )
        basket_syms = [c.symbol for c in req.basket.constituents]
        need = list(basket_syms)
        if req.include_benchmark and bench_sym:
            need.append(bench_sym)

        cov = self.price_coverage(need)
        missing = [s.symbol for s in cov.symbols if not s.has_prices and s.symbol in basket_syms]
        bench_row = next((s for s in cov.symbols if s.symbol == bench_sym), None)
        bench_ok = bool(bench_row and bench_row.has_prices) if req.include_benchmark else True

        starts = [s.start for s in cov.symbols if s.has_prices and s.start]
        ends = [s.end for s in cov.symbols if s.has_prices and s.end]
        coverage = CoverageSummary(
            basket_symbols=len(basket_syms),
            basket_with_prices=len(basket_syms) - len(missing),
            benchmark_ok=bench_ok if req.include_benchmark else False,
            missing_symbols=missing
            + ([bench_sym] if req.include_benchmark and not bench_ok else []),
            price_start=min(starts) if starts else None,
            price_end=max(ends) if ends else None,
        )

        warnings: list[str] = []
        if missing:
            warnings.append(
                "Missing curated prices for: "
                + ", ".join(missing)
                + ". Sync Upstox for those symbols (make sync-upstox) or remove them."
            )
        if cov.data_source == "sample":
            warnings.append(
                "Demo/sample prices — do not use these results to size real positions."
            )
        if req.include_benchmark and not bench_ok:
            warnings.append(
                f"Benchmark {bench_sym} has no curated prices; benchmark leg skipped."
            )

        if strict:
            if cov.data_source == "sample":
                raise DecisionServiceError(
                    "strict_market_data: sample prices are not allowed for decision runs.",
                    error_code="INSUFFICIENT_PRICES",
                    http_status=422,
                    details={"data_source": cov.data_source, "missing": missing},
                )
            if missing:
                raise DecisionServiceError(
                    "strict_market_data: incomplete basket price coverage.",
                    error_code="INSUFFICIENT_PRICES",
                    http_status=422,
                    details={"missing": missing},
                )

        # Drop missing symbols from run if not strict (partial basket)
        run_constituents = [
            c
            for c in req.basket.constituents
            if c.symbol not in missing
        ]
        if not run_constituents:
            raise DecisionServiceError(
                "No basket symbols have curated prices.",
                error_code="INSUFFICIENT_PRICES",
                http_status=422,
                details={"missing": missing},
            )
        if len(run_constituents) < len(req.basket.constituents):
            warnings.append(
                f"Running partial basket: {len(run_constituents)}/"
                f"{len(req.basket.constituents)} symbols with prices."
            )

        cfg = self._build_strategy(req, run_constituents)
        try:
            candidate_result = self.sip.run(cfg)
        except SipServiceError as exc:
            raise DecisionServiceError(
                str(exc),
                error_code="INVALID_BASKET",
                http_status=422,
            ) from exc
        except CuratedDataUnavailable as exc:
            raise DecisionServiceError(
                str(exc),
                error_code="CURATED_UNAVAILABLE",
                http_status=503,
            ) from exc

        candidate = self._leg_from_sip(candidate_result)
        data_source = candidate.data_source
        warnings.extend(candidate.warnings)

        benchmark_leg: Optional[DecisionLegResult] = None
        delta: Optional[float] = None
        if req.include_benchmark and bench_ok:
            bcfg = self._build_benchmark_strategy(req, bench_sym)
            try:
                bres = self.sip.run(bcfg)
                benchmark_leg = self._leg_from_sip(bres, symbol=bench_sym)
                if candidate.xirr is not None and benchmark_leg.xirr is not None:
                    delta = float(candidate.xirr) - float(benchmark_leg.xirr)
                if benchmark_leg.data_source != data_source:
                    data_source = "mixed"
            except (SipServiceError, CuratedDataUnavailable) as exc:
                warnings.append(f"Benchmark SIP failed: {exc}")

        weight_gap: list[WeightGapRow] = []
        if req.include_weight_gap:
            weight_gap = self._weight_gap(req)

        return DecisionRunResponse(
            run_id=f"dec_{uuid4().hex[:12]}",
            data_source=data_source,
            coverage=coverage,
            warnings=list(dict.fromkeys(warnings)),
            candidate=candidate,
            benchmark=benchmark_leg,
            delta_xirr=delta,
            weight_gap=weight_gap,
        )

    def _build_strategy(
        self,
        req: DecisionRunRequest,
        constituents: list,
    ) -> StrategyConfig:
        mode = (
            AllocationMode.equal_weight
            if req.basket.mode == "equal_weight"
            else AllocationMode.custom_weights
        )
        # Re-normalize weights if partial basket under custom mode
        if mode == AllocationMode.custom_weights:
            total = sum(float(c.target_weight or 0) for c in constituents)
            bcs = [
                BasketConstituent(
                    symbol=c.symbol,
                    target_weight=(float(c.target_weight or 0) / total) if total else None,
                )
                for c in constituents
            ]
        else:
            bcs = [
                BasketConstituent(symbol=c.symbol, target_weight=None)
                for c in constituents
            ]

        return StrategyConfig(
            strategy_id="decision-candidate",
            name="Decision Lab candidate",
            basket=InlineBasket(kind="inline", constituents=bcs),
            allocation_mode=mode,
            sip=SIPConfig(
                amount=req.sip.amount,
                day_of_month=req.sip.day_of_month,
                start_date=req.sip.start_date,
                end_date=req.sip.end_date,
            ),
        )

    def _build_benchmark_strategy(
        self, req: DecisionRunRequest, symbol: str
    ) -> StrategyConfig:
        return StrategyConfig(
            strategy_id="decision-benchmark",
            name=f"Benchmark {symbol}",
            basket=InlineBasket(
                kind="inline",
                constituents=[
                    BasketConstituent(symbol=symbol, target_weight=1.0),
                ],
            ),
            allocation_mode=AllocationMode.custom_weights,
            sip=SIPConfig(
                amount=req.sip.amount,
                day_of_month=req.sip.day_of_month,
                start_date=req.sip.start_date,
                end_date=req.sip.end_date,
            ),
        )

    def _leg_from_sip(self, result, *, symbol: str | None = None) -> DecisionLegResult:
        series = [
            DecisionSeriesPoint(
                date=p.date,
                market_value=p.market_value,
                invested_cum=p.total_invested_to_date,
            )
            for p in result.market_value
        ]
        series = _downsample_series(series)
        return DecisionLegResult(
            symbol=symbol,
            xirr=result.xirr,
            total_invested=result.metrics.total_invested,
            final_value=result.metrics.final_value,
            max_drawdown=result.metrics.max_drawdown,
            series=series,
            cashflows_summary={
                "n_contributions": result.metrics.n_sips,
                "n_cashflows": len(result.cashflows),
            },
            data_source=result.data_source,
            warnings=list(result.warnings or []),
        )

    def _weight_gap(self, req: DecisionRunRequest) -> list[WeightGapRow]:
        try:
            book = self.portfolio.latest()
        except PortfolioServiceError:
            return []

        port_w: dict[str, float] = {}
        for h in book.holdings:
            port_w[h.symbol] = port_w.get(h.symbol, 0.0) + float(h.weight or 0.0)

        if req.basket.mode == "equal_weight":
            n = len(req.basket.constituents)
            targets = {c.symbol: 1.0 / n for c in req.basket.constituents}
        else:
            targets = {
                c.symbol: float(c.target_weight or 0.0) for c in req.basket.constituents
            }

        symbols = sorted(set(port_w) | set(targets))
        total_value = book.total_value
        rows: list[WeightGapRow] = []
        for sym in symbols:
            tw = targets.get(sym, 0.0)
            pw = port_w.get(sym, 0.0)
            dw = tw - pw
            # Only show symbols in target or with material portfolio weight
            if tw == 0 and abs(pw) < 1e-9:
                continue
            if tw == 0 and sym not in targets:
                # optional: skip pure portfolio names not in basket
                if abs(pw) < 1e-6:
                    continue
            approx = None
            if total_value is not None:
                approx = dw * float(total_value)
            rows.append(
                WeightGapRow(
                    symbol=sym,
                    portfolio_weight=pw,
                    target_weight=tw,
                    delta_weight=dw,
                    approx_value_delta=approx,
                )
            )
        # Prefer names in the candidate basket first
        rows.sort(key=lambda r: (0 if r.symbol in targets else 1, -abs(r.delta_weight)))
        return rows
