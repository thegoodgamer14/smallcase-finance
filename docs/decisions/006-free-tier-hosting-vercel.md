# ADR 006 — Free-tier hosting: Vercel Hobby for redirects/UI; FastAPI local

**Status:** Accepted  
**Date:** 2026-07-28  
**Context:** Need HTTPS redirect URLs for Upstox/Kite developer apps and optional public UI, entirely on free tiers, without cost inflation later.

## Decision

1. **Vercel Hobby (free)** hosts `apps/web` (Next.js): UI + OAuth callbacks  
   - `https://<project>.vercel.app/callback/upstox`  
   - `https://<project>.vercel.app/callback/kite`  
2. **FastAPI + Polars + DuckDB + Parquet** stay on the **local machine** for personal SIP Lab work (`make api`, `make sync-upstox`).  
3. **Do not** deploy the full Python data stack as a Vercel serverless function on free tier by default.  
4. **Render free** remains optional for a public FastAPI *demo* only — not required for broker app registration.

## Rationale (cost + correctness)

| Option | Free-tier fit | Cost risk later |
|--------|---------------|-----------------|
| Full FastAPI + heavy numeric stack on Vercel | Poor: large deps, Active CPU on every metrics query, ephemeral FS vs Parquet SoT | High — pressure to Pro / overages |
| Next.js + thin OAuth on Vercel Hobby | Excellent | Low for personal traffic |
| FastAPI local | Free / unlimited personal | None |
| Render free for full FastAPI | OK for light demo; sleep/cold start | Low if left free |

## Consequences

- Broker portals get a stable production Vercel HTTPS URL.  
- Real price sync and backtests run where the data already lives (laptop).  
- Production UI without a public API will error on data pages unless `NEXT_PUBLIC_API_URL` points at a free demo host or local engine during dev.  
- Secrets: Upstox API key/secret on Vercel for OAuth exchange only; access token preferably in **local** `.env` for sync.

## Related

- `docs/deploy/vercel.md`  
- `docs/deploy/render.md` (secondary)  
- ADR 005 — Upstox sole market data  
