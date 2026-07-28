let meta = #{
    name: "author-and-backtest-smallcase",
    description: "Scope and plan: create a smallcase on the platform and backtest it with Upstox (or labeled sample) history — NOT Kite Phase 4",
    when_to_use: "User wants author-basket + historical backtest on this app; Upstox token may be delayed",
    phases: [
        #{ title: "Frame", detail: "correct roadmap slot vs Phase 4 Kite" },
        #{ title: "Inventory", detail: "what already exists for create + backtest + prices" },
        #{ title: "Gaps", detail: "missing create API/UI and price-path wiring" },
        #{ title: "Plan", detail: "sliced implementation plan with free-tier constraints" },
        #{ title: "Verify", detail: "adversarial check of plan against non-goals" },
        #{ title: "Synthesize", detail: "PO report for founder" },
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

fn agent_ok(r) {
    r != () && r.success == true
}

fn text_out(r) {
    if !agent_ok(r) { return ""; }
    if type_of(r.output) == "string" { return trimmed(r.output); }
    if r.output != () { return json_encode(r.output); }
    ""
}

// ── Binding product frame (always inject into prompts) ─────────────────────
let frame = "";
frame += "PRODUCT: SIP Lab / Basket Backtest Engine (smallcase-finance).\n";
frame += "FOUNDER FEATURE (this workflow): User creates a custom smallcase/basket ON THIS PLATFORM ";
frame += "(constituents + weights + optional SIP params), then the app backtests historical performance ";
frame += "using Upstox historical OHLCV when UPSTOX_ACCESS_TOKEN is set; otherwise labeled SAMPLE prices for demos.\n";
frame += "THIS IS NOT PHASE 4. Phase 4 = Kite Connect read-only equity holdings import vs strategy SIP.\n";
frame += "THIS IS NOT smallcase.com Gateway publisher/invest APIs. Local authoring only.\n";
frame += "ROADMAP FIT: Authoring + SIP/backtest is Phase 0–2 (foundations, SIP engine XIRR, API/UI). ";
frame += "Upstox prices = sole real history (ADR 005). Sample = demo only.\n";
frame += "NON-GOALS: live trading, orders, F&O, multi-user SaaS auth, yfinance/bhavcopy/Fyers, Coin/MF, Gateway partner deal.\n";
frame += "CONSTRAINT: Upstox access token may not be available yet — plan must work with sample data first and upgrade to Upstox when token arrives.\n";
frame += "REUSE: config/strategies YAML, strategies/loader, market_data/UpstoxProvider, POST /backtests/sip, GET /strategies, ";
frame += "v0 smallcase JSON under data/raw/smallcases, pipeline, Next.js AppShell, make sync-upstox.\n";
frame += "Repo root is the workspace. Use read_file, grep, list_dir. Never invent file contents.\n";

let po = "You are a specialist under the Product Owner. Do not address the end user. Inspect the repo with tools before answering.\n";

// ════════════════════════════════════════════════════════════════════════════
phase("Frame");
// ════════════════════════════════════════════════════════════════════════════

let frame_schema = #{
    "type": "object",
    "required": ["feature_name", "roadmap_phases", "not_in_scope", "summary"],
    "properties": #{
        "feature_name": #{ "type": "string" },
        "roadmap_phases": #{ "type": "string" },
        "not_in_scope": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "summary": #{ "type": "string" },
    },
};

let frame_p = "";
frame_p += po + frame + "\n";
frame_p += "TASK: Read docs/ROADMAP.md, PRODUCT.md (if present), docs/decisions/005-upstox-sole-market-data.md, ";
frame_p += "docs/integrations/kite-connect.md. Confirm in your own words that the founder feature is ";
frame_p += "author-basket + historical backtest (P0–P2), NOT Kite Phase 4. List explicit not-in-scope items.\n";

let frame_r = agent(frame_p, #{
    label: "frame:roadmap",
    capability_mode: "read-only",
    output_schema: frame_schema,
});

// ════════════════════════════════════════════════════════════════════════════
phase("Inventory");
// ════════════════════════════════════════════════════════════════════════════

let inv_schema = #{
    "type": "object",
    "required": ["summary", "create_path", "backtest_path", "price_path", "ui_path", "exists"],
    "properties": #{
        "summary": #{ "type": "string" },
        "create_path": #{ "type": "string" },
        "backtest_path": #{ "type": "string" },
        "price_path": #{ "type": "string" },
        "ui_path": #{ "type": "string" },
        "exists": #{
            "type": "object",
            "properties": #{
                "strategy_yaml": #{ "type": "boolean" },
                "sip_api": #{ "type": "boolean" },
                "create_api": #{ "type": "boolean" },
                "create_ui": #{ "type": "boolean" },
                "upstox_sync": #{ "type": "boolean" },
                "sample_fallback": #{ "type": "boolean" },
            },
        },
        "key_files": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 20 },
    },
};

let inv_jobs = [];

