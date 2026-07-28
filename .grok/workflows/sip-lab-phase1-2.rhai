let meta = #{
    name: "sip-lab-phase1-2",
    description: "PO-orchestrated Phase 1–2: SIP engine + XIRR, FastAPI, external-clear SIP Lab UI",
    when_to_use: "Build real monthly SIP backtest and a first-time-visitor-friendly SIP Lab UI",
    phases: [
        #{ title: "Inventory", detail: "API/UI/engine gap map" },
        #{ title: "Design", detail: "SIP Lab UX + external-user copy" },
        #{ title: "Engine", detail: "SIP schedule, units, cashflows, XIRR, goldens" },
        #{ title: "API", detail: "strategies list + POST SIP backtest" },
        #{ title: "Frontend", detail: "SIP Lab page + nav + clarity" },
        #{ title: "Clarity", detail: "First-time visitor polish pass" },
        #{ title: "Verify", detail: "pytest + npm build + DoD" },
        #{ title: "Synthesis", detail: "PO build report" },
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

let skip_approval = false;
if args != () {
    if args.skip_approval != () { skip_approval = truthy(args.skip_approval); }
}

let binding = "";
binding += "PRODUCT: SIP Lab / Basket Backtest Engine.\n";
binding += "GOAL: External visitor understands and runs a monthly SIP basket backtest without prior knowledge.\n";
binding += "PRIMARY METRIC: XIRR (not v0 weight-NAV total return).\n";
binding += "SIP DAY: fixed calendar day-of-month → next trading day if market closed.\n";
binding += "COSTS: zero MVP. XIRR golden tolerance abs ≤ 1e-4.\n";
binding += "HISTORY: Upstox only for real claims; sample/synthetic OK if labeled demo. NO yfinance/bhavcopy/Fyers.\n";
binding += "OUT OF SCOPE: Coin/MF, Kite import UI, live trading, orders.\n";
binding += "REUSE: strategies/ models, market_data/UpstoxProvider, calc/ risk helpers, FastAPI, Next.js AppShell, Recharts.\n";
binding += "DO NOT repurpose POST /backtest rebalance as SIP. New SIP path required.\n";
binding += "UI clarity: plain language, methodology accordion, data-source chip, empty/error/loading, Dashboard link to SIP Lab.\n";

let po = "";
po += "You are a specialist under Product Owner (AGENTS.md + .grok/agents/*). Do not address the end user.\n";
po += "Inspect the repo with tools before editing. Keep diffs focused. Never commit secrets.\n";

// ════════════════════════════════════════════════════════════════════════════
phase("Inventory");
// ════════════════════════════════════════════════════════════════════════════

let inv_schema = #{
    "type": "object",
    "required": ["summary", "api_routes", "ui_routes", "engine_status", "blockers"],
    "properties": #{
        "summary": #{ "type": "string" },
        "api_routes": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 30 },
        "ui_routes": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 15 },
        "engine_status": #{ "type": "string" },
        "blockers": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "price_path": #{ "type": "string" },
    },
};

let inv_p = "";
inv_p += po + "\n" + binding + "\n";
inv_p += "READ-ONLY inventory: map API routes, UI pages, strategies/, market_data/, calc/, curated prices availability.\n";
inv_p += "State whether SIP engine exists. List blockers for Phase 1–2. Do not edit files.\n";

let inv = agent(inv_p, #{
    label: "inventory-sip-ui",
    agent_type: "explore",
    capability_mode: "read-only",
    output_schema: inv_schema,
});
let inv_json = "{}";
if agent_ok(inv) && inv.output != () {
    inv_json = json_encode(inv.output);
}
log("Inventory done");

// ════════════════════════════════════════════════════════════════════════════
phase("Design");
// ════════════════════════════════════════════════════════════════════════════

