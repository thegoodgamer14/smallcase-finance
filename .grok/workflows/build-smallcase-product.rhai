let meta = #{
    name: "build-smallcase-product",
    description: "Product-Owner-orchestrated multi-agent build of the full local Smallcase Finance product (data pipeline, calc engine, API, UI, docs, tests)",
    when_to_use: "Bootstrap or rebuild the complete local Smallcase Finance app from the current repo scaffold",
    phases: [
        #{ title: "Inventory", detail: "Scan repo, data, and constraints" },
        #{ title: "Architecture", detail: "Data model, backend, and UI architecture in parallel" },
        #{ title: "Approval", detail: "Human gate for major structural decisions" },
        #{ title: "Data Foundation", detail: "Schemas, sample data, raw→curated pipeline" },
        #{ title: "Calculation Engine", detail: "Metrics, rebalance/backtest, unit tests" },
        #{ title: "Design", detail: "Dashboard and page design specs" },
        #{ title: "Implementation", detail: "Backend API and Next.js UI in parallel" },
        #{ title: "Integration", detail: "Wire pipeline, sample smallcase, run flow" },
        #{ title: "Documentation", detail: "README, data dictionary, how-to-add-data" },
        #{ title: "Verification", detail: "DoD checks, tests, fix critical gaps" },
        #{ title: "Synthesis", detail: "PO final report and run instructions" },
    ],
};

// ── helpers ──────────────────────────────────────────────────────────────────

fn trimmed(s) {
    if type_of(s) == "string" {
        s.trim();
        s
    } else {
        ""
    }
}

fn truthy(v) {
    v == true || v == "true" || v == 1 || v == "1"
}

fn agent_ok(r) {
    r != () && r.success == true
}

fn text_out(r) {
    if !agent_ok(r) { return ""; }
    if type_of(r.output) == "string" { return trimmed(r.output); }
    if r.output != () { return json_encode(r.output); }
    ""
}

// ── args ─────────────────────────────────────────────────────────────────────
//
// args.skip_approval (bool) — skip the human architecture gate (default false)
// args.force_sample_data (bool) — always generate sample data even if raw/ has files
// args.agent_budget is set by the tool caller, not args

let skip_approval = false;
let force_sample = true;
if args != () {
    if args.skip_approval != () { skip_approval = truthy(args.skip_approval); }
    if args.force_sample_data != () { force_sample = truthy(args.force_sample_data); }
}

// Binding product decisions (PO-owned; specialists must follow)
let stack_brief = "";
stack_brief += "STACK (binding unless Product Owner already approved otherwise):\n";
stack_brief += "- Frontend: Next.js (App Router) + TypeScript + Tailwind + Recharts (or Tremor)\n";
stack_brief += "- Backend: Python + FastAPI\n";
stack_brief += "- Data: Python + Polars or Pandas + DuckDB (or SQLite) + Parquet under data/curated/\n";
stack_brief += "- Layout: data/raw, data/curated, src/, notebooks/, docs/\n";
stack_brief += "- Non-goals v0: production auth, multi-user, live trading, full broker integration\n";
stack_brief += "- Market assumption: INR / Indian equities friendly; support generic tickers\n";
stack_brief += "- Local-first, reproducible, one-command or clearly documented install+run\n";

let po_rules = "";
po_rules += "ORCHESTRATION RULES:\n";
po_rules += "- You are a specialist. Do NOT speak as if you are talking to the end user.\n";
po_rules += "- Write code and docs into the repo. Leave a short agent report of what you did.\n";
po_rules += "- Use tools (read_file, list_dir, grep, bash) — inspect the repo before editing.\n";
po_rules += "- Prefer small, reviewable diffs. Do not gold-plate.\n";
po_rules += "- Follow existing AGENTS.md, PRODUCT.md, and docs/decisions/ ADRs.\n";

let dod = "";
dod += "DEFINITION OF DONE:\n";
dod += "1) Drop data into data/raw/, run documented pipeline → curated outputs\n";
dod += "2) At least one sample smallcase defined (constituents + target weights + methodology)\n";
dod += "3) Core metrics: NAV, returns, CAGR, volatility, max drawdown, Sharpe, basic attribution\n";
dod += "4) Simple rebalancing / backtest capability\n";
dod += "5) Local web UI: dashboard (metrics+chart), holdings, performance/risk, smallcase switcher\n";
dod += "6) Documented install+run; README; data dictionary; how to add personal data\n";
dod += "7) Lightweight tests for core calculation functions\n";

