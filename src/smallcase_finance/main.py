"""ASGI entrypoint.

Run from repo root (after ``pip install -e .``)::

    uvicorn smallcase_finance.main:app --reload --app-dir src

Or with package on PYTHONPATH::

    uvicorn smallcase_finance.main:app --reload

OpenAPI: http://127.0.0.1:8000/docs

Render free tier: see docs/deploy/render.md
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smallcase_finance import __version__
from smallcase_finance.api.routes import (
    backtest,
    health,
    integrations,
    oauth,
    sip_backtest,
    smallcases,
    strategies,
)

# Local Next.js defaults. Extra origins via CORS_ORIGINS (comma-separated), e.g.
# https://your-app.vercel.app for a free frontend deploy.
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _cors_origins() -> list[str]:
    extra = os.environ.get("CORS_ORIGINS", "").strip()
    if not extra:
        return list(_DEFAULT_CORS_ORIGINS)
    origins = [o.strip() for o in extra.split(",") if o.strip()]
    # Always keep local UI origins for hybrid local frontend + remote API.
    merged = list(dict.fromkeys(_DEFAULT_CORS_ORIGINS + origins))
    return merged


def create_app() -> FastAPI:
    """Build the FastAPI application with v0 + SIP Lab routers."""
    app = FastAPI(
        title="Smallcase Finance API",
        version=__version__,
        description=(
            "Local-first smallcase composition, NAV, performance, metrics, "
            "and SIP Lab (monthly SIP + XIRR). "
            "Contracts: docs/architecture/backend.md · docs/api.md. "
            "Deploy: docs/deploy/render.md."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(smallcases.router)
    app.include_router(backtest.router)
    app.include_router(strategies.router)
    app.include_router(sip_backtest.router)
    app.include_router(integrations.router)
    app.include_router(oauth.router)

    return app


app = create_app()
