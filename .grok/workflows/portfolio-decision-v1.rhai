let meta = #{
    name: "portfolio-decision-v1",
    description: "Implement PRD Portfolio Decision v1: Kite portfolio + Decision Lab APIs/UI",
    when_to_use: "Build or re-verify portfolio holdings + decide-backtest slice from the PRD",
    phases: [
        #{ title: "Inventory", detail: "Gap map vs PRD" },
        #{ title: "Backend", detail: "Portfolio + decision services" },
        #{ title: "Frontend", detail: "/portfolio /decide nav" },
        #{ title: "Verify", detail: "pytest + typecheck" },
        #{ title: "Synthesis", detail: "Build report" },
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

let skip_approval = false;
if args != () {
    if args.skip_approval != () { skip_approval = truthy(args.skip_approval); }
}

let binding = "";
binding += "PRD: docs/product/prd-portfolio-decision-v1.md. ADR 007. Upstox sole OHLCV (ADR 005).\n";
binding += "IN: Kite portfolio snapshot APIs + UI; Decision Lab SIP+benchmark+DQ+weight gap; nav Portfolio/Decide.\n";
binding += "OUT: Coin, trading, yfinance, multi-user. Reuse SipService — do not invent a third engine.\n";
binding += "Never commit .env or real holdings. Push only if explicitly asked; prefer main when founder requests.\n";

let po = "You are a specialist under AGENTS.md Product Owner. Use tools; do not address the end user.\n";

phase("Inventory");
let inv = agent(
    po + binding + "READ-ONLY: list existing kite/, sip, web routes, gaps vs PRD sections 4 and 9. No edits.",
    #{ label: "inventory-pdv1", agent_type: "explore", capability_mode: "read-only" },
);
log("Inventory: " + (if agent_ok(inv) { "ok" } else { "failed" }));

if !skip_approval {
    await_user("user", "Inventory done. Resume to implement backend + frontend.");
}

phase("Backend");
let be = agent(
    po + binding + "IMPLEMENT portfolio + decision backend per PRD: schemas, data_access/portfolio, "
        + "PortfolioService, DecisionService, routes /portfolio and /decisions, register in main.py, "
        + "tests with mocks/fixtures. pytest must pass for new tests.",
    #{ label: "backend-pdv1", agent_type: "backend", capability_mode: "all" },
);
log("Backend: " + (if agent_ok(be) { "ok" } else { "failed" }));

phase("Frontend");
let fe = agent(
    po + binding + "IMPLEMENT /portfolio and /decide pages, AppShell nav (Portfolio + Decision Lab primary), "
        + "api.ts + types. Reuse MetricCard, ErrorBanner, PerformanceChart variant=equity. Demo banners for sample data.",
    #{ label: "frontend-pdv1", agent_type: "frontend", capability_mode: "all" },
);
log("Frontend: " + (if agent_ok(fe) { "ok" } else { "failed" }));

phase("Verify");
let ver = agent(
    po + binding + "Run pytest -q from repo root. Fix failures. Optionally apps/web tsc --noEmit. Report pass/fail.",
    #{ label: "verify-pdv1", agent_type: "backend", capability_mode: "all" },
);
log("Verify: " + (if agent_ok(ver) { "ok" } else { "failed" }));

phase("Synthesis");
let syn = agent(
    po + binding + "Update or write docs/build-report-portfolio-decision-v1.md summarizing files changed and how to run. "
        + "Do not push git unless args say so.",
    #{ label: "synthesis-pdv1", agent_type: "general-purpose", capability_mode: "all" },
);

complete(#{
    summary: "portfolio-decision-v1 workflow finished",
    inventory_ok: agent_ok(inv),
    backend_ok: agent_ok(be),
    frontend_ok: agent_ok(fe),
    verify_ok: agent_ok(ver),
    synthesis_ok: agent_ok(syn),
});