// ════════════════════════════════════════════════════════════════════════════
phase("Inventory");
// ════════════════════════════════════════════════════════════════════════════

let inv_schema = #{
    "type": "object",
    "required": ["summary", "has_raw_data", "has_code", "risks"],
    "properties": #{
        "summary": #{ "type": "string" },
        "has_raw_data": #{ "type": "boolean" },
        "has_code": #{ "type": "boolean" },
        "existing_paths": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 40 },
        "risks": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
    },
};

let inv_prompt = "";
inv_prompt += "You are the inventory scout for the Smallcase Finance repo (Product Owner brief).\n";
inv_prompt += "Workspace root is the current project. Use list_dir, read_file, grep, bash.\n";
inv_prompt += "Read AGENTS.md, PRODUCT.md, README.md, and scan data/, src/, notebooks/, docs/, .grok/agents/.\n";
inv_prompt += "Report what exists vs empty. Note whether data/raw has usable files.\n";
inv_prompt += "Do not modify files. Return structured inventory only.\n";

let inv = agent(inv_prompt, #{
    label: "po-inventory",
    agent_type: "explore",
    capability_mode: "read-only",
    output_schema: inv_schema,
});

let has_raw = false;
let inv_summary = "Inventory unavailable; treating repo as empty scaffold.";
if agent_ok(inv) && inv.output != () {
    if inv.output.has_raw_data == true { has_raw = true; }
    if inv.output.summary != () { inv_summary = trimmed(inv.output.summary); }
}
if force_sample { has_raw = false; }
log("Inventory: " + inv_summary);
log("Will generate sample data: " + (!has_raw).to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Architecture");
// ════════════════════════════════════════════════════════════════════════════

let arch_jobs = [];

// --- Data Architect: logical + physical model ---
let da_prompt = "";
da_prompt += "You are the Data Architect (.grok/agents/data-architect.md) for Smallcase Finance.\n";
da_prompt += po_rules + "\n" + stack_brief + "\n";
da_prompt += "GOAL: Design the v0 data foundation and write it into the repo.\n";
da_prompt += "Repo is mostly empty scaffold. Inventory note: " + inv_summary + "\n\n";
da_prompt += "DELIVERABLES (write these files):\n";
da_prompt += "1) docs/data-dictionary.md — entities, fields, types, grain, source vs derived\n";
da_prompt += "2) docs/decisions/001-data-model.md — ADR: entities, storage (Parquet+DuckDB), layout under data/\n";
da_prompt += "3) docs/architecture/data-model.md — logical model (smallcases, constituents/weights,\n";
da_prompt += "   prices, holdings snapshots, NAV series, metrics, rebalance events) + file layout\n";
da_prompt += "4) Optional: src/smallcase_finance/schemas/ with JSON or Pydantic sketches if helpful\n\n";
da_prompt += "REQUIRED ENTITIES (minimum):\n";
da_prompt += "- instruments (symbol, name, sector optional)\n";
da_prompt += "- prices (symbol, date, close; open/high/low optional)\n";
da_prompt += "- smallcases (id, name, theme, methodology, rebalance_rule, created_at)\n";
da_prompt += "- smallcase_constituents (smallcase_id, symbol, target_weight, as_of / version)\n";
da_prompt += "- nav_series (smallcase_id, date, nav, daily_return)\n";
da_prompt += "- metrics_snapshot (smallcase_id, as_of, cagr, volatility, max_drawdown, sharpe, ...)\n";
da_prompt += "- contribution / attribution table or clear derivation rules\n\n";
da_prompt += "Principles: source-of-truth first; timestamp weight versions; simple for personal local use.\n";
da_prompt += "Do NOT implement the full pipeline yet — design + docs + light schema stubs only.\n";
da_prompt += "End with a short summary of decisions.\n";

arch_jobs.push(#{
    prompt: da_prompt,
    label: "arch-data-architect",
    agent_type: "data-architect",
    capability_mode: "all",
    phase: "Architecture",
});

