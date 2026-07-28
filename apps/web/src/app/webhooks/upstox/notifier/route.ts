import { NextRequest, NextResponse } from "next/server";

/**
 * Upstox **notifier webhook** (semi-automated access-token request flow).
 *
 * Register on the developer portal (optional):
 *   https://smallcase-sip-lab.vercel.app/webhooks/upstox/notifier
 *
 * This is **not** the OAuth redirect URI.
 * - Redirect URI (GET /callback/upstox): browser lands with ?code=… after login
 * - Notifier (POST here): Upstox server pushes access_token after you approve
 *   an Access Token Request on your phone / developer apps
 *
 * Prefer portal **Generate** for day-to-day SIP Lab sync; leave notifier blank
 * if you do not use Access Token Request automation.
 *
 * Never log access_token values. Response is plain JSON (Upstox accepts string or JSON).
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function extractAccessToken(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const o = body as Record<string, unknown>;

  // Common shapes: flat or nested under data
  if (typeof o.access_token === "string" && o.access_token) {
    return o.access_token;
  }
  const data = o.data;
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.access_token === "string" && d.access_token) {
      return d.access_token;
    }
  }
  return null;
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    // Some webhooks send form-encoded; try text and JSON-parse if possible
    try {
      const text = await req.text();
      body = text ? JSON.parse(text) : null;
    } catch {
      return NextResponse.json(
        { ok: false, error: "expected JSON body" },
        { status: 400 },
      );
    }
  }

  const accessToken = extractAccessToken(body);
  if (!accessToken) {
    // Still 200 so Upstox does not retry forever on shape changes we don't understand.
    // Operator can check Vercel logs if needed (we do not log the token).
    return NextResponse.json({
      ok: false,
      received: true,
      message: "No access_token field found in body",
    });
  }

  // Personal free-tier helper: return token once in the HTTP response body so
  // you can inspect the webhook delivery in Upstox/tests. For production you
  // would persist securely — we intentionally do not write tokens to disk here
  // (Vercel FS is ephemeral) and do not log them.
  return NextResponse.json({
    ok: true,
    received: true,
    message:
      "Token received. Copy access_token into local .env as UPSTOX_ACCESS_TOKEN if this response is visible in your webhook test.",
    access_token: accessToken,
    access_token_length: accessToken.length,
  });
}

/** Health / misconfiguration check (browser GET should not be used by Upstox). */
export async function GET() {
  return NextResponse.json({
    service: "upstox-notifier-webhook",
    method: "POST only",
    portal_field: "Notifier webhook endpoint",
    url: "https://smallcase-sip-lab.vercel.app/webhooks/upstox/notifier",
    note: "Leave blank on the portal if you only use Developer Apps → Generate for tokens.",
  });
}
