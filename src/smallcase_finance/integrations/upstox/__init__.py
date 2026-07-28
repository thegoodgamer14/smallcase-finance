"""Upstox historical price integration (sole market-data provider).

Credentials (portal names → env):
- ``UPSTOX_ACCESS_TOKEN`` — Bearer for historical candles (**required** for live prices)
- ``UPSTOX_API_KEY`` / ``UPSTOX_API_SECRET`` — OAuth client_id / client_secret (token exchange)
- ``UPSTOX_REDIRECT_URI`` — OAuth only

Never commit secrets. Sample data is demo-only when the access token is absent.
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