let inv_api = "";
inv_api += po + frame + "\n";
inv_api += "TASK: Inventory the API for authoring and backtest. Use grep/read_file on src/smallcase_finance/api/, services/, strategies/.\n";
inv_api += "Find: GET/POST strategies, POST /backtests/sip, POST /backtest (rebalance), integrations/upstox.\n";
inv_api += "Set exists.create_api true only if a write/create strategy endpoint exists (not just GET).\n";
inv_api += "Set exists.sip_api true if POST /backtests/sip exists. List key_files you opened.\n";
inv_api += "create_path / backtest_path = short description of current capability.\n";
inv_jobs.push(#{
    prompt: inv_api,
    label: "inv:api",
    capability_mode: "read-only",
    output_schema: inv_schema,
});

let inv_ui = "";
inv_ui += po + frame + "\n";
inv_ui += "TASK: Inventory the Next.js UI for creating a smallcase and running a backtest. ";
inv_ui += "Search apps/web/src for sip, strateg, smallcase, backtest, form, create. Read AppShell and any SIP Lab pages.\n";
inv_ui += "exists.create_ui true only if a user-facing form can CREATE a new basket (not only select existing).\n";
inv_ui += "ui_path = what a first-time user can do today. key_files = paths you opened.\n";
inv_jobs.push(#{
    prompt: inv_ui,
    label: "inv:ui",
    capability_mode: "read-only",
    output_schema: inv_schema,
});

let inv_data = "";
inv_data += po + frame + "\n";
inv_data += "TASK: Inventory price/data path for a newly authored basket. ";
inv_data += "Read docs/integrations/upstox.md, Makefile sync-upstox, integrations/upstox, market_data/, data/raw/smallcases examples, config/strategies/example-sip-equity.yaml.\n";
inv_data += "How does a new symbol list get OHLCV? Token optional? Sample fallback? exists.upstox_sync and exists.sample_fallback.\n";
inv_data += "price_path = end-to-end narrative. key_files = paths opened.\n";
inv_jobs.push(#{
    prompt: inv_data,
    label: "inv:data",
    capability_mode: "read-only",
    output_schema: inv_schema,
});

let inv_results = parallel(inv_jobs);

// ════════════════════════════════════════════════════════════════════════════
phase("Gaps");
// ════════════════════════════════════════════════════════════════════════════

let gaps_schema = #{
    "type": "object",
    "required": ["gaps", "mvp_slice", "token_delayed_mode"],
    "properties": #{
        "gaps": #{
            "type": "array",
            "maxItems": 12,
            "items": #{
                "type": "object",
                "required": ["area", "gap", "severity"],
                "properties": #{
                    "area": #{ "type": "string" },
                    "gap": #{ "type": "string" },
                    "severity": #{ "type": "string" },
                },
            },
        },
        "mvp_slice": #{ "type": "string" },
        "token_delayed_mode": #{ "type": "string" },
    },
};

let inv_blob = "";
let ii = 0;
for r in inv_results {
    inv_blob += "### Inventory panel " + ii.to_string() + "\n";
    inv_blob += text_out(r) + "\n\n";
    ii += 1;
}

let gaps_p = "";
gaps_p += po + frame + "\n";
gaps_p += "INVENTORY RESULTS (untrusted — re-check files if needed):\n";
gaps_p += inv_blob + "\n";
gaps_p += "TASK: List concrete gaps between 'create smallcase on platform + backtest with Upstox/sample history' and the inventory.\n";
gaps_p += "severity: blocker | important | nice-to-have.\n";
gaps_p += "mvp_slice: smallest shippable path for the founder (one paragraph).\n";
gaps_p += "token_delayed_mode: how the product works until UPSTOX_ACCESS_TOKEN is available (must be explicit sample labeling).\n";

let gaps_r = agent(gaps_p, #{
    label: "gaps:analyze",
    capability_mode: "read-only",
    output_schema: gaps_schema,
});

// ════════════════════════════════════════════════════════════════════════════
phase("Plan");
// ════════════════════════════════════════════════════════════════════════════

let plan_schema = #{
    "type": "object",
    "required": ["title", "slices", "acceptance", "out_of_scope"],
    "properties": #{
        "title": #{ "type": "string" },
        "slices": #{
            "type": "array",
            "maxItems": 8,
            "items": #{
                "type": "object",
                "required": ["id", "name", "agent", "work", "done_when"],
                "properties": #{
                    "id": #{ "type": "string" },
                    "name": #{ "type": "string" },
                    "agent": #{ "type": "string" },
                    "work": #{ "type": "string" },
                    "done_when": #{ "type": "string" },
                },
            },
        },
        "acceptance": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "out_of_scope": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 12 },
        "depends_on_token": #{ "type": "string" },
    },
};

let gaps_text = text_out(gaps_r);
let frame_text = text_out(frame_r);

