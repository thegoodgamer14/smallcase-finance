# Kite Connect — equity holdings (read-only)

**Role:** Live **equity book** from Zerodha Kite.  
**Not a price source.** Historical OHLCV stays **Upstox-only** (ADR 005).

**Status:** Login + token exchange + holdings smoke CLI implemented. Full “book vs SIP compare” UI is next.

---

## Why no access token on the developer portal

Kite **does not** issue a permanent access token in the app console. You only get:

| Credential | Where |
|------------|--------|
| `api_key` | developers.kite.trade app |
| `api_secret` | developers.kite.trade app (server-side only) |
| `access_token` | **Daily login flow** after you complete Zerodha login |

Official flow: [User / Login](https://kite.trade/docs/connect/v3/user/)

```text
1. Open https://kite.zerodha.com/connect/login?v=3&api_key=<API_KEY>
2. User logs in + 2FA
3. Redirect to your registered URL with ?request_token=...
4. Server POST https://api.kite.trade/session/token
     api_key + request_token + checksum
     checksum = SHA-256(api_key + request_token + api_secret)
5. Response includes access_token (until ~6 AM IST next day)
6. Calls use: Authorization: token api_key:access_token
```

**Redirect URL** for this project (register exactly one or both):

```text
https://smallcase-sip-lab.vercel.app/callback/kite
http://127.0.0.1:8000/callback/kite
```

Leave **postback URL** blank (orders/GTT — we do not place orders).

---

## Consent screen: “Place, modify, and cancel orders”

**You cannot turn that line off for a standard Kite Connect app.**  
Zerodha shows a **fixed permission list** for every Connect `api_key` login. There is **no** OAuth scope parameter on  
`https://kite.zerodha.com/connect/login?v=3&api_key=...` to request “holdings only.”

| What you see on Authorize | What Backtest Hero does |
|---------------------------|-------------------------|
| Place / modify / cancel orders | **Never** — no order APIs in this repo |
| Access holdings and positions | **Yes** — `GET /portfolio/holdings` via Kite client |
| Account balance and margins | Not used (token may allow; we do not call margins) |
| Profile details | Optional smoke (`profile` CLI only) |

**Product policy:** Kite is **read-only equity book**. Orders, GTT, funds, and trading are permanent non-goals.

If the consent copy worries you: that is Zerodha’s Connect product UX, not an extra permission we opted into. After authorize, this app only calls **holdings** (and optionally **profile** for debug). Tokens still technically belong to a full Connect session on Zerodha’s side; we simply never exercise order endpoints.

**Postback URL** on the developer app should stay **empty** (used for order updates we do not need).

---

## Local setup

```bash
# .env (never commit)
KITE_API_KEY=...
KITE_API_SECRET=...
KITE_REDIRECT_URI=https://smallcase-sip-lab.vercel.app/callback/kite
# after login:
KITE_ACCESS_TOKEN=...
```

```bash
make kite-login
# complete login in browser → copy request_token from redirect URL
make kite-exchange REQUEST_TOKEN=xxxxxxxx
# paste printed KITE_ACCESS_TOKEN into .env, then:
make kite-profile
make kite-holdings
```

Or use FastAPI callback (if redirect is `http://127.0.0.1:8000/callback/kite`):

```bash
make api
# open login URL from make kite-login; after redirect, token page shows access_token
```

Or Vercel: set `KITE_API_KEY` + `KITE_API_SECRET` on the project, open login URL, callback at  
`https://smallcase-sip-lab.vercel.app/callback/kite` exchanges and displays the token once.

---

## API (this app)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/integrations/kite/status` | Booleans + optional `login_url` — **no secrets** |
| GET | `/callback/kite` | Exchange `request_token` → show `access_token` once |

Holdings import CLI:

```bash
python -m smallcase_finance.integrations.kite holdings
```

---

## Product map

| Your book | Integration |
|-----------|-------------|
| **Kite equity** | This module (holdings read-only) |
| **Coin MF** | Later (not this slice) |
| **smallcase.com invest** | Future vision; create/backtest baskets **in this app** today |
| **Prices for backtests** | Upstox only |

---

## Non-goals

- Order placement, GTT, streaming ticks  
- Using Kite as historical candle vendor  
- Multi-user SaaS token vault  

---

## Code

| Path | Role |
|------|------|
| `integrations/kite/auth.py` | login URL, checksum, token exchange |
| `integrations/kite/client.py` | profile + holdings |
| `integrations/kite/__main__.py` | CLI |
| `apps/web/.../callback/kite/route.ts` | Vercel exchange helper |

## Related

- Prices: [upstox.md](./upstox.md)  
- SIP Lab: [ROADMAP](../ROADMAP.md)  