let des_p = "";
des_p += po + "\n" + binding + "\n";
des_p += "You are the Design agent. Inventory: " + inv_json + "\n\n";
des_p += "UPDATE docs/design/pages/sip-lab.md for IMPLEMENTATION readiness:\n";
des_p += "1) Page sections top-to-bottom for first-time visitors (hero, configure, results, how-to-read, data source).\n";
des_p += "2) Exact copy strings for: hero, XIRR definition one-liner, invested vs final value, demo vs Upstox warning.\n";
des_p += "3) Empty / error / loading states.\n";
des_p += "4) Nav order with SIP Lab; Dashboard callout to SIP Lab.\n";
des_p += "5) Component list mapping to existing MetricCard, charts, tables.\n";
des_p += "Also write docs/design/copy/sip-lab-external.md — glossary for non-experts (XIRR, SIP, drawdown, basket).\n";
des_p += "No React code in this phase.\n";

let des = agent(des_p, #{
    label: "design-sip-lab",
    agent_type: "design",
    capability_mode: "all",
    phase: "Design",
});
log("Design: " + (if agent_ok(des) { "ok" } else { "failed" }));

if !skip_approval {
    await_user(
        "user",
        "Design docs ready under docs/design/pages/sip-lab.md. Resume to implement SIP engine + API + UI.",
    );
}

// ════════════════════════════════════════════════════════════════════════════
phase("Engine");
// ════════════════════════════════════════════════════════════════════════════

let eng_jobs = [];

let analyst_p = "";
analyst_p += po + "\n" + binding + "\n";
analyst_p += "You are the Data Analyst. Implement pure SIP math + XIRR.\n";
analyst_p += "Create package under src/smallcase_finance/sip/ (or calc/sip_*) with:\n";
analyst_p += "1) sip_schedule(day_of_month, start, end, trading_dates) → contribution dates (next trading day rule)\n";
analyst_p += "2) run_sip_simulation(weights, prices, amount, schedule) → units path, MV series, cashflows\n";
analyst_p += "3) xirr(cashflows) with documented method; secondary total_invested, final_value, max_drawdown on MV\n";
analyst_p += "4) tests/test_sip_xirr.py golden fixtures abs error ≤ 1e-4; synthetic prices OK if labeled\n";
analyst_p += "5) docs/analytics/sip-xirr.md short methodology\n";
analyst_p += "Read strategies/models.py and docs/architecture/sip-engine.md. Zero costs. Equity/ETF only.\n";
analyst_p += "Run pytest on new tests and fix until green.\n";

eng_jobs.push(#{
    prompt: analyst_p,
    label: "engine-xirr-analyst",
    agent_type: "data-analyst",
    capability_mode: "all",
    phase: "Engine",
});

let be_eng_p = "";
be_eng_p += po + "\n" + binding + "\n";
be_eng_p += "You are the Backend agent supporting the SIP engine.\n";
be_eng_p += "1) Price panel loader from curated Parquet (data_access) for strategy symbols\n";
be_eng_p += "2) services/sip_service.py: load StrategyConfig + prices → call sip engine → result DTO\n";
be_eng_p += "3) Detect data_source: upstox if curated prices source is upstox / token path, else sample\n";
be_eng_p += "4) Warnings list for missing symbols/gaps\n";
be_eng_p += "5) Unit tests for service with fixture prices (no live network)\n";
be_eng_p += "Coordinate with sip/ modules the analyst adds; glue imports if needed.\n";
be_eng_p += "Run pytest and fix breakages you cause.\n";

eng_jobs.push(#{
    prompt: be_eng_p,
    label: "engine-service-backend",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Engine",
});

let eng_results = parallel(eng_jobs);
let eng_ok = 0;
for r in eng_results {
    if agent_ok(r) { eng_ok += 1; }
}
log("Engine parallel: " + eng_ok.to_string() + "/" + eng_results.len().to_string());

