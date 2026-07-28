"""Upstox historical price integration.

Credentials: ``UPSTOX_ACCESS_TOKEN`` (or ``UPSTOX_API_KEY``) in the environment.
Never commit secrets. Sample data remains the default when credentials are absent.
"""

from smallcase_finance.integrations.upstox.client import UpstoxClient, UpstoxError
from smallcase_finance.integrations.upstox.sync import SyncResult, resolve_lookback, sync_prices

__all__ = [
    "UpstoxClient",
    "UpstoxError",
    "SyncResult",
    "resolve_lookback",
    "sync_prices",
]