// --- Backend: service architecture ---
let be_arch_prompt = "";
be_arch_prompt += "You are the Backend agent (.grok/agents/backend.md) for Smallcase Finance.\n";
be_arch_prompt += po_rules + "\n" + stack_brief + "\n";
be_arch_prompt += "GOAL: Propose and document the FastAPI backend architecture for v0 (design only + light stubs).\n";
be_arch_prompt += "Write:\n";
be_arch_prompt += "1) docs/architecture/backend.md — modules, pure calc vs I/O, API surface, data access\n";
be_arch_prompt += "2) docs/decisions/002-backend-stack.md — ADR: FastAPI, how it reads curated Parquet/DuckDB\n";
be_arch_prompt += "3) Skeleton only if useful: src/smallcase_finance/ package layout (empty modules + __init__.py)\n\n";
be_arch_prompt += "API surface (plan for):\n";
be_arch_prompt += "GET /health, GET /smallcases, GET /smallcases/{id}, GET /smallcases/{id}/holdings,\n";
be_arch_prompt += "GET /smallcases/{id}/performance, GET /smallcases/{id}/metrics, GET /smallcases/{id}/nav\n";
be_arch_prompt += "Optional: POST /backtest or GET with query params for rebalance simulation.\n\n";
be_arch_prompt += "Keep pure financial functions importable by notebooks and tests.\n";
be_arch_prompt += "Do NOT build full endpoints yet. Document contracts clearly for Frontend and Data Analyst.\n";

arch_jobs.push(#{
    prompt: be_arch_prompt,
    label: "arch-backend",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Architecture",
});

// --- Design: information architecture ---
let des_arch_prompt = "";
des_arch_prompt += "You are the Design agent (.grok/agents/design.md) for Smallcase Finance.\n";
des_arch_prompt += po_rules + "\n" + stack_brief + "\n";
des_arch_prompt += "GOAL: High-level information architecture and design system direction for the local web UI.\n";
des_arch_prompt += "Write:\n";
des_arch_prompt += "1) docs/architecture/ui.md — pages, navigation, primary user flows\n";
des_arch_prompt += "2) docs/design/design-system.md — dark-mode default, tokens, typography, P&L colors, spacing\n";
des_arch_prompt += "Pages required: Dashboard, Holdings/Composition, Performance & Risk, Smallcase switcher.\n";
des_arch_prompt += "Desktop-first finance density; charts+tables first-class. ASCII wireframes welcome.\n";
des_arch_prompt += "Do NOT implement React code yet.\n";

arch_jobs.push(#{
    prompt: des_arch_prompt,
    label: "arch-design",
    agent_type: "design",
    capability_mode: "all",
    phase: "Architecture",
});

let arch_results = parallel(arch_jobs);
let arch_ok = 0;
for r in arch_results {
    if agent_ok(r) { arch_ok += 1; }
}
log("Architecture specialists completed: " + arch_ok.to_string() + "/" + arch_results.len().to_string());

// PO consolidates architecture into a single plan artifact
let consol_prompt = "";
consol_prompt += "You are acting under Product Owner direction (AGENTS.md + .grok/agents/product-owner.md).\n";
consol_prompt += "Do NOT spawn other agents. Synthesize architecture docs already in the repo.\n";
consol_prompt += "Read docs/architecture/*, docs/decisions/*, docs/data-dictionary.md if present.\n";
consol_prompt += "Write docs/architecture/v0-plan.md that:\n";
consol_prompt += "1) States the chosen stack and why\n";
consol_prompt += "2) Lists build order: data model → sample data+pipeline → calc engine+tests → API → UI → docs\n";
consol_prompt += "3) Lists out-of-scope items\n";
consol_prompt += "4) Lists open risks and assumptions (empty raw data → generate sample OHLCV + 1-2 smallcases)\n";
consol_prompt += "5) Definition of Done checklist\n";
consol_prompt += stack_brief + "\n" + dod + "\n";
consol_prompt += "Also update PRODUCT.md current goals to reflect this v0 build is in progress.\n";
consol_prompt += "Keep it concise and actionable.\n";

