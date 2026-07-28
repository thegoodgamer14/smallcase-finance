let meta = #{
    name: "sip-lab-roadmap",
    description: "PRD-driven SIP Lab roadmap: Upstox-only historical data, deferred Coin/MF, Kite equity later, SIP engine sequencing, docs + Phase 0 scaffold",
    when_to_use: "After SIP Lab PRD approval with Upstox as sole price source",
    phases: [
        #{ title: "Inventory", detail: "Map repo vs SIP Lab PRD gaps" },
        #{ title: "Research", detail: "Upstox historical + auth; Kite equity later notes" },
        #{ title: "Decisions", detail: "Lock ADR decisions (Upstox-only history)" },
        #{ title: "Roadmap", detail: "PRODUCT, ROADMAP, backlog, condensed PRD" },
        #{ title: "Architecture", detail: "SIP engine + Upstox data + UI wireframes" },
        #{ title: "Approval", detail: "Human gate before scaffold" },
        #{ title: "Scaffold", detail: "Strategy config + Upstox-as-sole provider stubs" },
        #{ title: "Synthesis", detail: "PO hand-off report" },
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
let do_scaffold = true;
if args != () {
    if args.skip_approval != () { skip_approval = truthy(args.skip_approval); }
    if args.scaffold != () { do_scaffold = truthy(args.scaffold); }
}

// Binding product decisions (founder-approved 2026-07-28)
let prd = "";
prd += "PRODUCT: SIP Lab / Basket Backtest Engine (evolution of smallcase-finance v0).\n";
prd += "VISION: Monthly SIP performance of custom stock/ETF baskets; XIRR primary; reproducible.\n";
prd += "FOUNDER: equities on Kite; Coin MF deferred (no Coin/MF APIs this version); authors smallcase baskets.\n";
prd += "COMPARE (later): live portfolio vs SIP backtest of strategy — Kite equity import is Phase 4, not this workflow's full impl.\n";
prd += "HISTORICAL DATA (BINDING): Upstox API is the SOLE source of equity/ETF historical OHLCV.\n";
prd += "  - NO yfinance, NO bhavcopy, NO Fyers fallbacks in this product version.\n";
prd += "  - User will provide Upstox API key / client ID / secret; access token from Upstox developer portal.\n";
prd += "  - Env: UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_ACCESS_TOKEN (and any official names from Upstox docs).\n";
prd += "  - Extend existing src/smallcase_finance/integrations/upstox/ — write TO Upstox API contracts.\n";
prd += "  - Document auth flow from Upstox developer portal accurately.\n";
prd += "COIN / MF: planned later; DO NOT implement Coin import APIs, MF holdings endpoints, or MF NAV engine now.\n";
prd += "REPO: remains PUBLIC; never commit secrets.\n";
prd += "NON-GOALS: live trading, F&O, paid multi-provider sprawl, multi-user social.\n";
prd += "ORDER: correct SIP engine first, UI second, Kite equity import later, Coin last.\n";
prd += "SIP defaults: fixed calendar day → next trading day; zero costs MVP; XIRR fixture tolerance 1e-4.\n";
prd += "Reuse v0: FastAPI, Next.js, pipeline, calc modules, Upstox client, sample smallcases.\n";

let po = "";
po += "You are a specialist under Product Owner (AGENTS.md). Do not address the end user.\n";
po += "Inspect the repo with tools before editing. No live trading. No Coin/MF APIs. No yfinance.\n";
po += "Never commit secrets. Prefer small diffs.\n";

// ════════════════════════════════════════════════════════════════════════════
phase("Inventory");
// ════════════════════════════════════════════════════════════════════════════

let inv_schema = #{
    "type": "object",
    "required": ["summary", "reuse", "gaps", "risks"],
    "properties": #{
        "summary": #{ "type": "string" },
        "reuse": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
        "gaps": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 25 },
        "risks": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 15 },
    },
};

let inv_p = "";
inv_p += po + "\n" + prd + "\n";
inv_p += "INVENTORY (read-only): Compare current smallcase-finance repo to SIP Lab needs.\n";
inv_p += "Read PRODUCT.md, README, docs/architecture, docs/build-report, calc/, integrations/upstox/, API, apps/web.\n";
inv_p += "Return summary, REUSE list, GAPS (SIP, XIRR, units, strategy config, Upstox-as-sole, Kite later), risks.\n";
inv_p += "Do not edit files.\n";

