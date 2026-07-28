"""Integration status and optional local-only Upstox sync trigger."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from smallcase_finance.config import (
    UPSTOX_DEFAULT_YEARS,
    UPSTOX_SYNC_ENABLED,
    upstox_configured,
)
from smallcase_finance.integrations.upstox.sync import resolve_lookback, sync_prices

router = APIRouter(prefix="/integrations", tags=["integrations"])


class UpstoxStatusResponse(BaseModel):
    """Credential status only — never includes tokens or secrets.

    ``configured`` is the sole secret-related field (boolean).
    """

    provider: str = "upstox"
    configured: bool = Field(
        description=(
            "True if UPSTOX_ACCESS_TOKEN is set. "
            "Boolean only — never returns the token value."
        )
    )
    sync_http_enabled: bool = Field(
        description="True only when UPSTOX_SYNC_ENABLED=1 (local footgun guard)"
    )
    default_years: int
    hint: str


class UpstoxSyncRequest(BaseModel):
    years: Optional[int] = Field(default=None, ge=1, le=30)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    symbols: Optional[list[str]] = None
    run_pipeline: bool = True


class UpstoxSyncResponse(BaseModel):
    from_date: date
    to_date: date
    requested_symbols: list[str]
    fetched_symbols: list[str]
    skipped_symbols: list[str]
    warnings: list[str]
    row_count: int
    output_path: Optional[str]
    used_sample_fallback: bool
    message: str


@router.get("/upstox/status", response_model=UpstoxStatusResponse)
def upstox_status() -> UpstoxStatusResponse:
    """Report whether Upstox is configured (boolean only — no secrets)."""
    configured = upstox_configured()
    if configured:
        hint = (
            "Token present. Sync via CLI: "
            "make sync-upstox "
            "or python -m smallcase_finance.integrations.upstox --years 3 --pipeline. "
            "POST /integrations/upstox/sync only when UPSTOX_SYNC_ENABLED=1."
        )
    else:
        hint = (
            "No access token. App uses sample prices (demo only). "
            "Set UPSTOX_ACCESS_TOKEN in .env then make sync-upstox. "
            "See docs/integrations/upstox.md."
        )
    return UpstoxStatusResponse(
        configured=configured,
        sync_http_enabled=UPSTOX_SYNC_ENABLED,
        default_years=UPSTOX_DEFAULT_YEARS,
        hint=hint,
    )


@router.post("/upstox/sync", response_model=UpstoxSyncResponse)
def upstox_sync(body: UpstoxSyncRequest) -> UpstoxSyncResponse:
    """Trigger a price sync (disabled by default).

    Enable only for local demos: ``UPSTOX_SYNC_ENABLED=1``. Prefer the CLI for
    normal use so secrets stay in the shell environment.
    """
    if not UPSTOX_SYNC_ENABLED:
        raise HTTPException(
            status_code=403,
            detail=(
                "HTTP sync disabled. Use CLI "
                "`python -m smallcase_finance.integrations.upstox` "
                "or `make sync-upstox`, "
                "or set UPSTOX_SYNC_ENABLED=1 for local-only API sync."
            ),
        )
    try:
        resolve_lookback(
            years=body.years,
            from_date=body.from_date,
            to_date=body.to_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = sync_prices(
        symbols=body.symbols,
        years=body.years,
        from_date=body.from_date,
        to_date=body.to_date,
        run_pipeline_after=body.run_pipeline,
        allow_sample_fallback=True,
    )
    return UpstoxSyncResponse(
        from_date=result.from_date,
        to_date=result.to_date,
        requested_symbols=result.requested_symbols,
        fetched_symbols=result.fetched_symbols,
        skipped_symbols=result.skipped_symbols,
        warnings=result.warnings,
        row_count=result.row_count,
        output_path=str(result.output_path) if result.output_path else None,
        used_sample_fallback=result.used_sample_fallback,
        message=result.message,
    )


@router.get("/upstox/lookback-preview")
def lookback_preview(
    years: Optional[int] = Query(default=None, ge=1, le=30),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
) -> dict:
    """Resolve a custom lookback window without fetching data."""
    try:
        start, end = resolve_lookback(years=years, from_date=from_date, to_date=to_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "years_arg": years,
        "default_years": UPSTOX_DEFAULT_YEARS,
    }
