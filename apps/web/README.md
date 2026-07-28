# Smallcase Finance — Web UI

Local Next.js dashboard for analyzing Smallcase-style thematic portfolios.

## Stack

- Next.js 15 (App Router) + TypeScript
- Tailwind CSS (design tokens from `docs/design/design-system.md`)
- Recharts for equity / drawdown / allocation charts
- Fetches FastAPI at `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`)

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — KPIs, equity curve, allocation, period returns |
| `/holdings` | Composition table, weight + sector charts |
| `/performance` | Risk KPIs, equity + drawdown, window table |

Global **smallcase switcher** and **range chips** (`1M` … `SI`) live in the shell. URL state: `?smallcase=<id>&window=1Y`.

## Prerequisites

1. Curated data under repo `data/curated/` (run pipeline from repo root).
2. FastAPI running:

```bash
# from repo root
make api
# → http://127.0.0.1:8000/docs
```

## Install & run

```bash
cd apps/web
cp .env.example .env.local   # optional; defaults work for local API
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server (port 3000) |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | ESLint |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | FastAPI origin (no trailing slash) |

CORS on the API allows `http://localhost:3000` and `http://127.0.0.1:3000`.

## Design source

- IA: `docs/architecture/ui.md`
- Tokens / components: `docs/design/design-system.md`, `docs/design/components.md`
- Pages: `docs/design/pages/*`

## Notes

- Dark mode is default; toggle persists in `localStorage` (`sf-theme`).
- Last smallcase id: `sf-smallcase`.
- API metric window `ITD` is shown as **SI** (since inception) in the UI.
- If the API is down, the shell shows a clear empty/error state (no fake demo data).
