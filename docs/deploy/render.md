# Deploy FastAPI on Render (free tier) — optional alternative

> **Free-tier primary host is Vercel (Next.js + OAuth callbacks).**  
> See **[vercel.md](./vercel.md)** for the binding decision and broker redirect URLs.  
> Use Render only if you want a **public demo FastAPI** (`/docs`, sample data). OAuth redirects do **not** require Render once Vercel is live.

**Audience:** Founder / you  
**Goal (optional):** Public **HTTPS** FastAPI at `https://<name>.onrender.com` for a demo API.

**Related:** [Vercel free-tier plan](./vercel.md) · [Upstox auth](../integrations/upstox.md) · [Blueprint](../../render.yaml) · [OAuth callbacks](../../src/smallcase_finance/api/routes/oauth.py)

---

## What you get

| Item | Value |
|------|--------|
| URL | `https://smallcase-sip-lab.onrender.com` (name is yours to choose) |
| HTTPS | Automatic free TLS |
| Upstox redirect | `https://<name>.onrender.com/callback/upstox` |
| Kite redirect | `https://<name>.onrender.com/callback/kite` |
| OpenAPI | `https://<name>.onrender.com/docs` |
| Health | `https://<name>.onrender.com/health` |
| Plan | **Free** — service sleeps after ~15 min idle; cold start ~30–60s |

---

## Prerequisites

1. GitHub (or GitLab/Bitbucket) account with this repo pushed.  
   Private or public is fine; **never push `.env`**.
