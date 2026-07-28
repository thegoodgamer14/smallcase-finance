"""Alternate ASGI entry (same app as ``smallcase_finance.main``).

Run::

    uvicorn smallcase_finance.api.main:app --reload --app-dir src
"""

from __future__ import annotations

from smallcase_finance.main import app, create_app

__all__ = ["app", "create_app"]
