"""Portfolio of record: Kite equity holdings refresh + read."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from smallcase_finance.config import (
    DEFAULT_CURRENCY,
    kite_app_configured,
    kite_session_configured,
)
from smallcase_finance.data_access import portfolio as portfolio_da
from smallcase_finance.integrations.kite.auth import KiteAuthError, kite_login_url
from smallcase_finance.integrations.kite.client import KiteClient, KiteError
from smallcase_finance.schemas.portfolio import (
    PortfolioHoldingItem,
    PortfolioResponse,
    PortfolioStatusResponse,
    PortfolioSymbolsResponse,
)


class PortfolioServiceError(Exception):
    def __init__(self, message: str, *, error_code: str = "PORTFOLIO_ERROR", http_status: int = 400):
        super().__init__(message)
        self.error_code = error_code
        self.http_status = http_status
        self.message = message


class PortfolioService:
    def __init__(
        self,
        *,
        curated_root: Path | None = None,
        kite_client: KiteClient | None = None,
    ) -> None:
        self.curated_root = curated_root
        self._kite = kite_client

    def status(self) -> PortfolioStatusResponse:
        app_ok = kite_app_configured()
        session_ok = kite_session_configured()
        login: Optional[str] = None
        if app_ok and not session_ok:
            try:
                login = kite_login_url()
            except KiteAuthError:
                login = None

        snap = portfolio_da.read_latest_snapshot(curated_root=self.curated_root)
        has = snap is not None
        total = None
        count = 0
        synced = None
        if snap:
            rows = snap["rows"]
            count = len(rows)
            vals = [r.get("value") for r in rows if r.get("value") is not None]
            total = float(sum(vals)) if vals else None
            synced = snap.get("synced_at")

        if not app_ok:
            msg = "Set KITE_API_KEY and KITE_API_SECRET, then complete Kite login."
        elif not session_ok:
            msg = "Kite app configured; complete login for an access token, then Refresh."
        elif not has:
            msg = "Session present. Refresh holdings to create a snapshot."
        else:
            msg = "OK"

        return PortfolioStatusResponse(
            kite_app_configured=app_ok,
            kite_session_configured=session_ok,
            login_url=login,
            has_snapshot=has,
            latest_synced_at=synced,
            position_count=count,
            total_value=total,
            currency=DEFAULT_CURRENCY,
            message=msg,
        )

    def latest(self) -> PortfolioResponse:
        snap = portfolio_da.read_latest_snapshot(curated_root=self.curated_root)
        if not snap:
            raise PortfolioServiceError(
                "No portfolio snapshot. POST /portfolio/refresh first.",
                error_code="NO_SNAPSHOT",
                http_status=404,
            )
        return self._to_response(snap)

    def symbols(self) -> PortfolioSymbolsResponse:
        try:
            res = self.latest()
        except PortfolioServiceError:
            return PortfolioSymbolsResponse(symbols=[], synced_at=None)
        syms = sorted({h.symbol for h in res.holdings})
        return PortfolioSymbolsResponse(symbols=syms, synced_at=res.synced_at)

    def refresh(self) -> PortfolioResponse:
        if not kite_session_configured() and self._kite is None:
            raise PortfolioServiceError(
                "Kite session not configured (KITE_API_KEY + KITE_ACCESS_TOKEN).",
                error_code="KITE_SESSION_MISSING",
                http_status=503,
            )

        client = self._kite or KiteClient()
        try:
            holdings = client.get_holdings()
            # Optional raw dump of serializable shape
            raw_payload = [
                {
                    "tradingsymbol": h.tradingsymbol,
                    "exchange": h.exchange,
                    "quantity": h.quantity,
                    "average_price": h.average_price,
                    "last_price": h.last_price,
                    "pnl": h.pnl,
                    "product": h.product,
                    "isin": h.isin,
                    "instrument_token": h.instrument_token,
                }
                for h in holdings
            ]
            try:
                portfolio_da.write_raw_kite_drop(raw_payload)
            except Exception:
                pass  # raw archive is best-effort

            sid = f"kite_{uuid4().hex[:12]}"
            when = datetime.now(timezone.utc)
            rows = portfolio_da.holdings_to_rows(
                holdings, snapshot_id=sid, synced_at=when, source="kite"
            )
            portfolio_da.write_snapshot_rows(rows, curated_root=self.curated_root)
            snap = portfolio_da.read_latest_snapshot(curated_root=self.curated_root)
            if not snap:
                # construct from rows if read failed
                snap = {
                    "snapshot_id": sid,
                    "synced_at": when,
                    "source": "kite",
                    "rows": rows,
                }
            return self._to_response(snap)
        except KiteError as exc:
            msg = str(exc)
            code = "KITE_AUTH_FAILED" if "401" in msg or "403" in msg else "KITE_UPSTREAM"
            status = 401 if code == "KITE_AUTH_FAILED" else 502
            if "not configured" in msg.lower():
                code, status = "KITE_SESSION_MISSING", 503
            raise PortfolioServiceError(msg, error_code=code, http_status=status) from exc

    def _to_response(self, snap: dict[str, Any]) -> PortfolioResponse:
        rows = snap["rows"]
        symbols = [str(r.get("symbol") or "").upper() for r in rows]
        sectors = portfolio_da.sector_lookup(symbols)
        items: list[PortfolioHoldingItem] = []
        total = 0.0
        has_value = False
        for r in rows:
            val = r.get("value")
            if val is not None:
                total += float(val)
                has_value = True
            sym = str(r.get("symbol") or "").upper()
            items.append(
                PortfolioHoldingItem(
                    symbol=sym,
                    exchange=str(r.get("exchange") or ""),
                    quantity=float(r.get("quantity") or 0),
                    average_price=r.get("average_price"),
                    last_price=r.get("last_price"),
                    value=float(val) if val is not None else None,
                    weight=float(r["weight"]) if r.get("weight") is not None else None,
                    pnl=r.get("pnl"),
                    product=r.get("product"),
                    isin=r.get("isin"),
                    instrument_token=r.get("instrument_token"),
                    sector=sectors.get(sym),
                )
            )
        items.sort(key=lambda x: (-(x.value or 0), x.symbol))
        synced = snap.get("synced_at") or datetime.now(timezone.utc)
        if isinstance(synced, datetime) and synced.tzinfo is None:
            synced = synced.replace(tzinfo=timezone.utc)
        return PortfolioResponse(
            snapshot_id=str(snap.get("snapshot_id") or "unknown"),
            synced_at=synced,
            source=str(snap.get("source") or "kite"),
            currency=DEFAULT_CURRENCY,
            total_value=total if has_value else None,
            position_count=len(items),
            holdings=items,
            warnings=[],
        )