let consol = agent(consol_prompt, #{
    label: "po-architecture-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
});
log("Architecture synthesis: " + (if agent_ok(consol) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Approval");
// ════════════════════════════════════════════════════════════════════════════

if !skip_approval {
    await_user(
        "user",
        "Architecture phase complete. Review docs/architecture/v0-plan.md (and related ADRs). Resume this workflow to implement the full product. Pass skip_approval=true on a new run to skip this gate next time.",
    );
}
log("Architecture approved (or skip_approval=true); proceeding to implementation.");

// ════════════════════════════════════════════════════════════════════════════
phase("Data Foundation");
// ════════════════════════════════════════════════════════════════════════════

// Data architect: finalize implementable contracts
let da2_prompt = "";
da2_prompt += "You are the Data Architect. Finalize implementable data contracts for v0.\n";
da2_prompt += po_rules + "\n" + stack_brief + "\n";
da2_prompt += "Read existing docs under docs/architecture and docs/data-dictionary.md.\n";
da2_prompt += "DELIVER:\n";
da2_prompt += "1) Tighten docs/data-dictionary.md to be implementable (exact columns, dtypes, PK/grain).\n";
da2_prompt += "2) docs/data/file-layout.md — exact paths under data/raw and data/curated (Parquet names).\n";
da2_prompt += "3) JSON or YAML example smallcase definition under data/raw/smallcases/ or config/smallcases/.\n";
da2_prompt += "4) src/smallcase_finance/schemas/models.py with Pydantic models matching the dictionary.\n";
da2_prompt += "Coordinate naming so Data Engineer can implement without guessing.\n";

let da2 = agent(da2_prompt, #{
    label: "data-architect-contracts",
    agent_type: "data-architect",
    capability_mode: "all",
    phase: "Data Foundation",
});
log("Data contracts: " + (if agent_ok(da2) { "ok" } else { "failed" }));

// Data engineer: sample data + pipeline
let de_prompt = "";
de_prompt += "You are the Data Engineer (.grok/agents/data-engineer.md).\n";
de_prompt += po_rules + "\n" + stack_brief + "\n";
de_prompt += "GOAL: Reproducible raw→curated pipeline + sample data so the product is demoable.\n";
de_prompt += "Read docs/data-dictionary.md, docs/data/file-layout.md, docs/architecture/* first.\n\n";
de_prompt += "REQUIREMENTS:\n";
de_prompt += "1) If data/raw is empty (or incomplete), GENERATE realistic sample data:\n";
de_prompt += "   - 8–15 Indian-ish equity symbols (e.g. RELIANCE, TCS, INFY, HDFCBANK, ...)\n";
de_prompt += "   - Daily closes for ~2–3 years (business days), CSV or Parquet under data/raw/\n";
de_prompt += "   - 1–2 sample smallcase definition files (theme, constituents, target weights summing to 1.0,\n";
de_prompt += "     methodology text, rebalance rule e.g. quarterly)\n";
de_prompt += "2) Pipeline code under src/smallcase_finance/pipeline/ (or scripts/):\n";
de_prompt += "   - ingest raw → clean → write curated Parquet\n";
de_prompt += "   - quality checks: null rates, date continuity, weight sum ≈ 1.0\n";
de_prompt += "3) Single entrypoint: `python -m smallcase_finance.pipeline` or `make data` / script in Makefile\n";
de_prompt += "4) pyproject.toml or requirements.txt with polars/pandas, duckdb, pyarrow, fastapi, uvicorn, pytest, etc.\n";
de_prompt += "5) Document how to re-run in docs/data/pipeline.md\n";
de_prompt += "6) Actually run the pipeline once so data/curated/ is populated.\n";
de_prompt += "Use Python. Prefer Polars + DuckDB + Parquet. Idempotent runs.\n";
de_prompt += "Do NOT build the full metrics engine or UI.\n";

let de = agent(de_prompt, #{
    label: "data-engineer-pipeline",
    agent_type: "data-engineer",
    capability_mode: "all",
    phase: "Data Foundation",
});
log("Data pipeline: " + (if agent_ok(de) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Calculation Engine");
// ════════════════════════════════════════════════════════════════════════════

let calc_jobs = [];

let analyst_prompt = "";
analyst_prompt += "You are the Data Analyst (.grok/agents/data-analyst.md).\n";
analyst_prompt += po_rules + "\n" + stack_brief + "\n" + dod + "\n";
analyst_prompt += "GOAL: Implement core performance/risk/attribution + simple rebalance backtest as pure Python.\n";
analyst_prompt += "Read curated data layout and schemas. Use tools; inspect real curated files if present.\n\n";
analyst_prompt += "IMPLEMENT under src/smallcase_finance/analytics/ (adjust if package path already set):\n";
analyst_prompt += "- returns & NAV construction from weights + prices (with rebalance schedule)\n";
analyst_prompt += "- CAGR, volatility (ann.), max drawdown, Sharpe (document rf assumption, default 0 or 6%)\n";
analyst_prompt += "- basic contribution/attribution by constituent over a period\n";
analyst_prompt += "- simple backtest: periodic rebalance to target weights vs buy-and-hold drift\n";
analyst_prompt += "Also:\n";
analyst_prompt += "- tests/test_metrics.py (or tests/analytics/) with lightweight pytest covering formulas on synthetic series\n";
analyst_prompt += "- notebooks/01_smallcase_overview.ipynb OR a script that prints a sample metrics table\n";
analyst_prompt += "- docs/analytics/metrics-definitions.md with exact definitions and assumptions\n";
analyst_prompt += "Run pytest and fix failures. Export sample computed outputs into data/curated/ if that matches architecture.\n";
analyst_prompt += "Keep functions pure and importable by FastAPI later.\n";

calc_jobs.push(#{
    prompt: analyst_prompt,
    label: "data-analyst-metrics",
    agent_type: "data-analyst",
    capability_mode: "all",
    phase: "Calculation Engine",
});

let be_core_prompt = "";
be_core_prompt += "You are the Backend agent.\n";
be_core_prompt += po_rules + "\n" + stack_brief + "\n";
be_core_prompt += "GOAL: Stand up FastAPI app skeleton that will serve smallcase data and metrics.\n";
be_core_prompt += "Read docs/architecture/backend.md and existing src/ layout.\n";
be_core_prompt += "IMPLEMENT:\n";
be_core_prompt += "- src/smallcase_finance/api/ (or app/) FastAPI app with /health\n";
be_core_prompt += "- Data access layer reading curated Parquet/DuckDB (graceful empty-state errors)\n";
be_core_prompt += "- Stub or real routes: /smallcases, /smallcases/{id}, holdings, performance, metrics, nav\n";
be_core_prompt += "- Wire to analytics functions IF they already exist; otherwise call placeholders with clear TODOs\n";
be_core_prompt += "- pyproject/requirements already may exist — extend, don't break\n";
be_core_prompt += "- Document run: uvicorn smallcase_finance.api.main:app --reload\n";
be_core_prompt += "Prefer correctness and clear Pydantic response models.\n";

calc_jobs.push(#{
    prompt: be_core_prompt,
    label: "backend-api-skeleton",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Calculation Engine",
});

