# ADR 002 — Backend stack: FastAPI + curated Parquet via DuckDB

**Status:** Accepted (v0)  
**Date:** 2026-07-28  
**Owner:** Backend  
**Related:** [backend architecture](../architecture/backend.md), [ADR 001 — data model](./001-data-model.md)

---

## Context

We need a local-first API for smallcase composition, holdings, NAV, performance, and risk metrics. The project already standardizes on:

- Curated analytics under `data/curated/` (layout fixed in ADR 001)
- Python for data work (Pandas/Polars, notebooks)
- A thin web UI later (Next.js)

The backend agent brief mentioned PostgreSQL as a possible v0 store, but ADR 001 and the product stack binding prefer **Parquet + DuckDB** and local reproducibility over a standing database server.

We also need **pure calculation functions** importable by notebooks and tests so API metrics match offline analysis.

---

## Decision

1. **HTTP framework:** **FastAPI** (Python 3.11+), Pydantic v2 for request/response schemas, Uvicorn as ASGI server.
2. **Primary data plane for v0:** **Read-only curated Parquet** under `data/curated/`.
3. **Query engine:** **DuckDB** in-process (`read_parquet` / registered views). Optional Polars for DataFrame transforms inside `data_access` / services.
4. **No PostgreSQL in v0** unless curated volume or multi-writer needs force it later.
5. **Package layout:** installable `src/smallcase_finance/` with strict split:
   - `calc/` — pure financial functions (no I/O)
   - `data_access/` — filesystem + DuckDB only
   - `services/` — orchestration
   - `api/` — HTTP routers
   - `schemas/` — API contracts
6. **Config:** `DATA_CURATED_ROOT` env (default repo `data/curated`).

---

## How the API reads data

```
Request → router → service → data_access
                                │
                                ├─ resolve path: {DATA_CURATED_ROOT}/…/*.parquet
                                ├─ duckdb.connect(database=":memory:")  # or file cache later
                                └─ SELECT … FROM read_parquet('…')
                         service → calc.*(series, weights) when not precomputed
                         service → Pydantic response
```

### Patterns

| Pattern | When to use |
|---------|-------------|
| Direct Parquet via DuckDB SQL | List/filter smallcases, join prices, date ranges |
| Precomputed `nav_series` / `metrics` Parquet | Fast dashboard reads if pipeline wrote them |
| On-the-fly `calc/` | Missing precompute, custom window, backtest params |
| Polars `scan_parquet` | Heavy column transforms without SQL preference |

### What we deliberately do not do (v0)

- Run a Postgres/MySQL server for the app database
- Write API mutations that update curated Parquet in place
- Embed business math inside SQL only (math lives in `calc/` for reuse)

---

## Consequences

### Positive

- Zero DB ops for local demo; clone repo + curated drop + `uvicorn` is enough.
- Same Python types/functions in notebooks, tests, and API.
- DuckDB is strong at scanning Parquet and date filters without ETL into SQL tables.
- Clear boundary for Data Engineer (write Parquet) vs Backend (read + serve).

### Negative / tradeoffs

- Concurrent writers to curated files are not supported (pipeline should replace atomically).
- Complex multi-table transactional integrity is weaker than Postgres (acceptable for analytics v0).
- Schema drift in Parquet must be coordinated; no DB migrations story — use data dictionary + versioned drops.

### Follow-ups

- Physical paths and dtypes: see ADR 001 + data dictionary (already accepted).
- Wire `data_access` to those paths; map rows → `schemas/` DTOs (domain rows already in `models/entities.py`).
- If we later need user-editable portfolios, introduce SQLite or Postgres for **app state** only; keep market/curated history as Parquet.

---

## Alternatives considered

| Option | Why not (v0) |
|--------|----------------|
| FastAPI + PostgreSQL for everything | Extra ops; duplicates curated lake; slower iteration |
| Node/Express API | Weaker interop with Pandas/Polars/notebooks and shared `calc` |
| Django | Heavier; ORM-centric; not needed without multi-user write models |
| Only notebooks, no API | Blocks Frontend dashboard contract |
| SQLite as sole store | Fine for app state later; worse than Parquet for columnar market history |

---

## Compliance with project non-goals

- No production auth, multi-user, live trading, or broker integration in this stack choice.
- Market assumption: INR / Indian equities friendly; tickers remain opaque strings at the API boundary.
