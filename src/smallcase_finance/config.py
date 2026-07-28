"""Runtime configuration for the local API and integrations.

Values are intentionally simple for v0 (env overrides, no secrets store).
Never commit real tokens — use ``.env`` (gitignored) or the shell environment.

Upstox portal mapping (see docs/integrations/upstox.md):

| Portal / OAuth name   | Env var                | Role                                      |
|-----------------------|------------------------|-------------------------------------------|
| Access token (Bearer) | ``UPSTOX_ACCESS_TOKEN``| Primary credential for historical candles |
| API Key (client_id)   | ``UPSTOX_API_KEY``     | App id; OAuth authorize + token exchange  |
| API Secret            | ``UPSTOX_API_SECRET``  | client_secret; token exchange only        |
| Redirect URI          | ``UPSTOX_REDIRECT_URI``| OAuth only; must match developer app      |
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: src/smallcase_finance/config.py → parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Soft-load .env for local dev (never overrides real environment variables)
_env_file = _REPO_ROOT / ".env"
if _env_file.is_file():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file, override=False)
    except ImportError:
        pass

DATA_CURATED_ROOT: Path = Path(
    os.environ.get("DATA_CURATED_ROOT", _REPO_ROOT / "data" / "curated")
).expanduser().resolve()

DEFAULT_CURRENCY: str = os.environ.get("DEFAULT_CURRENCY", "INR")
PERIODS_PER_YEAR: int = int(os.environ.get("PERIODS_PER_YEAR", "252"))
DEFAULT_RF: float = float(os.environ.get("DEFAULT_RF", "0.0"))

API_HOST: str = os.environ.get("API_HOST", "127.0.0.1")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))

# ── Upstox historical prices (sole provider) ────────────────────────────────
# Bearer for candle APIs. Do NOT treat API Key as a token alias — portal names
# map cleanly: API Key = client_id, API Secret = client_secret, Access token = Bearer.
UPSTOX_ACCESS_TOKEN: str = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
# Official Upstox API Key (= OAuth client_id). Used for authorize / token exchange only.
UPSTOX_API_KEY: str = os.environ.get("UPSTOX_API_KEY", "").strip()
# Official Upstox API Secret (= OAuth client_secret). Never log or commit.
UPSTOX_API_SECRET: str = os.environ.get("UPSTOX_API_SECRET", "").strip()
# Must match developer app config when using OAuth code flow.
UPSTOX_REDIRECT_URI: str = os.environ.get("UPSTOX_REDIRECT_URI", "").strip()
UPSTOX_API_BASE: str = os.environ.get(
    "UPSTOX_API_BASE", "https://api.upstox.com/v2"
).rstrip("/")
# Default lookback when neither --from/--to nor --years is set
UPSTOX_DEFAULT_YEARS: int = int(os.environ.get("UPSTOX_DEFAULT_YEARS", "3"))
# Local footgun guard for optional HTTP sync endpoint
UPSTOX_SYNC_ENABLED: bool = os.environ.get("UPSTOX_SYNC_ENABLED", "").strip() in {
    "1",
    "true",
    "True",
    "yes",
    "YES",
}


def upstox_configured() -> bool:
    """True when a non-empty access token is present (value is never logged)."""
    return bool(UPSTOX_ACCESS_TOKEN)