let calc_results = parallel(calc_jobs);
let calc_ok = 0;
for r in calc_results {
    if agent_ok(r) { calc_ok += 1; }
}
log("Calculation/API phase: " + calc_ok.to_string() + "/" + calc_results.len().to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Design");
// ════════════════════════════════════════════════════════════════════════════

let design_prompt = "";
design_prompt += "You are the Design agent.\n";
design_prompt += po_rules + "\n" + stack_brief + "\n";
design_prompt += "GOAL: Produce implementable UI specs for the Frontend agent.\n";
design_prompt += "Read docs/architecture/ui.md and docs/design/design-system.md; refine them.\n";
design_prompt += "WRITE:\n";
design_prompt += "1) docs/design/pages/dashboard.md — layout, metric cards, performance chart, smallcase switcher\n";
design_prompt += "2) docs/design/pages/holdings.md — composition table, weight bars, sector breakdown if available\n";
design_prompt += "3) docs/design/pages/performance.md — risk metrics, drawdown chart, returns table, attribution\n";
design_prompt += "4) docs/design/components.md — MetricCard, PerformanceChart, HoldingsTable, SmallcaseSelect, props/states\n";
design_prompt += "5) Tailwind-oriented tokens (colors, radii) ready to paste into globals.css / tailwind config\n";
design_prompt += "Dark mode default, desktop-first, finance clarity. No React implementation in this step.\n";

let design_r = agent(design_prompt, #{
    label: "design-ui-specs",
    agent_type: "design",
    capability_mode: "all",
    phase: "Design",
});
log("Design specs: " + (if agent_ok(design_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Implementation");
// ════════════════════════════════════════════════════════════════════════════

let impl_jobs = [];

let be_impl_prompt = "";
be_impl_prompt += "You are the Backend agent — full API implementation pass.\n";
be_impl_prompt += po_rules + "\n" + stack_brief + "\n" + dod + "\n";
be_impl_prompt += "GOAL: Complete FastAPI so Frontend can power the UI from real curated data + analytics.\n";
be_impl_prompt += "Inspect src/, data/curated/, analytics modules, and docs/architecture/backend.md.\n";
be_impl_prompt += "MUST HAVE working endpoints returning JSON for:\n";
be_impl_prompt += "- list/detail smallcases\n";
be_impl_prompt += "- holdings/composition with weights\n";
be_impl_prompt += "- NAV time series\n";
be_impl_prompt += "- headline metrics (CAGR, vol, max DD, Sharpe, total return)\n";
be_impl_prompt += "- performance detail + basic attribution if available\n";
be_impl_prompt += "- optional backtest summary endpoint\n";
be_impl_prompt += "CORS: allow local Next.js (localhost:3000).\n";
be_impl_prompt += "If curated data missing, ensure pipeline can be run; do not leave the API entirely broken.\n";
be_impl_prompt += "Add a short docs/api.md with example curl commands.\n";
be_impl_prompt += "Smoke-test with python -c imports and/or TestClient if feasible.\n";

impl_jobs.push(#{
    prompt: be_impl_prompt,
    label: "backend-api-complete",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Implementation",
});

let fe_impl_prompt = "";
fe_impl_prompt += "You are the Frontend agent (.grok/agents/frontend.md).\n";
fe_impl_prompt += po_rules + "\n" + stack_brief + "\n" + dod + "\n";
fe_impl_prompt += "GOAL: Build a clean local Next.js + TypeScript + Tailwind UI for Smallcase Finance.\n";
fe_impl_prompt += "Read docs/design/* and docs/architecture/ui.md and docs/api.md (if present).\n";
fe_impl_prompt += "Place the app under apps/web/ OR frontend/ OR web/ — pick one consistent with repo; prefer apps/web.\n\n";
fe_impl_prompt += "PAGES / FEATURES:\n";
fe_impl_prompt += "1) Dashboard: headline metrics + performance (NAV) chart + smallcase switcher\n";
fe_impl_prompt += "2) Holdings / composition view\n";
fe_impl_prompt += "3) Performance & risk detail (metrics table, drawdown or returns, attribution if API provides)\n";
fe_impl_prompt += "4) Ability to switch between defined smallcases (URL param or select)\n\n";
fe_impl_prompt += "TECH:\n";
fe_impl_prompt += "- Next.js App Router + TS + Tailwind\n";
fe_impl_prompt += "- Recharts or Tremor for charts\n";
fe_impl_prompt += "- Dark mode default finance UI\n";
fe_impl_prompt += "- Fetch from FastAPI base URL via env NEXT_PUBLIC_API_URL default http://127.0.0.1:8000\n";
fe_impl_prompt += "- Strong types for API responses; graceful loading/empty/error states\n";
fe_impl_prompt += "- If API is down, show clear empty state (optional small mock fallback only if needed for build)\n";
fe_impl_prompt += "Ensure `npm install` and `npm run build` succeed. Document dev script in apps/web/README.md.\n";

impl_jobs.push(#{
    prompt: fe_impl_prompt,
    label: "frontend-ui",
    agent_type: "frontend",
    capability_mode: "all",
    phase: "Implementation",
});

let impl_results = parallel(impl_jobs);
let impl_ok = 0;
for r in impl_results {
    if agent_ok(r) { impl_ok += 1; }
}
log("Implementation: " + impl_ok.to_string() + "/" + impl_results.len().to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Integration");
// ════════════════════════════════════════════════════════════════════════════

let integ_prompt = "";
integ_prompt += "You are a Backend-leaning integration engineer under Product Owner direction.\n";
integ_prompt += po_rules + "\n" + stack_brief + "\n" + dod + "\n";
integ_prompt += "GOAL: Make the whole system runnable end-to-end from a clean checkout.\n";
integ_prompt += "Inspect the full repo. Then:\n";
integ_prompt += "1) Root Makefile or scripts/ with targets: install, data, test, api, web (or documented equivalents)\n";
integ_prompt += "2) Ensure Python package is installable (pip install -e .)\n";
integ_prompt += "3) Re-run pipeline if needed so curated data + at least one smallcase exist\n";
integ_prompt += "4) Re-run pytest; fix broken imports/paths\n";
integ_prompt += "5) Align API response shapes with what the frontend expects (read frontend fetch code)\n";
integ_prompt += "6) Fix CORS, paths, package names, missing __init__.py, etc.\n";
integ_prompt += "7) Add a simple scripts/run_demo.sh or make demo that documents the sequence\n";
integ_prompt += "Do not redesign architecture. Focus on glue and green path.\n";
integ_prompt += "agent_type specialty: backend for code fixes.\n";

let integ = agent(integ_prompt, #{
    label: "integration-glue",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Integration",
});
log("Integration: " + (if agent_ok(integ) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Documentation");
// ════════════════════════════════════════════════════════════════════════════

let docs_prompt = "";
docs_prompt += "You are documenting the product under Product Owner direction (general-purpose).\n";
docs_prompt += po_rules + "\n" + dod + "\n";
docs_prompt += "GOAL: Excellent onboarding docs so a human can use this with personal data immediately.\n";
docs_prompt += "Rewrite/upgrade README.md to include:\n";
docs_prompt += "- What this is\n";
docs_prompt += "- Quickstart (install, generate/run pipeline, start API, start web UI)\n";
docs_prompt += "- Project structure\n";
docs_prompt += "- How to add your own data (drop into data/raw/, expected formats, re-run pipeline)\n";
docs_prompt += "- How smallcases are defined\n";
docs_prompt += "- Metrics definitions link\n";
docs_prompt += "- Non-goals / limitations\n";
docs_prompt += "Also ensure these exist and are accurate:\n";
docs_prompt += "- docs/data-dictionary.md\n";
docs_prompt += "- docs/data/how-to-add-data.md (step-by-step personal data)\n";
docs_prompt += "- docs/data/pipeline.md\n";
docs_prompt += "- PRODUCT.md updated: check off completed goals, note remaining open questions\n";
docs_prompt += "Read the actual code and scripts so docs match reality. Fix mismatches.\n";

let docs_r = agent(docs_prompt, #{
    label: "docs-onboarding",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Documentation",
});
log("Documentation: " + (if agent_ok(docs_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Verification");
// ════════════════════════════════════════════════════════════════════════════

let ver_schema = #{
    "type": "object",
    "required": ["passed", "failed", "notes", "ready_for_user"],
    "properties": #{
        "passed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
        "failed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
        "notes": #{ "type": "string" },
        "ready_for_user": #{ "type": "boolean" },
    },
};

let ver_jobs = [];

let ver_tests_prompt = "";
ver_tests_prompt += "You are verifying the Smallcase Finance repo under Product Owner direction.\n";
ver_tests_prompt += "Use bash and read tools. RUN:\n";
ver_tests_prompt += "1) Python tests (pytest) from repo root or package root\n";
ver_tests_prompt += "2) Pipeline entrypoint if cheap (or confirm curated outputs exist)\n";
ver_tests_prompt += "3) Python import of API app if possible\n";
ver_tests_prompt += "4) Frontend: npm run build if node_modules present or after npm install (reasonable timeout)\n";
ver_tests_prompt += "Fix only CRITICAL breakages that prevent DoD (imports, missing deps in requirements, obvious bugs).\n";
ver_tests_prompt += "Return structured passed/failed checklist against: pipeline, metrics tests, API import, UI build.\n";
ver_tests_prompt += dod;

ver_jobs.push(#{
    prompt: ver_tests_prompt,
    label: "verify-runtime",
    agent_type: "backend",
    capability_mode: "all",
    output_schema: ver_schema,
    phase: "Verification",
});

let ver_dod_prompt = "";
ver_dod_prompt += "You are a read-mostly DoD auditor for Smallcase Finance (explore/general).\n";
ver_dod_prompt += "Inspect the repository structure and key files WITHOUT large rewrites.\n";
ver_dod_prompt += "Check each Definition of Done item and report passed/failed with evidence paths.\n";
ver_dod_prompt += dod + "\n";
ver_dod_prompt += "ready_for_user=true only if a human can realistically follow README to see metrics in UI or notebook/CLI fallback.\n";
ver_dod_prompt += "If critical docs are missing one short file, you may add it; prefer reporting gaps.\n";

ver_jobs.push(#{
    prompt: ver_dod_prompt,
    label: "verify-dod",
    agent_type: "explore",
    capability_mode: "read-only",
    output_schema: ver_schema,
    phase: "Verification",
});

let ver_results = parallel(ver_jobs);

let all_failed = [];
let all_passed = [];
let ready = false;
for r in ver_results {
    if agent_ok(r) && r.output != () {
        if r.output.passed != () {
            for p in r.output.passed { all_passed.push(p); }
        }
        if r.output.failed != () {
            for f in r.output.failed { all_failed.push(f); }
        }
        if r.output.ready_for_user == true { ready = true; }
    }
}
log("Verification passed items: " + all_passed.len().to_string() + ", failed: " + all_failed.len().to_string());

// Critical fix pass if failures remain
if all_failed.len() > 0 {
    let fix_prompt = "";
    fix_prompt += "You are fixing critical gaps under Product Owner direction (backend specialist).\n";
    fix_prompt += po_rules + "\n" + dod + "\n";
    fix_prompt += "The verifier reported these failures (JSON):\n";
    fix_prompt += json_encode(all_failed) + "\n\n";
    fix_prompt += "Fix the highest-impact issues so the green path works: pipeline, tests, API, README quickstart.\n";
    fix_prompt += "Re-run pytest after fixes. Keep scope tight.\n";
    let fix_r = agent(fix_prompt, #{
        label: "verify-fix-critical",
        agent_type: "backend",
        capability_mode: "all",
        phase: "Verification",
    });
    log("Critical fix pass: " + (if agent_ok(fix_r) { "ok" } else { "failed" }));
}

