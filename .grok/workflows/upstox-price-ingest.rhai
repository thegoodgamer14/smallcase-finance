let meta = #{
    name: "upstox-price-ingest",
    description: "Plan and implement Upstox historical price ingestion for local smallcase backtests (env-based credentials, keep sample data, pipeline + docs + light UI)",
    when_to_use: "Wire real market history via Upstox API so smallcases can be backtested on N years of prices",
    phases: [
        #{ title: "Discover", detail: "Map current pipeline contracts and Upstox API needs" },
        #{ title: "Plan", detail: "ADR + implementation plan for approval" },
        #{ title: "Approval", detail: "Human gate before coding" },
        #{ title: "Implement", detail: "Upstox client, pipeline stage, config, tests" },
        #{ title: "Surface", detail: "CLI/Make + light UI data-source affordance" },
        #{ title: "Docs", detail: "Env setup, one-click path later, how-to" },
        #{ title: "Verify", detail: "Tests, dry-run, DoD check" },
        #{ title: "Synthesis", detail: "PO report and next steps" },
    ],
};

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

// args.skip_approval — skip human gate (default false)
// args.years — default lookback years as string/number for plan (default 3)
// args.live_fetch — if true, attempt live Upstox call when credentials present (default false)

let skip_approval = false;
let years = 3;
let live_fetch = false;
if args != () {
    if args.skip_approval != () { skip_approval = truthy(args.skip_approval); }
    if args.live_fetch != () { live_fetch = truthy(args.live_fetch); }
    if args.years != () {
        // years may be number or string; coerce carefully
        if type_of(args.years) == "i64" || type_of(args.years) == "f64" {
            years = args.years;
        }
    }
}

let years_s = years.to_string();

let scope = "";
scope += "PRODUCT CONTEXT (binding for this small v0.1 slice):\n";
scope += "- Goal: connect Upstox historical market data so we can backtest local smallcases over ~N years.\n";
scope += "- Smallcase.com cannot export user-created smallcases via API → smallcases stay local JSON under data/raw/smallcases/.\n";
scope += "- User will provide Upstox API credentials when needed via ENV (never commit secrets).\n";
scope += "- Keep synthetic sample data as fallback demo path.\n";
scope += "- On incomplete prices: skip missing symbols with WARNINGS; renormalize remaining weights (existing policy OK).\n";
scope += "- Design toward future one-click connect, but this slice is: env credentials + make/CLI sync + pipeline recompute.\n";
scope += "- OUT OF SCOPE this slice: Smallcase.com login, broker order placement, storing passwords, full multi-broker framework,\n";
scope += "  reproducing Smallcase.com official backtest charts pixel-for-pixel, production OAuth UI.\n";
scope += "- Default lookback years for plan/docs: " + years_s + "\n";
scope += "- Prefer stack already in repo: Python, FastAPI, Polars/Pandas, Parquet, existing pipeline layout.\n";

let po = "";
po += "You are a specialist under Product Owner direction (AGENTS.md). Do not address the end user directly.\n";
po += "Inspect the repo with tools before editing. Keep diffs small. No gold-plating.\n";

// ════════════════════════════════════════════════════════════════════════════
phase("Discover");
// ════════════════════════════════════════════════════════════════════════════

let disc_schema = #{
    "type": "object",
    "required": ["pipeline_entry", "price_contract", "gaps", "risks"],
    "properties": #{
        "pipeline_entry": #{ "type": "string" },
        "price_contract": #{ "type": "string" },
        "raw_layout": #{ "type": "string" },
        "gaps": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "risks": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "suggested_modules": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
    },
};

let disc_prompt = "";
disc_prompt += po + "\n" + scope + "\n";
disc_prompt += "DISCOVER (read-only): Map how prices flow today and what Upstox integration must hook into.\n";
disc_prompt += "Read: docs/data-dictionary.md, docs/data/file-layout.md, docs/data/pipeline.md, docs/data/how-to-add-data.md,\n";
disc_prompt += "src/smallcase_finance/pipeline/*, pyproject.toml, PRODUCT.md, README.md.\n";
disc_prompt += "Return structured notes: pipeline entrypoint, exact price columns/grain, raw folder layout, gaps for Upstox, risks, module ideas.\n";
disc_prompt += "Do not modify files.\n";