2. Free [Render](https://render.com) account (no credit card required for free web services).
3. Optional: Upstox developer app (can create **after** you know the Render URL).

---

## Path A — Blueprint (recommended)

The repo includes [`render.yaml`](../../render.yaml).

1. Push latest `main` (including `render.yaml`) to GitHub.
2. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the repo → Render reads `render.yaml`.
4. Confirm service name (default `smallcase-sip-lab`) and region (default Singapore).
5. Apply. First build:
   - `pip install .`
   - `python -m smallcase_finance.pipeline` (generates **sample** curated data — prices are gitignored)
6. When status is **Live**, open:
   ```text
   https://<your-service>.onrender.com/health
   https://<your-service>.onrender.com/docs
   ```

### Set environment variables (after first deploy)

Dashboard → your service → **Environment** → add:

| Key | Required? | Notes |
|-----|-----------|--------|
| `UPSTOX_REDIRECT_URI` | For OAuth | Exact: `https://<your-service>.onrender.com/callback/upstox` |
| `UPSTOX_API_KEY` | For OAuth | Portal **API Key** |
| `UPSTOX_API_SECRET` | For OAuth | Portal **API Secret** |
| `UPSTOX_ACCESS_TOKEN` | For live candles | Portal **Generate**, or token from OAuth callback page |
| `CORS_ORIGINS` | If UI on Vercel etc. | Comma-separated, e.g. `https://my-app.vercel.app` |
| `UPSTOX_SYNC_ENABLED` | Leave `0` | Do not enable HTTP sync on a public free URL |

Save → Render redeploys. Tokens are **never** committed to git.

---

## Path B — Manual Web Service

1. **New** → **Web Service** → connect repo.
2. Settings:

| Field | Value |
|-------|--------|
| **Name** | `smallcase-sip-lab` (or any unique name) |
| **Region** | Singapore (or closest) |
| **Runtime** | Python 3 |
| **Build Command** | `pip install . && python -m smallcase_finance.pipeline` |
| **Start Command** | `uvicorn smallcase_finance.main:app --host 0.0.0.0 --port $PORT` |
| **Instance type** | Free |
| **Health check path** | `/health` |

3. Add env vars (same table as Path A).
4. Deploy.

---

## Wire Upstox / Kite redirect URLs

Once the service name is fixed:

```text
Upstox:  https://smallcase-sip-lab.onrender.com/callback/upstox
Kite:    https://smallcase-sip-lab.onrender.com/callback/kite
```

### Upstox — get credentials

1. [Developer Apps](https://account.upstox.com/developer/apps) → create/edit app.  
2. Redirect URI = the Upstox URL above (**exact** match, no trailing slash mismatch).  
3. Copy API Key + API Secret → Render env `UPSTOX_API_KEY` / `UPSTOX_API_SECRET`.  
4. Set `UPSTOX_REDIRECT_URI` to the same URL.  
5. **Easiest token path:** portal → **Generate** → paste into `UPSTOX_ACCESS_TOKEN`.  
6. **OAuth path (optional):** open authorize URL in browser:

```text
https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=<API_KEY>&redirect_uri=https%3A%2F%2F<smallcase-sip-lab.onrender.com>%2Fcallback%2Fupstox
```

After login, Render serves `/callback/upstox`, exchanges the code, and shows the access token **once** for copy into `UPSTOX_ACCESS_TOKEN`.

### Kite

Register `/callback/kite` so the developer console accepts the app. Full token exchange is **Phase 4** (placeholder page only). Kite Connect subscription is paid separately.

---

## Verify

```bash
# replace with your service URL
BASE=https://smallcase-sip-lab.onrender.com

curl -sS "$BASE/health" | jq
curl -sS "$BASE/smallcases" | jq '.items[].id'
curl -sS "$BASE/integrations/upstox/status" | jq
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/callback/upstox"
# 400 without code is expected — proves the route exists
```

Cold start: first request after sleep can take **30–60+ seconds**. Wait and retry.

---

## Free-tier limits (plan around them)

| Limit | Impact on this app |
|-------|--------------------|
| Sleep after ~15 min idle | First hit is slow |
| Ephemeral filesystem | Build-time sample Parquet is in the deploy artifact; **writes at runtime** (e.g. HTTP sync) do not persist across deploys — keep `UPSTOX_SYNC_ENABLED=0` |
| ~512 MB RAM | Fine for demo API + sample data; large multi-year syncs better **locally** via `make sync-upstox` |
| 750 hrs/month free | Enough for personal use |

**Recommended split**

- **Render:** public HTTPS redirect + demo API (sample data).  
- **Local Mac:** real Upstox sync + pipeline (`make sync-upstox`) with secrets only in local `.env`.

---

## Frontend (optional)

Next.js stays free on [Vercel](https://vercel.com):

1. Deploy `apps/web` as a Vercel project (root directory `apps/web`).  
2. Set `NEXT_PUBLIC_API_URL=https://<your-service>.onrender.com`.  
3. On Render, set `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`.

Local UI against Render API:

```bash
# apps/web
NEXT_PUBLIC_API_URL=https://smallcase-sip-lab.onrender.com npm run dev
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Build fails on `pip install` | Ensure Python ≥ 3.11 (`PYTHON_VERSION` in `render.yaml`) |
| `/smallcases` empty or 500 | Confirm build ran `python -m smallcase_finance.pipeline` |
| OAuth “redirect_uri mismatch” | Portal value must equal `UPSTOX_REDIRECT_URI` and the authorize URL, character-for-character |
| Token exchange 500 “missing server env” | Set Key, Secret, Redirect on Render Environment |
| CORS errors from browser UI | Set `CORS_ORIGINS` to the exact frontend origin (scheme + host, no path) |
| Service “unavailable” then works | Cold start — wait and retry `/health` |

---

## Security checklist

- [ ] `.env` is gitignored and never deployed as a file  
- [ ] Secrets only in Render Environment (encrypted at rest by Render)  
- [ ] `UPSTOX_SYNC_ENABLED` is **not** `1` on public free tier  
- [ ] Do not paste access tokens into public issues/chats  
- [ ] Prefer portal **Generate** when OAuth page is unnecessary  

---

## Local parity

```bash
# same as Render start, local port
pip install .
python -m smallcase_finance.pipeline
uvicorn smallcase_finance.main:app --host 0.0.0.0 --port 8000
# open http://127.0.0.1:8000/docs
```