let inv = agent(inv_p, #{
    label: "inventory-prd-gap",
    agent_type: "explore",
    capability_mode: "read-only",
    output_schema: inv_schema,
});
let inv_json = "{}";
if agent_ok(inv) && inv.output != () {
    inv_json = json_encode(inv.output);
}
log("Inventory complete");

// ════════════════════════════════════════════════════════════════════════════
phase("Research");
// ════════════════════════════════════════════════════════════════════════════

let res_jobs = [];

let upstox_p = "";
upstox_p += po + "\n" + prd + "\n";
upstox_p += "RESEARCH Upstox as SOLE historical market data provider for this product.\n";
upstox_p += "Use web_search/open_page on official Upstox developer docs (API v2/v3 historical candles, auth, instruments).\n";
upstox_p += "Also read existing src/smallcase_finance/integrations/upstox/* and docs/integrations/upstox*.md.\n";
upstox_p += "Write/overwrite docs/integrations/upstox.md as the canonical guide:\n";
upstox_p += "1) Developer portal setup: API key, API secret, client ID if applicable, how to obtain access token\n";
upstox_p += "2) Exact env var names for this project\n";
upstox_p += "3) Historical candle endpoint(s), path params, intervals (day), date range limits, rate limits\n";
upstox_p += "4) instrument_key resolution (NSE_EQ|ISIN) and our map file\n";
upstox_p += "5) Response mapping → our price schema (symbol, date, OHLCV, source=upstox)\n";
upstox_p += "6) CLI make sync-upstox / python -m ... with --years and --from/--to\n";
upstox_p += "7) Explicit: no alternate historical providers in this version; without token, sample data only for demo\n";
upstox_p += "8) Security: never commit tokens\n";
upstox_p += "Update docs/integrations/upstox-research.md if needed for endpoint accuracy.\n";

res_jobs.push(#{
    prompt: upstox_p,
    label: "research-upstox-sole",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Research",
});

let kite_note_p = "";
kite_note_p += po + "\n" + prd + "\n";
kite_note_p += "Write docs/integrations/kite-connect.md as a FUTURE plan only (Phase 4+).\n";
kite_note_p += "Cover: Kite equities holdings import later; Coin MF deferred further; no order placement.\n";
kite_note_p += "State clearly: THIS VERSION implements NO Kite/Coin runtime APIs and NO MF import.\n";
kite_note_p += "Link to kite.trade docs and pykiteconnect for future implementers.\n";
kite_note_p += "MCP kite_connect_api may be used by agents later for mapping validation — not product runtime.\n";
kite_note_p += "Keep the doc short. Do not add Python kite client code in this step.\n";

res_jobs.push(#{
    prompt: kite_note_p,
    label: "research-kite-future",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Research",
});

let res_results = parallel(res_jobs);
let res_ok = 0;
for r in res_results {
    if agent_ok(r) { res_ok += 1; }
}
log("Research: " + res_ok.to_string() + "/" + res_results.len().to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Decisions");
// ════════════════════════════════════════════════════════════════════════════

let dec_p = "";
dec_p += po + "\n" + prd + "\n";
dec_p += "Inventory (untrusted): " + inv_json + "\n\n";
dec_p += "Write docs/decisions/004-sip-lab-prd-decisions.md locking founder-approved decisions:\n";
dec_p += "1) Historical prices: Upstox ONLY — no yfinance/bhavcopy/Fyers in this version\n";
dec_p += "2) SIP day rule: fixed calendar day → next trading day\n";
dec_p += "3) Costs: zero default MVP; optional later\n";
dec_p += "4) Coin/MF: deferred; no APIs this version\n";
dec_p += "5) Hosting: local-first; free-tier later\n";
dec_p += "6) XIRR tolerance: ≤ 1e-4 on golden fixtures\n";
dec_p += "7) Repo stays public; secrets via env only\n";
dec_p += "8) Kite equity import: Phase 4 roadmap only, not this version's implementation\n";
dec_p += "Also write docs/decisions/005-upstox-sole-market-data.md (ADR): sole provider, auth, cache, sample fallback for demos without token.\n";

let dec = agent(dec_p, #{
    label: "po-decisions",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Decisions",
});
log("Decisions: " + (if agent_ok(dec) { "ok" } else { "failed" }));

// ════════════════════════════════════════════════════════════════════════════
phase("Roadmap");
// ════════════════════════════════════════════════════════════════════════════

let road_jobs = [];

