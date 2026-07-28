# Deploy on Vercel (Hobby free tier) — free-tier decision

**Status:** Binding free-tier hosting plan for SIP Lab  
**Audience:** Founder  
**Goal:** Stable **HTTPS** URLs for Upstox / Kite redirect URIs + optional public UI, **without leaving the free tier**.

---

## Decision (read this first)

### What we deploy on Vercel (correct for free tier)

| Piece | Host | Why |
|-------|------|-----|
| **Next.js UI** (`apps/web`) | **Vercel Hobby** | Native fit; free HTTPS; low Active CPU |
| **OAuth callbacks** | Same project: `/callback/upstox`, `/callback/kite` | Tiny Node route handlers; perfect for broker redirect URIs |
| **FastAPI SIP engine** (Polars / DuckDB / Parquet) | **Local machine** | Heavy compute, filesystem SoT, long syncs — not free-tier-safe on serverless |

### What we deliberately do **not** put on Vercel free

| Tempting option | Why it is a **bad free-tier decision** |
|-----------------|----------------------------------------|
| Full FastAPI + Polars + PyArrow + DuckDB + Pandas as one Python function | Large unpack size / cold starts; Active CPU pricing burns on every metrics query; ephemeral disk fights Parquet SoT; risk of Hobby limits → **pressure to upgrade to Pro** later |
| `UPSTOX_SYNC_ENABLED=1` on a public serverless URL | Long-running network + write I/O; free timeouts; secrets on a public surface |
| Multiple always-on PaaS free boxes “just in case” | More cold starts, more accounts, more ops — no product gain for personal use |

**Cost posture:** Stay on **Vercel Hobby** only. Do not enable paid add-ons, custom domains that require paid DNS (optional free domains are fine), or Pro for longer functions unless you later outgrow Hobby with eyes open.

Render free (`docs/deploy/render.md`) remains an **optional** place for a public **demo** FastAPI if you want `/docs` online. It is **not** required for OAuth redirects once Vercel is live.

---

## Redirect URLs for developer portals

**Live production project (Hobby):** `smallcase-sip-lab`  
**Production host:** `https://smallcase-sip-lab.vercel.app`

```text
Upstox:  https://smallcase-sip-lab.vercel.app/callback/upstox
Kite:    https://smallcase-sip-lab.vercel.app/callback/kite
```

Use the **exact** production hostname Vercel assigns (or your free custom domain).  
Preview URLs (`*.vercel.app` deployment hashes) change — **do not** register preview URLs on Upstox/Kite.

---

## Deploy steps (Hobby)

### 1. Connect the monorepo

1. Push this repo to GitHub (secrets stay out of git).
2. [vercel.com/new](https://vercel.com/new) → import the repo.
3. **Root Directory:** `apps/web`  
   (or use repo-root `vercel.json` which sets `rootDirectory`).
4. Framework: Next.js (auto-detected).
5. Plan: **Hobby** (free). Do not select Pro.
6. Deploy.

CLI alternative (from a machine logged into Vercel):

```bash
cd apps/web
npx vercel@latest link --yes --scope <your-team-slug>
npx vercel@latest --prod --yes
```

### 2. Environment variables (Project → Settings → Environment Variables)

| Key | Environments | Notes |
|-----|----------------|-------|
| `UPSTOX_API_KEY` | Production | Portal API Key |
| `UPSTOX_API_SECRET` | Production | Portal API Secret — never commit |
| `UPSTOX_REDIRECT_URI` | Production | Exact: `https://<project>.vercel.app/callback/upstox` |
| `NEXT_PUBLIC_API_URL` | Production / Preview | Optional. Default is local FastAPI `http://127.0.0.1:8000`. For pure OAuth-only deploy, leave unset or point at local when developing UI against local API. |

Redeploy after setting env vars.

### 3. Register broker apps

1. **Upstox** → redirect = production `/callback/upstox` URL above.  
2. Copy Key/Secret into Vercel env.  
3. **Generate** access token in portal → put in **local** `.env` as `UPSTOX_ACCESS_TOKEN` → run `make sync-upstox` on your Mac.  
4. Optional: browser OAuth via authorize dialog → callback shows token once for copy into local `.env`.  
5. **Kite** (when needed) → `/callback/kite` (placeholder; Phase 4).

### 4. Verify

```bash
BASE=https://smallcase-sip-lab.vercel.app

curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/"
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/callback/upstox"
# 400 without code is OK — route is live
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/callback/kite"
```

UI talks to FastAPI via `NEXT_PUBLIC_API_URL`. For local engine:

```bash
# terminal 1 — free, unlimited personal use
make api

# terminal 2
cd apps/web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev
```

Production UI without a public FastAPI will show API errors for data pages — that is expected under the free-tier split. OAuth callbacks still work.

---

## Free-tier guardrails (do not break these)

1. **Hobby only** — no Pro “just for longer timeouts.”  
2. **No heavy Python data plane on Vercel** for this repo until product requirements force it *and* you accept cost.  
3. **No HTTP Upstox sync** on public Vercel routes.  
4. **Stable production hostname** only in broker portals.  
5. **Spend alerts:** Vercel dashboard → enable spend/usage notifications if available on your account.  
6. Prefer portal **Generate** token over OAuth when you only need local sync.

---

## Architecture (free tier)

```text
  Browser
     │
     ├─ HTTPS ──► Vercel Hobby (Next.js)
     │              • UI (optional demo)
     │              • /callback/upstox  (OAuth redirect)
     │              • /callback/kite    (placeholder)
     │
     └─ local ──► FastAPI on Mac (make api)
                    • Parquet / DuckDB / Polars
                    • make sync-upstox
                    • SIP / backtest engine
```

---

## If you later want a *public* FastAPI demo

Options that stay free-ish without inflating Vercel bill:

1. **Keep engine local** (preferred).  
2. **Render free** — long-running Python web service with sleep; see `render.md`. Still free, separate from Vercel.  
3. **Vercel Python FastAPI** — only if you **slim** dependencies (no full Polars/Pandas stack for every request) and accept Hobby Active CPU limits. Not the default for this product.

---

## Related

- Callbacks (Next): `apps/web/src/app/callback/upstox/route.ts`, `.../kite/route.ts`  
- Callbacks (FastAPI, optional local/Render): `src/smallcase_finance/api/routes/oauth.py`  
- Upstox contract: `docs/integrations/upstox.md`  
- Render alternative: `docs/deploy/render.md`