let disc = agent(disc_prompt, #{
    label: "discover-pipeline",
    agent_type: "explore",
    capability_mode: "read-only",
    output_schema: disc_schema,
});

let disc_json = "{}";
if agent_ok(disc) && disc.output != () {
    disc_json = json_encode(disc.output);
}
log("Discover complete");

// Parallel: Upstox API research (what endpoints/auth/instrument keys)
let upstox_research_prompt = "";
upstox_research_prompt += po + "\n" + scope + "\n";
upstox_research_prompt += "RESEARCH Upstox historical candle / market quote APIs for equities (India).\n";
upstox_research_prompt += "Use web_search / open_page if available. Prefer official Upstox API v2 docs.\n";
upstox_research_prompt += "Document for implementers (write docs/integrations/upstox-research.md):\n";
upstox_research_prompt += "1) Auth model (access token / API key / what env vars we should use)\n";
upstox_research_prompt += "2) How to resolve NSE/BSE symbol → instrument_key\n";
upstox_research_prompt += "3) Historical candle endpoint (interval, max range, pagination, rate limits)\n";
upstox_research_prompt += "4) Response field mapping to our prices contract: symbol, date, open, high, low, close, volume\n";
upstox_research_prompt += "5) Failure modes and recommended retries\n";
upstox_research_prompt += "6) Explicit: never store secrets in git; .env.example only\n";
upstox_research_prompt += "Be accurate; cite doc URLs in the markdown. If unsure, say so.\n";

let research = agent(upstox_research_prompt, #{
    label: "research-upstox-api",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Discover",
});
log("Upstox research: " + (if agent_ok(research) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Plan");
// ════════════════════════════════════════════════════════════════════════════

let plan_jobs = [];

let da_plan = "";
da_plan += po + "\n" + scope + "\n";
da_plan += "Discovery JSON (untrusted):\n" + disc_json + "\n\n";
da_plan += "You are the Data Architect. Read docs/integrations/upstox-research.md if present.\n";
da_plan += "Write:\n";
da_plan += "1) docs/decisions/003-upstox-price-source.md — ADR: Upstox as optional live price source;\n";
da_plan += "   sample remains default; raw drop layout for upstox pulls; source label in prices.\n";
da_plan += "2) Update docs/data/file-layout.md and docs/data-dictionary.md ONLY as needed for source=upstox.\n";
da_plan += "Keep personal secrets out of docs. Small slice only.\n";

plan_jobs.push(#{
    prompt: da_plan,
    label: "plan-data-architect",
    agent_type: "data-architect",
    capability_mode: "all",
    phase: "Plan",
});

let be_plan = "";
be_plan += po + "\n" + scope + "\n";
be_plan += "You are the Backend agent. Read discovery notes and docs/integrations/upstox-research.md.\n";
be_plan += "Write docs/architecture/upstox-ingest-plan.md with:\n";
be_plan += "- Modules to add (e.g. src/smallcase_finance/integrations/upstox/)\n";
be_plan += "- Env vars (UPSTOX_ACCESS_TOKEN or whatever research says; .env.example)\n";
be_plan += "- CLI: python -m smallcase_finance.integrations.upstox.sync --years " + years_s + " --symbols ...\n";
be_plan += "  or sync symbols from existing smallcase definitions automatically\n";
be_plan += "- How sync writes into data/raw/prices/{date}_upstox/ then pipeline runs\n";
be_plan += "- Rate-limit / pagination strategy\n";
be_plan += "- Test strategy with mocked HTTP (no live token required in CI)\n";
be_plan += "- Future one-click: what UI would call later (POST /admin/sync-prices stub optional)\n";
be_plan += "- Explicit non-goals\n";
be_plan += "- Implementation checklist ordered for a small PR series\n";
be_plan += "Do NOT implement production code yet beyond optional stubs if required for the plan clarity.\n";

plan_jobs.push(#{
    prompt: be_plan,
    label: "plan-backend",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Plan",
});