let prod_p = "";
prod_p += po + "\n" + prd + "\n";
prod_p += "Rewrite PRODUCT.md for SIP Lab positioning while preserving v0 shipped checklist.\n";
prod_p += "Emphasize: Upstox-only historical data; Coin deferred; public repo; phases linking to docs/ROADMAP.md.\n";
prod_p += "Read ADR 004/005 and honor them.\n";

road_jobs.push(#{
    prompt: prod_p,
    label: "update-product-md",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Roadmap",
});

let road_p = "";
road_p += po + "\n" + prd + "\n";
road_p += "Write docs/ROADMAP.md phases 0–4 with work packages, acceptance criteria, agent owners.\n";
road_p += "P0: strategy/SIP config, Upstox as MarketDataProvider sole impl, Parquet cache, secrets.\n";
road_p += "P1: SIP engine + XIRR golden tests (equity/ETF only).\n";
road_p += "P2: API + Next.js SIP UI + export.\n";
road_p += "P3: benchmark via Upstox, strategy compare, cost toggle, DQ warnings.\n";
road_p += "P4: Kite equity holdings import + portfolio vs strategy compare; Coin still later.\n";
road_p += "Write docs/product/prd-sip-lab.md condensed PRD summary.\n";
road_p += "Write docs/product/backlog-phase-0-2.md with id, title, agent, AC, deps, S/M/L.\n";

road_jobs.push(#{
    prompt: road_p,
    label: "write-roadmap-backlog",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Roadmap",
});

let road_results = parallel(road_jobs);
let road_ok = 0;
for r in road_results {
    if agent_ok(r) { road_ok += 1; }
}
log("Roadmap: " + road_ok.to_string() + "/" + road_results.len().to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Architecture");
// ════════════════════════════════════════════════════════════════════════════

let arch_jobs = [];

let arch_engine = "";
arch_engine += po + "\n" + prd + "\n";
arch_engine += "Write docs/architecture/sip-engine.md: StrategyConfig, SIP cashflows, next-trading-day,\n";
arch_engine += "units, rebalance, XIRR/CAGR/DD, contribution; extend existing calc/; golden tests.\n";
arch_engine += "Equity/ETF only. Data feed assumption: Upstox daily bars in Parquet cache.\n";
arch_engine += "Add docs/data-dictionary-sip.md for new entities.\n";

arch_jobs.push(#{
    prompt: arch_engine,
    label: "arch-sip-engine",
    agent_type: "data-architect",
    capability_mode: "all",
    phase: "Architecture",
});

let arch_int = "";
arch_int += po + "\n" + prd + "\n";
arch_int += "Write docs/architecture/integrations-overview.md with mermaid:\n";
arch_int += "Strategy → SIP Engine → Upstox provider → Parquet cache → metrics/UI.\n";
arch_int += "Phase 4 dashed: Kite equity import → portfolio snapshot → compare.\n";
arch_int += "NO multi-provider chain. API sketch: strategies, POST /backtests/sip, results export.\n";
arch_int += "Env table for Upstox credentials. Explicit non-goals: Coin APIs, orders, yfinance.\n";

arch_jobs.push(#{
    prompt: arch_int,
    label: "arch-integrations",
    agent_type: "backend",
    capability_mode: "all",
    phase: "Architecture",
});

let arch_ui = "";
arch_ui += po + "\n" + prd + "\n";
arch_ui += "Write docs/design/pages/sip-lab.md: strategy editor, SIP params, run backtest, XIRR results,\n";
arch_ui += "equity curve, contribution, methodology warnings, Upstox data-source status.\n";
arch_ui += "Skip Coin/portfolio-import screens for this version (note as future).\n";
arch_ui += "Reuse dark finance design system.\n";

