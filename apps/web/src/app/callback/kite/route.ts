import { NextRequest, NextResponse } from "next/server";

/**
 * Kite Connect redirect target (Phase 4 placeholder).
 *
 * Register: https://<project>.vercel.app/callback/kite
 * Token exchange is not implemented in this product version.
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
    code, pre { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px; }
    .ok { color: #047857; }
    .warn { color: #b45309; }
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
  const requestToken = req.nextUrl.searchParams.get("request_token");
  const status = req.nextUrl.searchParams.get("status");

  if (!requestToken) {
    return htmlPage(
      "Kite callback",
      `<p>No <code>request_token</code>. This path is reserved for Phase 4 equity
       holdings import. See <code>docs/integrations/kite-connect.md</code>.</p>
       <p>Register this URL on the Kite developer console so app creation succeeds.</p>`,
      400,
    );
  }

  return htmlPage(
    "Kite request_token received",
    `
<p class="ok">Login redirect reached this app (status=
<code>${escapeHtml(status || "n/a")}</code>).</p>
<p>Token exchange is <strong>not implemented</strong> in this product version.
Copy <code>request_token</code> from the browser address bar only if testing Kite
manually; product wiring is Phase 4 only.</p>
<p class="warn">request_token length: ${requestToken.length} (value not shown).</p>
<p><a href="/">Back to app</a></p>
`,
  );
}
