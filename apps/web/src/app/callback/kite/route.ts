import { NextRequest, NextResponse } from "next/server";
import { createHash } from "crypto";

/**
 * Kite Connect OAuth redirect — exchange request_token for access_token.
 *
 * Register: https://smallcase-sip-lab.vercel.app/callback/kite
 * Env on Vercel: KITE_API_KEY, KITE_API_SECRET
 *
 * Official flow: https://kite.trade/docs/connect/v3/user/
 * Never log api_secret / request_token / access_token.
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
  const sp = req.nextUrl.searchParams;
  const status = sp.get("status");
  const requestToken = sp.get("request_token");

  if (status === "error") {
    return htmlPage(
      "Kite login failed",
      `<p class="err">Login was cancelled or failed (status=error).</p>`,
      400,
    );
  }

  if (!requestToken) {
    return htmlPage(
      "Kite callback",
      `<p>No <code>request_token</code>. Start login with
       <code>make kite-login</code> or
       <code>https://kite.zerodha.com/connect/login?v=3&amp;api_key=YOUR_KEY</code>.</p>
       <p>Kite does <strong>not</strong> issue access tokens on the developer console —
       only via this login flow.</p>`,
      400,
    );
  }

  const apiKey = process.env.KITE_API_KEY?.trim() ?? "";
  const apiSecret = process.env.KITE_API_SECRET?.trim() ?? "";
  const apiBase = (
    process.env.KITE_API_BASE?.trim() || "https://api.kite.trade"
  ).replace(/\/$/, "");

  if (!apiKey || !apiSecret) {
    return htmlPage(
      "Missing server env",
      `<p class="err">Set <code>KITE_API_KEY</code> and <code>KITE_API_SECRET</code>
       on Vercel Environment (or run exchange locally with
       <code>make kite-exchange REQUEST_TOKEN=…</code>).</p>`,
      500,
    );
  }

  const checksum = createHash("sha256")
    .update(`${apiKey}${requestToken}${apiSecret}`)
    .digest("hex");

  const body = new URLSearchParams({
    api_key: apiKey,
    request_token: requestToken,
    checksum,
  });

  let resp: Response;
  try {
    resp = await fetch(`${apiBase}/session/token`, {
      method: "POST",
      headers: {
        "X-Kite-Version": "3",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
      cache: "no-store",
    });
  } catch {
    return htmlPage(
      "Kite token exchange failed",
      `<p class="err">Network error talking to Kite.</p>`,
      502,
    );
  }

  if (!resp.ok) {
    const snippet = (await resp.text()).slice(0, 200);
    return htmlPage(
      "Kite token exchange failed",
      `<p class="err">HTTP ${resp.status}</p><pre>${escapeHtml(snippet)}</pre>`,
      502,
    );
  }

  const payload = (await resp.json()) as {
    status?: string;
    message?: string;
    data?: { access_token?: string; user_name?: string; user_id?: string };
  };

  if (payload.status === "error") {
    return htmlPage(
      "Kite token exchange failed",
      `<p class="err">${escapeHtml(payload.message || "rejected")}</p>`,
      502,
    );
  }

  const accessToken = payload.data?.access_token;
  if (typeof accessToken !== "string" || !accessToken) {
    return htmlPage(
      "Kite token exchange failed",
      `<p class="err">Response missing access_token.</p>`,
      502,
    );
  }

  const who = escapeHtml(
    payload.data?.user_name || payload.data?.user_id || "ok",
  );

  return htmlPage(
    "Kite access token ready",
    `
<p class="ok">Login successful (${who}).</p>
<p class="warn"><strong>Copy into local <code>.env</code></strong> as
<code>KITE_ACCESS_TOKEN</code>. Never commit. Expires ~6:00&nbsp;AM IST next day.</p>
<pre>${escapeHtml(accessToken)}</pre>
<p>Then run <code>make kite-holdings</code> locally.</p>
<p><a href="/">Home</a></p>
`,
  );
}