arch_jobs.push(#{
    prompt: arch_ui,
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
log("Architecture: " + arch_ok.to_string() + "/" + arch_results.len().to_string());

// ════════════════════════════════════════════════════════════════════════════
phase("Approval");
// ════════════════════════════════════════════════════════════════════════════

if !skip_approval {
    await_user(
        "user",
        "Review PRODUCT.md, docs/ROADMAP.md, docs/decisions/004-sip-lab-prd-decisions.md, docs/architecture/sip-engine.md, docs/integrations/upstox.md. Resume for Phase 0 scaffold (Upstox-only; no Coin APIs).",
    );
}
log("Approval passed or skipped");

// ════════════════════════════════════════════════════════════════════════════
phase("Scaffold");
// ════════════════════════════════════════════════════════════════════════════

if do_scaffold {
    let sc_jobs = [];

    let sc_cfg = "";
    sc_cfg += po + "\n" + prd + "\n";
    sc_cfg += "PHASE 0 SCAFFOLD (no full SIP loop yet):\n";
    sc_cfg += "1) src/smallcase_finance/strategies/ — Pydantic StrategyConfig + SIPConfig; load YAML/JSON\n";
    sc_cfg += "2) config/strategies/example-sip-equity.yaml — sample equity SIP basket\n";
    sc_cfg += "3) src/smallcase_finance/market_data/ — Provider protocol with UpstoxProvider as the ONLY concrete provider\n";
    sc_cfg += "   Wire to existing integrations/upstox client where possible; no yfinance module at all\n";
    sc_cfg += "4) tests for config validation + provider interface shape\n";
    sc_cfg += "5) Update .env.example with Upstox portal credentials fields (placeholders only)\n";
    sc_cfg += "Do not implement full XIRR SIP engine. Do not add Kite/Coin code.\n";

    sc_jobs.push(#{
        prompt: sc_cfg,
        label: "scaffold-strategy-upstox",
        agent_type: "data-architect",
        capability_mode: "all",
        phase: "Scaffold",
    });

    let sc_up = "";
    sc_up += po + "\n" + prd + "\n";
    sc_up += "Harden Upstox integration for sole-provider role:\n";
    sc_up += "Read docs/integrations/upstox.md and existing integrations/upstox/*.\n";
    sc_up += "1) Align config/env names with Upstox developer portal (key, secret, access token)\n";
    sc_up += "2) Ensure status endpoint reports configured boolean only\n";
    sc_up += "3) market_data.UpstoxProvider delegates to sync/client\n";
    sc_up += "4) unit tests remain mocked HTTP\n";
    sc_up += "5) README blurb: historical data = Upstox only; set credentials then make sync-upstox\n";
    sc_up += "6) Run pytest -q and fix breakages\n";
    sc_up += "No Coin/Kite. No yfinance.\n";

    sc_jobs.push(#{
        prompt: sc_up,
        label: "scaffold-upstox-harden",
        agent_type: "backend",
        capability_mode: "all",
        phase: "Scaffold",
    });

    let sc_results = parallel(sc_jobs);
    let sc_ok = 0;
    for r in sc_results {
        if agent_ok(r) { sc_ok += 1; }
    }
    log("Scaffold: " + sc_ok.to_string() + "/" + sc_results.len().to_string());

    let glue = "";
    glue += po + "\n";
    glue += "Glue pass: imports, pyproject if needed, pytest -q green, pointer in README to docs/ROADMAP.md.\n";
    glue += "Remove any accidental yfinance references added in this run.\n";
    let glue_r = agent(glue, #{
        label: "scaffold-glue",
        agent_type: "backend",
        capability_mode: "all",
        phase: "Scaffold",
    });
    log("Glue: " + (if agent_ok(glue_r) { "ok" } else { "failed" }));
} else {
    log("Scaffold skipped");
}

// ════════════════════════════════════════════════════════════════════════════
phase("Synthesis");
// ════════════════════════════════════════════════════════════════════════════

let syn = "";
syn += "Write docs/build-report-sip-lab-plan.md — PO synthesis:\n";
syn += "Vision, Upstox-only history, Coin deferred, public repo, what shipped this run, Phase 0–2 next steps,\n";
syn += "how to configure Upstox credentials, risks. Inventory: " + inv_json + "\n";
syn += "Inspect actual files; only claim what exists.\n";

let syn_r = agent(syn, #{
    label: "po-synthesis",
    agent_type: "general-purpose",
    capability_mode: "all",
    phase: "Synthesis",
});

let report = text_out(syn_r);
let path = write_scratch_file("sip-lab-plan-report.md", report);
if report == "" {
    path = write_scratch_file(
        "sip-lab-plan-report.md",
        "# SIP Lab plan finished\n\nSee docs/ROADMAP.md and docs/build-report-sip-lab-plan.md\n",
    );
}

complete(#{
    summary: "SIP Lab roadmap locked: Upstox-only historical data; Coin deferred; docs + optional Phase 0 scaffold",
    report_path: path,
    history_provider: "upstox_only",
    coin_mf: "deferred",
    repo_visibility: "public",
    next_phase: "Phase 1 SIP engine + XIRR golden tests",
    how_to_configure_upstox: "Set UPSTOX_* from developer portal in .env; make sync-upstox YEARS=N",
    workflow: "sip-lab-roadmap",
});