let plan_p = "";
plan_p += po + frame + "\n";
plan_p += "FRAME:\n" + frame_text + "\n\nGAPS:\n" + gaps_text + "\n\n";
plan_p += "TASK: Produce an implementation plan of 4–8 ordered slices for the founder feature.\n";
plan_p += "Each slice: id (A1, A2…), name, agent (backend|frontend|data-engineer|design|data-architect), work, done_when.\n";
plan_p += "Prefer: (1) create/save strategy API to config/strategies or data/raw/smallcases, ";
plan_p += "(2) optional symbol-scoped Upstox sync when token present, ";
plan_p += "(3) wire SIP or rebalance backtest for authored basket, ";
plan_p += "(4) Next.js create form + run backtest UX with data-source banner, ";
plan_p += "(5) tests + sample path without token.\n";
plan_p += "Do NOT schedule Kite, Gateway, or live trading. Free-tier: local FastAPI + optional Vercel UI only.\n";
plan_p += "depends_on_token: what still works without a token vs what needs make sync-upstox.\n";

let plan_r = agent(plan_p, #{
    label: "plan:slices",
    capability_mode: "read-only",
    output_schema: plan_schema,
});

// ════════════════════════════════════════════════════════════════════════════
phase("Verify");
// ════════════════════════════════════════════════════════════════════════════

let verdict_schema = #{
    "type": "object",
    "required": ["ok", "issues", "evidence"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "issues": #{ "type": "array", "items": #{ "type": "string" }, "maxItems": 10 },
        "evidence": #{ "type": "string" },
    },
};

let plan_text = text_out(plan_r);

let vjobs = [];

let v1 = "";
v1 += po + "\nAdversarially review this plan. Fail if it smuggles Phase 4 Kite, Gateway partner APIs, live orders, or multi-provider prices.\n";
v1 += "Plan JSON:\n" + plan_text + "\n";
v1 += "Set ok=true only if out_of_scope is respected and slices stay on author+backtest+Upstox/sample. Cite evidence from the plan text.\n";
vjobs.push(#{
    prompt: v1,
    label: "verify:scope",
    capability_mode: "read-only",
    output_schema: verdict_schema,
});

let v2 = "";
v2 += po + "\nAdversarially review whether the plan works when UPSTOX_ACCESS_TOKEN is missing (founder waiting on portal token).\n";
v2 += "Plan JSON:\n" + plan_text + "\n";
v2 += "ok=true only if sample/demo path is explicit and not confused with real market claims. evidence required.\n";
vjobs.push(#{
    prompt: v2,
    label: "verify:token-delay",
    capability_mode: "read-only",
    output_schema: verdict_schema,
});

let v3 = "";
v3 += po + "\nRe-read repo inventory mentally from plan + open 1–2 key files if needed. Does the plan reinvent existing SIP/strategy loaders?\n";
v3 += "Plan:\n" + plan_text + "\nInventory:\n" + inv_blob + "\n";
v3 += "ok=true if plan reuses strategies/, POST /backtests/sip, make sync-upstox where they exist. evidence required.\n";
vjobs.push(#{
    prompt: v3,
    label: "verify:reuse",
    capability_mode: "read-only",
    output_schema: verdict_schema,
});

let verdicts = parallel(vjobs);

// ════════════════════════════════════════════════════════════════════════════
phase("Synthesize");
// ════════════════════════════════════════════════════════════════════════════

let report = "";
report += "# Author smallcase + backtest (Upstox/sample) — implementation scope\n\n";
report += "**Product correction:** This is **not** Phase 4 (Kite holdings). ";
report += "It is **create basket on this platform → historical SIP/backtest** using Upstox when token is ready, sample when not.\n\n";

report += "## Frame\n\n";
report += frame_text + "\n\n";

report += "## Inventory (API / UI / data)\n\n";
report += inv_blob + "\n";

report += "## Gaps\n\n";
report += gaps_text + "\n\n";

report += "## Implementation plan\n\n";
report += plan_text + "\n\n";

report += "## Verification\n\n";
let vi = 0;
for v in verdicts {
    report += "### Panel " + vi.to_string() + "\n";
    if agent_ok(v) {
        report += text_out(v) + "\n\n";
    } else {
        report += "_(verification panel failed or empty — treat as unverified)_\n\n";
    }
    vi += 1;
}

report += "## Founder next steps\n\n";
report += "1. Keep filling local `.env` when Upstox **Generate** token is ready; run `make sync-upstox` for real history.\n";
report += "2. Until then, develop create+backtest UX against **labeled sample** prices.\n";
report += "3. Implement plan slices in order (prefer backend create strategy → SIP backtest wire → UI form).\n";
report += "4. Do **not** start Kite Phase 4 until SIP Lab create+backtest is usable.\n";
report += "5. Optional: run existing workflow `sip-lab-phase1-2` to build engine/API/UI if not already shipped.\n";

let path = write_scratch_file("author-backtest-plan.md", report);
log("Wrote " + path);

complete(#{
    path: path,
    summary: "Scoped author-smallcase + Upstox/sample backtest (not Kite Phase 4)",
    report: report,
});
