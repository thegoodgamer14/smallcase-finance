"""OAuth redirect callbacks (personal free-tier deploy / local helper).

Upstox and Kite redirect here after login. The preferred founder path remains
portal **Generate** token → env; these routes support the authorization-code
flow when a public HTTPS redirect is registered (e.g. Render).

Never log client_secret, access_token, or request_token values.
"""

from __future__ import annotations

import html
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from smallcase_finance.config import (
    UPSTOX_API_BASE,
    UPSTOX_API_KEY,
    UPSTOX_API_SECRET,
    UPSTOX_REDIRECT_URI,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])


def _page(title: str, body: str, *, status_code: int = 200) -> HTMLResponse:
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto;
           padding: 0 1rem; line-height: 1.5; color: #0f172a; }}
    code, pre {{ background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px;
                 word-break: break-all; }}
    pre {{ padding: 0.75rem; overflow-x: auto; }}
    .warn {{ color: #b45309; }}
    .ok {{ color: #047857; }}
    .err {{ color: #b91c1c; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  {body}
</body>
</html>"""
    return HTMLResponse(content=doc, status_code=status_code)


@router.get("/callback/upstox", response_class=HTMLResponse)
def upstox_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
) -> HTMLResponse:
    """Receive Upstox OAuth ``code`` and exchange it for an access token.

    Register this exact path as the app Redirect URI, e.g.::

        https://<your-service>.onrender.com/callback/upstox

    Env required for exchange: ``UPSTOX_API_KEY``, ``UPSTOX_API_SECRET``,
    ``UPSTOX_REDIRECT_URI`` (must match the portal value character-for-character).
    """
    _ = state  # optional continuity param; unused in v0

    if error:
        detail = error_description or error
        logger.warning("Upstox OAuth error callback: %s", error)
        return _page(
            "Upstox OAuth failed",
            f'<p class="err">Provider error: <code>{html.escape(str(detail))}</code></p>',
            status_code=400,
        )

    if not code:
        return _page(
            "Upstox callback",
            "<p>No <code>code</code> query param. Open the Upstox authorize URL, "
            "or use Developer Apps → <strong>Generate</strong> for a portal token.</p>"
            "<p>See <code>docs/integrations/upstox.md</code> and "
            "<code>docs/deploy/render.md</code>.</p>",
            status_code=400,
        )

    if not (UPSTOX_API_KEY and UPSTOX_API_SECRET and UPSTOX_REDIRECT_URI):
        return _page(
            "Upstox callback — missing server env",
            "<p class='err'>Set <code>UPSTOX_API_KEY</code>, "
            "<code>UPSTOX_API_SECRET</code>, and <code>UPSTOX_REDIRECT_URI</code> "
            "on the host (Render Environment), then retry login.</p>"
            "<p>Redirect URI must match the developer portal <em>exactly</em>.</p>",
            status_code=500,
        )

    token_url = f"{UPSTOX_API_BASE}/login/authorization/token"
    form = {
        "code": code,
        "client_id": UPSTOX_API_KEY,
        "client_secret": UPSTOX_API_SECRET,
        "redirect_uri": UPSTOX_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                token_url,
                data=form,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
    except httpx.HTTPError as exc:
        logger.exception("Upstox token exchange transport error")
        return _page(
            "Upstox token exchange failed",
            f'<p class="err">Network error talking to Upstox: '
            f"<code>{html.escape(type(exc).__name__)}</code></p>",
            status_code=502,
        )

    if resp.status_code >= 400:
        # Do not echo secrets; status + short body snippet only
        snippet = (resp.text or "")[:200]
        logger.warning(
            "Upstox token exchange HTTP %s (body length %s)",
            resp.status_code,
            len(resp.text or ""),
        )
        return _page(
            "Upstox token exchange failed",
            f'<p class="err">HTTP {resp.status_code} from Upstox token endpoint.</p>'
            f"<pre>{html.escape(snippet)}</pre>"
            "<p>Check that redirect_uri matches the portal and the code was not reused.</p>",
            status_code=502,
        )

    try:
        payload = resp.json()
    except ValueError:
        return _page(
            "Upstox token exchange failed",
            '<p class="err">Token response was not JSON.</p>',
            status_code=502,
        )

    access_token = payload.get("access_token")
    if not access_token or not isinstance(access_token, str):
        logger.warning("Upstox token response missing access_token")
        return _page(
            "Upstox token exchange failed",
            '<p class="err">Response JSON had no <code>access_token</code>.</p>',
            status_code=502,
        )

    # Personal free-tier helper: show token once for copy into env / Render secrets.
    # Do not persist to disk (ephemeral) and do not log the value.
    safe_token = html.escape(access_token)
    return _page(
        "Upstox access token ready",
        f"""
<p class="ok">Authorization code exchanged successfully.</p>
<p class="warn"><strong>Copy this token now</strong> into Render Environment as
<code>UPSTOX_ACCESS_TOKEN</code> (or local <code>.env</code>), then redeploy or
restart so the API picks it up. Tokens expire ~3:30&nbsp;AM IST the following day.</p>
<pre id="tok">{safe_token}</pre>
<p>Never commit this value. Prefer regenerating via the portal when in doubt.</p>
<p><a href="/integrations/upstox/status">Check Upstox status</a> ·
<a href="/docs">API docs</a> · <a href="/health">Health</a></p>
""",
    )


@router.get("/callback/kite", response_class=HTMLResponse)
def kite_oauth_callback(
    request_token: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
) -> HTMLResponse:
    """Kite Connect redirect: exchange request_token → access_token (personal use).

    Register this exact path on developers.kite.trade, e.g.::

        https://smallcase-sip-lab.vercel.app/callback/kite
        http://127.0.0.1:8000/callback/kite

    Env: ``KITE_API_KEY``, ``KITE_API_SECRET``. Never log tokens.
    """
    from smallcase_finance.integrations.kite.auth import (
        KiteAuthError,
        exchange_request_token,
    )

    _ = action
    if status == "error" or (status and status.lower() == "error"):
        return _page(
            "Kite login cancelled or failed",
            f'<p class="err">status=<code>{html.escape(status or "")}</code></p>',
            status_code=400,
        )

    if not request_token:
        return _page(
            "Kite callback",
            "<p>No <code>request_token</code>. Start with "
            "<code>make kite-login</code> and complete Zerodha login. "
            "See <code>docs/integrations/kite-connect.md</code>.</p>",
            status_code=400,
        )

    try:
        session = exchange_request_token(request_token)
    except KiteAuthError as exc:
        logger.warning("Kite token exchange failed: %s", type(exc).__name__)
        return _page(
            "Kite token exchange failed",
            f'<p class="err">{html.escape(str(exc))}</p>'
            "<p>Check KITE_API_KEY / KITE_API_SECRET and that the request_token "
            "was not reused (single-use, short lifetime).</p>",
            status_code=502,
        )

    safe = html.escape(session.access_token)
    who = html.escape(session.user_name or session.user_id or "ok")
    return _page(
        "Kite access token ready",
        f"""
<p class="ok">Login successful ({who}).</p>
<p class="warn"><strong>Copy into local <code>.env</code></strong> as
<code>KITE_ACCESS_TOKEN</code> (never commit). Expires ~6:00&nbsp;AM IST next day.</p>
<pre>{safe}</pre>
<p>Then: <code>make kite-holdings</code> or
<code>python -m smallcase_finance.integrations.kite holdings</code>.</p>
<p><a href="/integrations/kite/status">Kite status</a> ·
<a href="/docs">API docs</a></p>
""",
    )
