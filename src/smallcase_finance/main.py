"""ASGI entrypoint.

Run from repo root (after ``pip install -e .``)::

    uvicorn smallcase_finance.main:app --reload --app-dir src

Or with package on PYTHONPATH::

    uvicorn smallcase_finance.main:app --reload

OpenAPI: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smallcase_finance import __version__
from smallcase_finance.api.routes import backtest, health, integrations, smallcases

# Local Next.js (and common dev ports). No credentials in v0.
_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def create_app() -> FastAPI:
    """Build the FastAPI application with v0 routers."""
    app = FastAPI(
        title="Smallcase Finance API",
        version=__version__,
        description=(
            "Local-first smallcase composition, NAV, performance, and metrics. "
            "Contracts: docs/architecture/backend.md §6 · docs/api.md."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(smallcases.router)
    app.include_router(backtest.router)
    app.include_router(integrations.router)

    return app


app = create_app()
