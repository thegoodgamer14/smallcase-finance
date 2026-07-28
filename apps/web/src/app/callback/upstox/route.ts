import { NextRequest, NextResponse } from "next/server";

/**
 * Upstox OAuth redirect target (Hobby-safe on Vercel).
 *
 * Register exactly (production):
 *   https://<project>.vercel.app/callback/upstox
 *
 * Env (Vercel Project → Settings → Environment Variables):
 *   UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI
 *
 * Prefer portal Generate for tokens; this route is the optional code flow.
 * Never log client_secret or access_token.
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function htmlPage(title: string, body: string, status = 200): NextResponse {
  const doc = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto;
           padding: 0 1rem; line-height: 1.5; color: #0f172a; }
    code, pre { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px;
                word-break: break-all; }
    pre { padding: 0.75rem; overflow-x: auto; }
    .warn { color: #b45309; }
    .ok { color: #047857; }
    .err { color: #b91c1c; }
  </style>
</head>
<body>
  <h1>${escapeHtml(title)}</h1>
  ${body}
</body>
</html>`;
  return new NextResponse(doc, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");
  const code = searchParams.get("code");

  if (error) {
    const detail = errorDescription || error;
    return htmlPage(
      "Upstox OAuth failed",
      `<p class="err">Provider error: <code>${escapeHtml(detail)}</code></p>`,
      400,
    );
  }

  if (!code) {
    return htmlPage(
      "Upstox callback",
      `<p>No <code>code</code> query param. Open the Upstox authorize URL, or use
       Developer Apps → <strong>Generate</strong> for a portal token.</p>
       <p>See <code>docs/deploy/vercel.md</code> and <code>docs/integrations/upstox.md</code>.</p>`,
      400,
    );
  }

  const clientId = process.env.UPSTOX_API_KEY?.trim() ?? "";
  const clientSecret = process.env.UPSTOX_API_SECRET?.trim() ?? "";
  const redirectUri = process.env.UPSTOX_REDIRECT_URI?.trim() ?? "";
  const apiBase = (
    process.env.UPSTOX_API_BASE?.trim() || "https://api.upstox.com/v2"
  ).replace(/\/$/, "");

  if (!clientId || !clientSecret || !redirectUri) {
    return htmlPage(
      "Upstox callback — missing server env",
      `<p class="err">Set <code>UPSTOX_API_KEY</code>, <code>UPSTOX_API_SECRET</code>,
       and <code>UPSTOX_REDIRECT_URI</code> in the Vercel project Environment Variables,
       then redeploy and retry login.</p>
       <p>Redirect URI must match the developer portal <em>exactly</em>.</p>`,
      500,
    );
  }

  const body = new URLSearchParams({
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: redirectUri,
    grant_type: "authorization_code",
  });

  let resp: Response;
  try {
    resp = await fetch(`${apiBase}/login/authorization/token`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
      cache: "no-store",
    });
  } catch {
    return htmlPage(
      "Upstox token exchange failed",
      `<p class="err">Network error talking to Upstox.</p>`,
      502,
    );
  }

  if (!resp.ok) {
    const snippet = (await resp.text()).slice(0, 200);
    return htmlPage(
      "Upstox token exchange failed",
      `<p class="err">HTTP ${resp.status} from Upstox token endpoint.</p>
       <pre>${escapeHtml(snippet)}</pre>
       <p>Check that redirect_uri matches the portal and the code was not reused.</p>`,
      502,
    );
  }

  let payload: { access_token?: unknown };
  try {
    payload = (await resp.json()) as { access_token?: unknown };
  } catch {
    return htmlPage(
      "Upstox token exchange failed",
      `<p class="err">Token response was not JSON.</p>`,
      502,
    );
  }

  const accessToken = payload.access_token;
  if (typeof accessToken !== "string" || !accessToken) {
    return htmlPage(
      "Upstox token exchange failed",
      `<p class="err">Response JSON had no <code>access_token</code>.</p>`,
      502,
    );
  }

  return htmlPage(
    "Upstox access token ready",
    `
<p class="ok">Authorization code exchanged successfully.</p>
<p class="warn"><strong>Copy this token now</strong> into local <code>.env</code> as
<code>UPSTOX_ACCESS_TOKEN</code> (for <code>make sync-upstox</code> on your machine).
Tokens expire ~3:30&nbsp;AM IST the following day.</p>
<pre>${escapeHtml(accessToken)}</pre>
<p>Never commit this value. Prefer regenerating via the portal when in doubt.</p>
<p><a href="/">Back to app</a></p>
`,
  );
}
