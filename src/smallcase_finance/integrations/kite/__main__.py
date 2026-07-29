"""CLI: Kite Connect login helpers and holdings smoke test.

Examples::

    python -m smallcase_finance.integrations.kite login
    python -m smallcase_finance.integrations.kite exchange --request-token RT...
    python -m smallcase_finance.integrations.kite holdings
    python -m smallcase_finance.integrations.kite profile
"""

from __future__ import annotations

import argparse
import sys

from smallcase_finance.config import (
    KITE_REDIRECT_URI,
    kite_app_configured,
    kite_session_configured,
)
from smallcase_finance.integrations.kite.auth import (
    KiteAuthError,
    exchange_request_token,
    kite_login_url,
)
from smallcase_finance.integrations.kite.client import KiteClient, KiteError


def cmd_login(_: argparse.Namespace) -> int:
    if not kite_app_configured():
        print(
            "Set KITE_API_KEY and KITE_API_SECRET in .env first.",
            file=sys.stderr,
        )
        return 1
    url = kite_login_url()
    print("Open this URL in your browser (Zerodha login + 2FA):")
    print(url)
    print()
    print(f"Registered redirect should match: {KITE_REDIRECT_URI}")
    print(
        "After redirect, copy request_token from the URL query, then run:\n"
        "  make kite-exchange REQUEST_TOKEN=...\n"
        "or:\n"
        "  python -m smallcase_finance.integrations.kite exchange --request-token ..."
    )
    return 0


def cmd_exchange(args: argparse.Namespace) -> int:
    try:
        session = exchange_request_token(args.request_token)
    except KiteAuthError as exc:
        print(f"Exchange failed: {exc}", file=sys.stderr)
        return 1
    print("Token exchange OK.")
    if session.user_id:
        print(f"user_id: {session.user_id}")
    if session.user_name:
        print(f"user_name: {session.user_name}")
    if session.login_time:
        print(f"login_time: {session.login_time}")
    print()
    print("Copy into local .env (never commit):")
    print(f"KITE_ACCESS_TOKEN={session.access_token}")
    print()
    print(
        "Token typically expires ~6 AM IST next day. Re-run login when API returns 403."
    )
    return 0


def cmd_profile(_: argparse.Namespace) -> int:
    if not kite_session_configured():
        print(
            "Need KITE_API_KEY + KITE_ACCESS_TOKEN. Run: make kite-login",
            file=sys.stderr,
        )
        return 1
    try:
        with KiteClient() as client:
            profile = client.get_profile()
    except KiteError as exc:
        print(f"Profile failed: {exc}", file=sys.stderr)
        return 1
    # Safe fields only
    for k in ("user_id", "user_name", "email", "broker", "user_type"):
        if k in profile:
            print(f"{k}: {profile[k]}")
    return 0


def cmd_holdings(_: argparse.Namespace) -> int:
    if not kite_session_configured():
        print(
            "Need KITE_API_KEY + KITE_ACCESS_TOKEN. Run: make kite-login",
            file=sys.stderr,
        )
        return 1
    try:
        with KiteClient() as client:
            holdings = client.get_holdings()
    except KiteError as exc:
        print(f"Holdings failed: {exc}", file=sys.stderr)
        return 1
    print(f"holdings_count: {len(holdings)}")
    # Show a short sample (symbols only) — not a full portfolio dump for logs
    for h in holdings[:25]:
        print(
            f"  {h.exchange}:{h.tradingsymbol} qty={h.quantity} "
            f"avg={h.average_price} ltp={h.last_price}"
        )
    if len(holdings) > 25:
        print(f"  … +{len(holdings) - 25} more")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m smallcase_finance.integrations.kite",
        description="Kite Connect login helpers and read-only holdings smoke test",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Print Kite Connect login URL")
    p_login.set_defaults(func=cmd_login)

    p_ex = sub.add_parser(
        "exchange",
        help="Exchange request_token for access_token (prints env line)",
    )
    p_ex.add_argument(
        "--request-token",
        required=True,
        help="One-time request_token from redirect URL query",
    )
    p_ex.set_defaults(func=cmd_exchange)

    p_prof = sub.add_parser("profile", help="GET /user/profile (needs access token)")
    p_prof.set_defaults(func=cmd_profile)

    p_hold = sub.add_parser(
        "holdings", help="GET /portfolio/holdings (needs access token)"
    )
    p_hold.set_defaults(func=cmd_holdings)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