let plan_results = parallel(plan_jobs);
let plan_ok = 0;
for r in plan_results {
    if agent_ok(r) { plan_ok += 1; }
}
log("Plan specialists: " + plan_ok.to_string() + "/" + plan_results.len().to_string());

let consol = "";
consol += po + "\n" + scope + "\n";
consol += "Synthesize a single approval doc: docs/architecture/v0.1-upstox-plan.md\n";
consol += "Read ADR 003 and docs/architecture/upstox-ingest-plan.md and research notes.\n";
consol += "Include: user-facing summary, what will change, what will NOT, env setup steps,\n";
consol += "definition of done for this slice, risks, and a checkbox implementation order.\n";
consol += "State clearly: user-created Smallcase.com baskets are NOT auto-imported; user mirrors them as local JSON.\n";
consol += "State clearly: 'platform backtest numbers from Smallcase.com' are out of scope; we compute local metrics.\n";
consol += "Update PRODUCT.md open questions / next goal to mention Upstox v0.1 in progress.\n";

let consol_r = agent(consol, #{
    label: "po-plan-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Plan",
});
log("Plan synthesis: " + (if agent_ok(consol_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Approval");
// ════════════════════════════════════════════════════════════════════════════

if !skip_approval {
    await_user(
        "user",
        "Review docs/architecture/v0.1-upstox-plan.md (and ADR 003). Resume to implement Upstox price ingest. Or re-run with skip_approval=true.",
    );
}
log("Approved (or skip_approval); implementing.");

// ════════════════════════════════════════════════════════════════════════════
phase("Implement");
// ════════════════════════════════════════════════════════════════════════════

let impl_jobs = [];

let de_impl = "";
de_impl += po + "\n" + scope + "\n";
de_impl += "You are the Data Engineer. IMPLEMENT the Upstox → raw prices path per the approved plan docs.\n";
de_impl += "Read docs/architecture/v0.1-upstox-plan.md and upstox-ingest-plan.md and research notes first.\n";
de_impl += "REQUIREMENTS:\n";
de_impl += "1) Upstox client module with clear interfaces; HTTP mocked in unit tests\n";
de_impl += "2) Symbol/instrument resolution path documented; support NSE equities used in sample smallcases\n";
de_impl += "3) Sync command that:\n";
de_impl += "   - reads symbols from data/raw/smallcases/*.json (union of constituents) unless --symbols given\n";
de_impl += "   - fetches ~" + years_s + " years daily history (configurable --years)\n";
de_impl += "   - writes data/raw/prices/{yyyy-mm-dd}_upstox/ in our price schema\n";
de_impl += "   - logs warnings for symbols that fail; continues with others\n";
de_impl += "4) Credentials ONLY from environment / .env (python-dotenv ok); never commit secrets\n";
de_impl += "5) .env.example with placeholder var names\n";
de_impl += "6) Ensure existing pipeline still ingests upstox-labeled drops; source column preserved if schema has it\n";
de_impl += "7) Keep sample generator path intact when no upstox data\n";
de_impl += "8) pyproject deps: add httpx if needed\n";
de_impl += "9) tests/ with mocked responses proving mapping + partial failure warnings\n";
de_impl += "If live credentials are absent, sync must exit with a clear message (non-zero ok).\n";
de_impl += "Do not build a full OAuth browser flow.\n";

impl_jobs.push(#{
    prompt: de_impl,
    label: "impl-data-engineer",
    agent_type: "data-engineer",
    capability_mode: "all",
    phase: "Implement",
});

let be_impl = "";
be_impl += po + "\n" + scope + "\n";
be_impl += "You are the Backend agent. Support the Upstox ingest with API/CLI ergonomics from the plan.\n";
be_impl += "After data-engineer modules exist (or create complementary pieces if missing):\n";
be_impl += "1) Make target e.g. `make sync-upstox YEARS=" + years_s + "` that runs sync then pipeline\n";
be_impl += "2) Optional FastAPI endpoint POST /integrations/upstox/sync that is DISABLED unless\n";
be_impl += "   env UPSTOX_SYNC_ENABLED=1 (local-only footgun guard) — or skip endpoint if plan preferred CLI-only\n";
be_impl += "3) Ensure health or a small GET /integrations/upstox/status reports whether token is configured (boolean only; never echo secret)\n";
be_impl += "4) Wire docs/api.md updates\n";
be_impl += "5) Tests for status endpoint\n";
be_impl += "Coordinate file paths with existing package layout. Run pytest and fix breakages you cause.\n";

impl_jobs.push(#{
    prompt: be_impl,
    label: "impl-backend",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Implement",
});

let impl_results = parallel(impl_jobs);
let impl_ok = 0;
for r in impl_results {
    if agent_ok(r) { impl_ok += 1; }
}
log("Implement: " + impl_ok.to_string() + "/" + impl_results.len().to_string());

// Integration glue if parallel agents stepped on each other
let glue = "";
glue += po + "\n" + scope + "\n";
glue += "Integration pass: inspect Upstox modules, Makefile, pipeline, tests. Fix import paths, missing __init__,\n";
glue += "double definitions, and ensure `make sync-upstox` or documented CLI exists. Run pytest -q and fix failures.\n";
glue += "If live_fetch requested is not your concern unless env present — do not block on missing token.\n";

let glue_r = agent(glue, #{
    label: "impl-integration",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Implement",
});
log("Integration: " + (if agent_ok(glue_r) { "ok" } else { "failed" }));