// ════════════════════════════════════════════════════════════════════════════
phase("Synthesis");
// ════════════════════════════════════════════════════════════════════════════

let syn_prompt = "";
syn_prompt += "You are the Product Owner synthesizer for the Smallcase Finance build workflow.\n";
syn_prompt += "Read README.md, PRODUCT.md, docs/architecture/v0-plan.md, and skim src/, apps/ or web/, data/curated/.\n";
syn_prompt += "Write a final user-facing report to docs/build-report.md with:\n";
syn_prompt += "1) What shipped\n";
syn_prompt += "2) Exact commands to install, run pipeline, run API, run UI\n";
syn_prompt += "3) How to add personal data\n";
syn_prompt += "4) Known limitations / next backlog items\n";
syn_prompt += "5) Honest DoD status\n";
syn_prompt += "Also refresh PRODUCT.md checkboxes to match reality.\n";
syn_prompt += "Be accurate — only claim what exists in the repo.\n";
syn_prompt += "Verification notes — passed: " + json_encode(all_passed) + "\n";
syn_prompt += "Verification notes — failed: " + json_encode(all_failed) + "\n";

let syn = agent(syn_prompt, #{
    label: "po-final-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Synthesis",
});

let report_text = text_out(syn);
let report_path = write_scratch_file("build-report.md", report_text);
if report_text == "" {
    report_path = write_scratch_file(
        "build-report.md",
        "# Build workflow finished\n\nSee docs/build-report.md and README.md in the repository.\n",
    );
}

log("Workflow complete. ready_for_user≈" + ready.to_string());

complete(#{
    summary: "Smallcase Finance product build workflow finished",
    report_path: report_path,
    verification_passed_count: all_passed.len(),
    verification_failed_count: all_failed.len(),
    verification_failed: all_failed,
    ready_for_user: ready,
    how_to_run: "See README.md and docs/build-report.md — typically: pip install -e . && make data && make api & make web",
    workflow: "build-smallcase-product",
});
