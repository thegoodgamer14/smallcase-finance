# Kite Connect — future plan only (Phase 4+)

> **Status: NOT IMPLEMENTED.**  
> This version of SIP Lab / Basket Backtest Engine has **no** Kite runtime APIs, **no** Coin / mutual-fund import, and **no** MF NAV path.  
> Historical equity/ETF OHLCV is **Upstox-only** today. See [upstox.md](./upstox.md).

This document is a **forward plan** for implementers (Phase 4+). Do not treat it as a current feature.

## Scope when we get there

| In scope later | Explicitly out |
|----------------|----------------|
| **Read-only** import of **equity** holdings from Zerodha Kite | Order placement / live trading |
| Compare live equity portfolio vs SIP backtest of a strategy | F&O positions |
| Map Kite symbols → local instrument / basket keys | Paid multi-broker sprawl |
| | **Coin MF** holdings / NAV (deferred **after** equity import) |

**Coin / mutual funds:** planned even later than Kite equity import. Do not implement Coin APIs, MF holdings endpoints, or an MF NAV engine in this product version.

## Why later

Product order is fixed:

1. Correct SIP / basket backtest engine (XIRR primary)
2. UI polish
3. Kite **equity** holdings import (this doc)
4. Coin / MF last (if ever in this repo)

## Intended future use (equities only)

When Phase 4 lands, Kite Connect would support **portfolio comparison**, not market-data sourcing:

1. User authorizes a personal Kite app (API key + secret; access token via login flow).
2. App pulls **equity holdings** (and optionally positions) via the official Portfolio APIs.
3. Holdings land under something like `data/raw/holdings/{date}_kite/` → curated snapshots.
4. UI/API compare **actual equity book** vs **SIP backtest** of the author’s basket strategy.

Prices for backtests remain **Upstox historical candles**. Kite is not planned as a candle provider in this product version.

## Non-goals (forever in this product line unless vision changes)

- Placing, modifying, or cancelling orders
- GTT / alerts / streaming ticks as product features
- Multi-user SaaS auth around broker tokens
- Committing API secrets (repo stays public)

## References for future implementers

| Resource | URL |
|----------|-----|
| Kite Connect docs | [https://kite.trade/docs/connect/v3/](https://kite.trade/docs/connect/v3/) |
| Portfolio / holdings | [https://kite.trade/docs/connect/v3/portfolio/](https://kite.trade/docs/connect/v3/portfolio/) |
| Official Python client | [https://github.com/zerodha/pykiteconnect](https://github.com/zerodha/pykiteconnect) |
| Developer console | [https://developers.kite.trade/](https://developers.kite.trade/) |

Env names (when implemented — **do not** wire product runtime yet). You may store keys in local `.env` now:

| Env | Purpose |
|-----|---------|
| `KITE_API_KEY` | API key from developers.kite.trade |
| `KITE_API_SECRET` | API secret (server-side only) |
| `KITE_ACCESS_TOKEN` | Daily session token after login (not needed until Phase 4) |
| `KITE_REDIRECT_URI` | `https://smallcase-sip-lab.vercel.app/callback/kite` |

**What to do after creating the Kite app (today):**

1. Put `KITE_API_KEY` + `KITE_API_SECRET` in **local** `.env` only (never commit).  
2. Confirm redirect URL on the console is `https://smallcase-sip-lab.vercel.app/callback/kite`.  
3. Leave **postback URL blank** (orders/GTT — we do not place orders).  
4. **Do not** start building holdings import until Phase 4 (SIP engine first).  
5. No daily access token is required until you deliberately test the login flow later.

Confirm env names against current Zerodha docs at implementation time. Never commit `.env`.

## Agent / MCP note

The **MCP `kite_connect_api` server** may be used by agents for **API mapping validation** (endpoint shapes, field names) during design reviews. It is **not** product runtime and must not be called from FastAPI, the pipeline, or the Next.js app.

## Implementation checklist (Phase 4 — not this release)

- [ ] ADR: Kite equity holdings import only; no orders; Coin deferred
- [ ] Thin client under `src/smallcase_finance/integrations/kite/` (read holdings only)
- [ ] Raw drop layout + pipeline path to `holdings_snapshots`
- [ ] Compare endpoint/UI: live equity vs SIP backtest
- [ ] Secrets via env only; public-repo safe
- [ ] No Coin / MF code until a later phase

## Related

- Price source (current): [upstox.md](./upstox.md), [ADR 003](../decisions/003-upstox-price-source.md)
- Product vision / non-goals: [PRODUCT.md](../../PRODUCT.md)