// Optional live fetch attempt note — agent checks env without printing secrets
if live_fetch {
    let live_p = "";
    live_p += po + "\n";
    live_p += "LIVE FETCH: If UPSTOX credentials are present in the environment, run the sync for sample smallcase symbols\n";
    live_p += "for " + years_s + " years, then run the pipeline. Do NOT print token values. If missing, log that live fetch was skipped.\n";
    live_p += "Summarize row counts written.\n";
    let live_r = agent(live_p, #{
        label: "live-upstox-fetch",
        agent_type: "data-engineer",
        capability_mode: "all",
        phase: "Implement",
    });
    log("Live fetch attempt: " + (if agent_ok(live_r) { "ok" } else { "failed/skipped" }));
}

// ════════════════════════════════════════════════════════════════════════════
phase("Surface");
// ════════════════════════════════════════════════════════════════════════════

let fe_prompt = "";
fe_prompt += po + "\n" + scope + "\n";
fe_prompt += "You are the Frontend agent. Light UI affordances only (small scope):\n";
fe_prompt += "1) Show data source / last price range if API already exposes it; else show static help linking to docs\n";
fe_prompt += "2) Small banner or settings blurb: 'Prices: sample or Upstox — configure UPSTOX_* and run make sync-upstox'\n";
fe_prompt += "3) If GET /integrations/upstox/status exists, show configured: yes/no (boolean)\n";
fe_prompt += "Do NOT build full OAuth connect UI in this slice. Keep dark finance styling.\n";
fe_prompt += "Ensure npm run build still works.\n";