let eng_glue = "";
eng_glue += po + "\n" + binding + "\n";
eng_glue += "ENGINE GLUE: Ensure sip modules + sip_service import cleanly; pytest for sip/xirr green.\n";
eng_glue += "If analyst and backend overlapped, resolve conflicts. No live Upstox in unit tests.\n";
let eng_g = agent(eng_glue, #{
    label: "engine-glue",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Engine",
});
log("Engine glue: " + (if agent_ok(eng_g) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("API");
// ════════════════════════════════════════════════════════════════════════════

let api_p = "";
api_p += po + "\n" + binding + "\n";
api_p += "Implement FastAPI for SIP Lab:\n";
api_p += "1) GET /strategies — list config/strategies/*.yaml (id, name, summary fields)\n";
api_p += "2) GET /strategies/{id} — full validated config\n";
api_p += "3) POST /backtests/sip — body: strategy_id and/or inline overrides (amount, day, start, end);\n";
api_p += "   response: xirr, total_invested, final_value, max_drawdown, series, cashflows, data_source, assumptions, warnings\n";
api_p += "4) Pydantic schemas under schemas/; register routers in main.py; CORS unchanged\n";
api_p += "5) docs/api.md section for SIP; tests/test_sip_api.py smoke (sample prices OK)\n";
api_p += "6) Never return secrets. 4xx on invalid config.\n";
api_p += "Do not break existing smallcases/metrics routes.\n";
api_p += "Run pytest -q.\n";

let api_r = agent(api_p, #{
    label: "api-sip-routes",
    agent_type: "backend",
    capability_mode: "all",
    phase: "API",
});
log("API: " + (if agent_ok(api_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Frontend");
// ════════════════════════════════════════════════════════════════════════════

let fe_p = "";
fe_p += po + "\n" + binding + "\n";
fe_p += "You are the Frontend agent. Implement SIP Lab UI for first-time external visitors.\n";
fe_p += "Read docs/design/pages/sip-lab.md and docs/design/copy/sip-lab-external.md and docs/api.md.\n";
fe_p += "REQUIREMENTS:\n";
fe_p += "1) apps/web route /sip-lab with hero (what is this), configure form (strategy select, amount, day, start/end), Run button\n";
fe_p += "2) Results: XIRR hero MetricCard(s), total invested, final value, max DD; PerformanceChart for MV series;\n";
fe_p += "   cashflows table; data_source chip (upstox vs sample/demo); warnings list; methodology accordion\n";
fe_p += "3) Export JSON and/or CSV client-side from response\n";
fe_p += "4) AppShell nav: add SIP Lab; keep Dashboard/Holdings/Performance\n";
fe_p += "5) Dashboard callout linking to /sip-lab explaining SIP vs basket NAV view\n";
fe_p += "6) lib/api.ts types + fetch helpers for strategies + POST sip backtest\n";
fe_p += "7) Loading/error/empty states with plain language\n";
fe_p += "8) npm run build must succeed\n";
fe_p += "Dark finance UI, Tailwind, existing components. No fake metrics if API fails.\n";

let fe_r = agent(fe_p, #{
    label: "frontend-sip-lab",
    agent_type: "frontend",
    capability_mode: "all",
    phase: "Frontend",
});
log("Frontend: " + (if agent_ok(fe_r) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Clarity");
// ════════════════════════════════════════════════════════════════════════════

let clar_des = "";
clar_des += po + "\n" + binding + "\n";
clar_des += "Review the implemented /sip-lab UI code and Dashboard callout as Design agent.\n";
clar_des += "Write docs/design/reviews/sip-lab-clarity-review.md with concrete UX issues for first-time users\n";
clar_des += "(missing labels, jargon, hierarchy, empty states). Max 12 prioritized fixes. Read the actual TSX files.\n";

let clar_d = agent(clar_des, #{
    label: "clarity-design-review",
    agent_type: "design",
    capability_mode: "all",
    phase: "Clarity",
});
log("Clarity review: " + (if agent_ok(clar_d) { "ok" } else { "failed" }));

let clar_fe = "";
clar_fe += po + "\n" + binding + "\n";
clar_fe += "Apply the highest-impact fixes from docs/design/reviews/sip-lab-clarity-review.md if present;\n";
clar_fe += "otherwise improve first-time clarity yourself (hero, XIRR tooltip/help, demo banner, methodology).\n";
clar_fe += "npm run build must still pass.\n";

let clar_f = agent(clar_fe, #{
    label: "clarity-frontend-fix",
    agent_type: "frontend",
    capability_mode: "all",
    phase: "Clarity",
});
log("Clarity fix: " + (if agent_ok(clar_f) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Verify");
// ════════════════════════════════════════════════════════════════════════════

let ver_schema = #{
    "type": "object",
    "required": ["passed", "failed", "ready_for_user", "notes"],
    "properties": #{
        "passed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
        "failed": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
        "ready_for_user": #{ "type": "boolean" },
        "notes": #{ "type": "string" },
    },
};

let ver_jobs = [];

let ver_be = "";
ver_be += po + "\n" + binding + "\n";
ver_be += "VERIFY backend DoD: run pytest -q; hit SIP API with TestClient if possible;\n";
ver_be += "confirm XIRR tests exist and pass; fix critical failures only.\n";
ver_be += "Return structured passed/failed vs: xirr goldens, sip service, strategies API, sip POST, no secrets leak.\n";

ver_jobs.push(#{
    prompt: ver_be,
    label: "verify-backend",
    agent_type: "backend",
    capability_mode: "all",
    output_schema: ver_schema,
    phase: "Verify",
});

let ver_fe = "";
ver_fe += po + "\n" + binding + "\n";
ver_fe += "VERIFY frontend: npm run build in apps/web; ensure /sip-lab page exists and imports resolve.\n";
ver_fe += "Check nav includes SIP Lab. Fix build breakages. Return structured passed/failed.\n";
ver_fe += "ready_for_user=true only if build OK and page present.\n";

ver_jobs.push(#{
    prompt: ver_fe,
    label: "verify-frontend",
    agent_type: "frontend",
    capability_mode: "all",
    output_schema: ver_schema,
    phase: "Verify",
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
log("Verify passed=" + all_passed.len().to_string() + " failed=" + all_failed.len().to_string());

if all_failed.len() > 0 {
    let fix_p = "";
    fix_p += po + "\n";
    fix_p += "Fix critical verification failures: " + json_encode(all_failed) + "\n";
    fix_p += "Re-run pytest and/or npm build as needed. Keep scope to SIP Lab path.\n";
    let fix_r = agent(fix_p, #{
        label: "verify-fix",
        agent_type: "backend",
        capability_mode: "all",
        phase: "Verify",
    });
    log("Fix: " + (if agent_ok(fix_r) { "ok" } else { "failed" }));
}

// ════════════════════════════════════════════════════════════════════════════
phase("Synthesis");
// ════════════════════════════════════════════════════════════════════════════

let syn_p = "";
syn_p += "Product Owner synthesis. Inspect sip engine, API routes, apps/web/sip-lab, tests.\n";
syn_p += "Write docs/build-report-sip-lab-ui.md: what shipped, how to run (pipeline, api, web, open /sip-lab),\n";
syn_p += "how to read XIRR, demo vs Upstox, limitations, verification notes.\n";
syn_p += "Update PRODUCT.md / ROADMAP checkboxes for Phase 1–2 if accurate.\n";
syn_p += "passed=" + json_encode(all_passed) + " failed=" + json_encode(all_failed) + "\n";
syn_p += "Only claim what exists.\n";

let syn = agent(syn_p, #{
    label: "po-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Synthesis",
});

let report = text_out(syn);
let path = write_scratch_file("sip-lab-ui-report.md", report);
if report == "" {
    path = write_scratch_file(
        "sip-lab-ui-report.md",
        "# SIP Lab Phase 1–2 finished\n\nSee docs/build-report-sip-lab-ui.md and open /sip-lab\n",
    );
}

complete(#{
    summary: "SIP Lab Phase 1–2 workflow finished (engine + API + UI)",
    report_path: path,
    ready_for_user: ready,
    verification_passed_count: all_passed.len(),
    verification_failed_count: all_failed.len(),
    verification_failed: all_failed,
    how_to_run: "make pipeline && make api & make web → http://localhost:3000/sip-lab",
    primary_metric: "XIRR",
    workflow: "sip-lab-phase1-2",
});