let fe_r = agent(fe_prompt, #{
    label: "surface-frontend",
    agent_type: "frontend",
    capability_mode: "all",
    phase: "Surface",
});
log("UI surface: " + (if agent_ok(fe_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Docs");
// ════════════════════════════════════════════════════════════════════════════

let docs_p = "";
docs_p += po + "\n" + scope + "\n";
docs_p += "Update user-facing docs to match what was actually implemented (inspect code!):\n";
docs_p += "1) README.md — section 'Real prices via Upstox'\n";
docs_p += "2) docs/data/how-to-add-data.md — Upstox path + sample fallback\n";
docs_p += "3) docs/integrations/upstox.md — get token, env vars, sync command, troubleshoot rate limits\n";
docs_p += "4) PRODUCT.md — check off / rephrase next goal; note Smallcase.com basket import still manual JSON\n";
docs_p += "5) Future one-click connect: short 'roadmap' bullet in docs/integrations/upstox.md\n";
docs_p += "Never put real secrets in docs.\n";

let docs_r = agent(docs_p, #{
    label: "docs-upstox",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Docs",
});
log("Docs: " + (if agent_ok(docs_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Verify");
// ════════════════════════════════════════════════════════════════════════════

let ver_schema = #{
    "type": "object",
    "required": ["passed", "failed", "ready_for_user", "notes"],
    "properties": #{
        "passed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 16 },
        "failed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 16 },
        "ready_for_user": #{ "type": "boolean" },
        "notes": #{ "type": "string" },
    },
};

let ver_p = "";
ver_p += po + "\n" + scope + "\n";
ver_p += "VERIFY DoD for this slice by running commands and reading code:\n";
ver_p += "1) pytest passes (including mocked Upstox tests)\n";
ver_p += "2) Sync CLI exists and fails clearly without credentials\n";
ver_p += "3) Sample pipeline still works (make pipeline / python -m smallcase_finance.pipeline)\n";
ver_p += "4) .env.example present; no secrets in git-tracked files (grep for obvious token patterns carefully)\n";
ver_p += "5) Docs describe real steps\n";
ver_p += "6) Sample data path still intact\n";
ver_p += "Fix only critical breakages. Return structured passed/failed.\n";
ver_p += "ready_for_user=true if user can follow docs to set UPSTOX token and sync prices for local backtest.\n";

let ver_r = agent(ver_p, #{
    label: "verify-upstox-dod",
    agent_type: "backend",
    capability_mode: "all",
    output_schema: ver_schema,
    phase: "Verify",
});

let all_failed = [];
let all_passed = [];
let ready = false;
if agent_ok(ver_r) && ver_r.output != () {
    if ver_r.output.passed != () {
        for p in ver_r.output.passed { all_passed.push(p); }
    }
    if ver_r.output.failed != () {
        for f in ver_r.output.failed { all_failed.push(f); }
    }
    if ver_r.output.ready_for_user == true { ready = true; }
}
log("Verify passed=" + all_passed.len().to_string() + " failed=" + all_failed.len().to_string());

if all_failed.len() > 0 {
    let fix_p = "";
    fix_p += po + "\n";
    fix_p += "Fix these verification failures (JSON): " + json_encode(all_failed) + "\n";
    fix_p += "Keep scope to Upstox ingest slice. Re-run pytest.\n";
    let fix_r = agent(fix_p, #{
        label: "verify-fix",
        agent_type: "backend",
        capability_mode: "all",
        phase: "Verify",
    });
    log("Fix pass: " + (if agent_ok(fix_r) { "ok" } else { "failed" }));
}

// ════════════════════════════════════════════════════════════════════════════
phase("Synthesis");
// ════════════════════════════════════════════════════════════════════════════

let syn_p = "";
syn_p += "Product Owner synthesis for Upstox v0.1 slice. Inspect repo and write docs/build-report-upstox.md with:\n";
syn_p += "1) What shipped\n";
syn_p += "2) Exact commands to configure token + sync + pipeline + run UI\n";
syn_p += "3) What user must still do manually (mirror Smallcase baskets as JSON; provide API token)\n";
syn_p += "4) Limitations vs full one-click Smallcase connect\n";
syn_p += "5) Verification notes passed=" + json_encode(all_passed) + " failed=" + json_encode(all_failed) + "\n";
syn_p += "Be honest; only claim what exists.\n";

let syn = agent(syn_p, #{
    label: "po-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Synthesis",
});

let report_text = text_out(syn);
let report_path = write_scratch_file("upstox-report.md", report_text);
if report_text == "" {
    report_path = write_scratch_file(
        "upstox-report.md",
        "# Upstox ingest workflow finished\n\nSee docs/build-report-upstox.md and docs/architecture/v0.1-upstox-plan.md\n",
    );
}

complete(#{
    summary: "Upstox price ingest workflow finished",
    report_path: report_path,
    ready_for_user: ready,
    verification_passed_count: all_passed.len(),
    verification_failed_count: all_failed.len(),
    verification_failed: all_failed,
    years: years,
    how_to_run: "Review docs/architecture/v0.1-upstox-plan.md; set UPSTOX_* from .env.example; make sync-upstox; make pipeline; make api & make web",
    note: "Smallcase.com user baskets are not API-exportable; define local JSON. Credentials via env only — never commit.",
    workflow: "upstox-price-ingest",
});
