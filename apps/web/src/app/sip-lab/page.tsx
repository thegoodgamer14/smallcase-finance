"use client";

import { ChevronDown, Download, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PerformanceChart } from "@/components/charts/PerformanceChart";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { MetricCard } from "@/components/kpis/MetricCard";
import {
  DataSourceChip,
  isDemoSource,
  SipDataSourceBanner,
} from "@/components/sip/DataSourceChip";
import { exportSipCashflowsCsv, exportSipJson } from "@/components/sip/export";
import { HowToReadPanel } from "@/components/sip/HowToReadPanel";
import { MethodologyPanel } from "@/components/sip/MethodologyPanel";
import { SipCashflowTable } from "@/components/sip/SipCashflowTable";
import { SipHoldingTable } from "@/components/sip/SipHoldingTable";
import {
  ApiError,
  apiBase,
  getPriceUniverse,
  getStrategy,
  getUpstoxStatus,
  listStrategies,
  postSipBacktest,
} from "@/lib/api";
import { drawdownFromNav } from "@/lib/drawdown";
import {
  formatDate,
  formatInr,
  formatInrCompact,
  formatInrSigned,
  formatPercent,
  formatWeight,
} from "@/lib/format";
import {
  sentimentFromSigned,
  sentimentMaxDrawdown,
} from "@/lib/sentiment";
import type {
  ChartSeries,
  SipBacktestRequest,
  SipBacktestResponse,
  StrategyDetail,
  StrategySummary,
} from "@/lib/types";

type RunState = "idle" | "loading" | "success" | "error";
type ResultsTab = "cashflows" | "holdings";
type BasketMode = "pick" | "create";

interface BasketPeekRow {
  symbol: string;
  weight?: number | null;
}

interface CreateRow {
  symbol: string;
  weight: string;
}

function slugifyName(name: string): string {
  const s = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  return s || "custom-basket";
}

function defaultStartDate(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 3);
  return d.toISOString().slice(0, 10);
}

function mapSipError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return `Can’t reach the API at ${apiBase()}. Is the server running?`;
    }
    if (err.status === 404) {
      return `Invalid SIP config: ${err.message}`;
    }
    if (err.status === 400) {
      const detail = err.message.toLowerCase();
      if (
        detail.includes("price") ||
        detail.includes("history") ||
        detail.includes("symbol")
      ) {
        return err.message.includes("Not enough")
          ? err.message
          : `Not enough price history. Sync Upstox or shorten the date range. (${err.message})`;
      }
      return `Invalid SIP config: ${err.message}`;
    }
    if (err.status === 503) {
      return `Backtest failed. Price data missing — run the data pipeline or sync Upstox. (${err.message})`;
    }
    if (err.status === 408 || err.status === 504) {
      return "Backtest timed out. Try a shorter range or fewer symbols.";
    }
    return `Backtest failed. Retry or check API logs. (${err.message})`;
  }
  if (err instanceof Error) {
    return err.message || "Backtest failed. Retry or check API logs.";
  }
  return "Backtest failed. Retry or check API logs.";
}

function parseBasketPeek(detail: StrategyDetail | null): BasketPeekRow[] {
  if (!detail?.basket || typeof detail.basket !== "object") return [];
  const raw = detail.basket as {
    constituents?: Array<{
      symbol?: string;
      target_weight?: number | null;
      weight?: number | null;
    }>;
  };
  const list = raw.constituents;
  if (!Array.isArray(list)) return [];
  return list
    .filter((c): c is { symbol: string; target_weight?: number | null; weight?: number | null } =>
      Boolean(c && typeof c.symbol === "string" && c.symbol.length > 0),
    )
    .map((c) => ({
      symbol: c.symbol,
      weight: c.target_weight ?? c.weight ?? null,
    }));
}

function allocationLabel(mode: string | undefined): string {
  if (!mode) return "";
  if (mode === "equal_weight") return "equal weight";
  if (mode === "custom_weights") return "custom weights";
  return mode.replace(/_/g, " ");
}

function focusConfigure() {
  const el = document.getElementById("configure");
  el?.scrollIntoView({ behavior: "smooth", block: "start" });
  // Prefer amount field so keyboard users land in the form
  window.setTimeout(() => {
    const amount = document.getElementById("sip-amount");
    if (amount instanceof HTMLElement) {
      amount.focus();
      return;
    }
    const run = document.getElementById("sip-run");
    if (run instanceof HTMLElement) run.focus();
  }, 300);
}

export default function SipLabPage() {
  const [strategies, setStrategies] = useState<StrategySummary[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(true);
  const [strategiesError, setStrategiesError] = useState<string | null>(null);

  const [basketMode, setBasketMode] = useState<BasketMode>("pick");
  const [strategyId, setStrategyId] = useState("");
  const [createName, setCreateName] = useState("My custom basket");
  const [createEqual, setCreateEqual] = useState(true);
  const [createRows, setCreateRows] = useState<CreateRow[]>([
    { symbol: "TCS", weight: "0.25" },
    { symbol: "INFY", weight: "0.25" },
    { symbol: "RELIANCE", weight: "0.25" },
    { symbol: "HDFCBANK", weight: "0.25" },
  ]);
  const [priceUniverse, setPriceUniverse] = useState<string[]>([]);

  const [amount, setAmount] = useState(10000);
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [start, setStart] = useState(defaultStartDate);
  const [end, setEnd] = useState("");
  const [endLatest, setEndLatest] = useState(true);

  const [upstoxConfigured, setUpstoxConfigured] = useState<boolean | null>(
    null,
  );

  const [strategyDetail, setStrategyDetail] = useState<StrategyDetail | null>(
    null,
  );
  const [detailLoading, setDetailLoading] = useState(false);

  const [runState, setRunState] = useState<RunState>("idle");
  const [result, setResult] = useState<SipBacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [tab, setTab] = useState<ResultsTab>("cashflows");

  const lastBodyRef = useRef<SipBacktestRequest | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  // Load strategies + upstox status
  useEffect(() => {
    let cancelled = false;
    setStrategiesLoading(true);
    setStrategiesError(null);
    listStrategies()
      .then((res) => {
        if (cancelled) return;
        setStrategies(res.items);
        if (res.items.length && !strategyId) {
          const first = res.items[0];
          setStrategyId(first.id);
          setAmount(first.sip_amount || 10000);
          setDayOfMonth(first.day_of_month || 1);
          if (first.start_date) setStart(first.start_date);
          if (first.end_date) {
            setEnd(first.end_date);
            setEndLatest(false);
          }
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setStrategiesError(
            e instanceof ApiError
              ? e.message
              : e instanceof Error
                ? e.message
                : "Failed to load strategies",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setStrategiesLoading(false);
      });

    getUpstoxStatus()
      .then((s) => {
        if (!cancelled) setUpstoxConfigured(s.configured);
      })
      .catch(() => {
        if (!cancelled) setUpstoxConfigured(null);
      });

    getPriceUniverse()
      .then((u) => {
        if (!cancelled && u.symbols?.length) {
          setPriceUniverse(u.symbols);
          // Prefer universe defaults when creating
          const prefer = ["TCS", "INFY", "RELIANCE", "HDFCBANK"].filter((s) =>
            u.symbols.includes(s),
          );
          if (prefer.length >= 2) {
            const w = (1 / prefer.length).toFixed(4);
            setCreateRows(prefer.map((symbol) => ({ symbol, weight: w })));
          }
        }
      })
      .catch(() => {
        /* keep fallback rows */
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load basket composition when strategy changes
  useEffect(() => {
    if (!strategyId) {
      setStrategyDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    getStrategy(strategyId)
      .then((d) => {
        if (!cancelled) setStrategyDetail(d);
      })
      .catch(() => {
        if (!cancelled) setStrategyDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [strategyId]);

  // Mark results stale when params change after a successful run
  useEffect(() => {
    if (runState === "success" && result) setStale(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    basketMode,
    strategyId,
    createName,
    createEqual,
    createRows,
    amount,
    dayOfMonth,
    start,
    end,
    endLatest,
  ]);

  // Close export menu on outside click
  useEffect(() => {
    if (!exportOpen) return;
    function onDoc(e: MouseEvent) {
      if (
        exportRef.current &&
        !exportRef.current.contains(e.target as Node)
      ) {
        setExportOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [exportOpen]);

  const selectedStrategy = useMemo(
    () => strategies.find((s) => s.id === strategyId) ?? null,
    [strategies, strategyId],
  );

  const basketPeek = useMemo(
    () => parseBasketPeek(strategyDetail),
    [strategyDetail],
  );

  const amountInvalid = !(amount > 0);
  const dayInvalid = dayOfMonth < 1 || dayOfMonth > 28;
  const strategyInvalid = basketMode === "pick" && !strategyId;
  const endInvalid = !endLatest && (!end || end < start);

  const createSymbols = useMemo(
    () =>
      createRows
        .map((r) => r.symbol.trim().toUpperCase())
        .filter(Boolean),
    [createRows],
  );

  const createWeightSum = useMemo(() => {
    if (createEqual) return 1;
    return createRows.reduce((acc, r) => {
      const w = parseFloat(r.weight);
      return acc + (Number.isFinite(w) ? w : 0);
    }, 0);
  }, [createEqual, createRows]);

  const createInvalid =
    basketMode === "create" &&
    (createSymbols.length < 1 ||
      new Set(createSymbols).size !== createSymbols.length ||
      (!createEqual && Math.abs(createWeightSum - 1) > 0.02) ||
      !createName.trim());

  const formValid =
    !strategyInvalid &&
    !createInvalid &&
    !amountInvalid &&
    !dayInvalid &&
    Boolean(start) &&
    !endInvalid;

  const buildBody = useCallback((): SipBacktestRequest => {
    const body: SipBacktestRequest = {
      amount,
      day_of_month: dayOfMonth,
      start,
    };
    if (!endLatest && end) body.end = end;

    if (basketMode === "create") {
      const n = createSymbols.length || 1;
      const constituents = createRows
        .filter((r) => r.symbol.trim())
        .map((r) => {
          const symbol = r.symbol.trim().toUpperCase();
          const w = createEqual
            ? 1 / n
            : parseFloat(r.weight) || 0;
          return { symbol, target_weight: w };
        });
      body.strategy = {
        strategy_id: slugifyName(createName),
        name: createName.trim() || "Custom basket",
        currency: "INR",
        version: "1",
        allocation_mode: createEqual ? "equal_weight" : "custom_weights",
        price_field: "close",
        rebalance_mode: "none",
        fractional_units: true,
        basket: { kind: "inline", constituents },
        sip: {
          amount,
          day_of_month: dayOfMonth,
          start_date: start,
          end_date: endLatest || !end ? null : end,
          as_of: null,
        },
        costs: {
          brokerage_bps: 0,
          stt_bps: 0,
          slippage_bps: 0,
          flat_fee: 0,
        },
      };
    } else {
      body.strategy_id = strategyId;
    }
    return body;
  }, [
    basketMode,
    strategyId,
    createName,
    createEqual,
    createRows,
    createSymbols.length,
    amount,
    dayOfMonth,
    start,
    end,
    endLatest,
  ]);

  const runBacktest = useCallback(async () => {
    if (!formValid) return;
    const body = buildBody();
    lastBodyRef.current = body;
    setRunState("loading");
    setError(null);
    setStale(false);
    setExportOpen(false);
    try {
      const res = await postSipBacktest(body);
      setResult(res);
      setRunState("success");
      setTab("cashflows");
    } catch (e: unknown) {
      setError(mapSipError(e));
      setRunState("error");
      // Do not invent metrics on failure
    }
  }, [formValid, buildBody]);

  const onStrategyChange = (id: string) => {
    setStrategyId(id);
    const s = strategies.find((x) => x.id === id);
    if (s) {
      setAmount(s.sip_amount || 10000);
      setDayOfMonth(s.day_of_month || 1);
      if (s.start_date) setStart(s.start_date);
      if (s.end_date) {
        setEnd(s.end_date);
        setEndLatest(false);
      } else {
        setEndLatest(true);
        setEnd("");
      }
    }
  };

  const equitySeries: ChartSeries[] = useMemo(() => {
    if (!result?.series?.length) return [];
    return [
      {
        id: "mv",
        name: "Portfolio value",
        role: "portfolio",
        data: result.series.map((p) => ({
          date: p.date,
          value: p.market_value,
        })),
      },
      {
        id: "invested",
        name: "Cumulative invested",
        role: "benchmark",
        strokeDasharray: "6 4",
        data: result.series.map((p) => ({
          date: p.date,
          value: p.total_invested_to_date,
        })),
      },
    ];
  }, [result]);

  const drawdownSeries: ChartSeries[] = useMemo(() => {
    if (!result?.series?.length) return [];
    const navPts = result.series.map((p) => ({
      date: p.date,
      nav: p.market_value,
    }));
    return [
      {
        id: "dd",
        name: "Drawdown",
        role: "drawdown",
        data: drawdownFromNav(navPts),
      },
    ];
  }, [result]);

  const absoluteGain =
    result?.absolute_gain ??
    (result ? result.final_value - result.total_invested : null);

  const xirrSublabel = result
    ? `${formatDate(start)} → ${endLatest || !end ? "latest" : formatDate(end)} · SIP day ${dayOfMonth} → next session if closed`
    : undefined;

  const demoResult = result ? isDemoSource(result.data_source) : false;
  const idleOrDemo = demoResult || !result;

  const nNames =
    selectedStrategy?.n_constituents ??
    (basketPeek.length > 0 ? basketPeek.length : null);
  const modeLabel = allocationLabel(
    strategyDetail?.allocation_mode ?? selectedStrategy?.allocation_mode,
  );
  const peekTop = basketPeek.slice(0, 5);
  const peekMore = Math.max(0, basketPeek.length - peekTop.length);

  const inputClass =
    "w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:opacity-50";
  const labelClass = "block text-xs font-medium text-[var(--text-secondary)]";

  const preRunSourceCopy =
    upstoxConfigured === true
      ? "Real history available (Upstox). Results after run will say so."
      : upstoxConfigured === false
        ? "Demo prices — not live market performance. Connect Upstox for real history."
        : "Checking price source…";

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6 px-6 py-6">
      {/* §1 Hero */}
      <header id="hero" className="space-y-1">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">
          SIP Lab
        </h1>
        <p className="max-w-2xl text-sm text-[var(--text-secondary)]">
          See what a monthly SIP into a stock/ETF basket would have returned.
        </p>
        <p className="mt-1 text-sm text-[var(--text-primary)]">
          Primary result: XIRR — the annualized return on every contribution
          plus your ending portfolio value.
        </p>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          Equities & ETFs only · Zero transaction costs in this version · Not
          live trading
        </p>
        <a
          href="#methodology"
          className="mt-2 inline-block text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]"
        >
          How SIP Lab works
        </a>
      </header>

      {/* §2 Data source strip — single high-visibility note */}
      <div
        id="data-source"
        className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]"
      >
        <span className="text-[var(--text-muted)]">
          Real history: Upstox only. Sample data is labeled Demo.
        </span>
        {result ? (
          <DataSourceChip dataSource={result.data_source} />
        ) : (
          <span
            className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs ${
              upstoxConfigured
                ? "border-[var(--accent)]/40 bg-[var(--accent-subtle)] text-[var(--accent)]"
                : "border-[var(--risk-warning)]/50 bg-[var(--risk-warning)]/10 text-[var(--risk-warning)]"
            }`}
          >
            {preRunSourceCopy}
          </span>
        )}
      </div>

      {/* Config + Results */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* §3 Configure (sticky on xl) */}
        <aside
          id="configure"
          className="flex flex-col gap-4 xl:col-span-4 xl:sticky xl:top-20 xl:self-start"
        >
          <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
            <h2 className="text-sm font-medium text-[var(--text-primary)]">
              Basket
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Equities & ETFs only in this version.
            </p>

            {strategiesError ? (
              <div className="mt-3">
                <ErrorBanner message={strategiesError} />
              </div>
            ) : null}

            <div className="mt-3 flex gap-1 rounded-md bg-[var(--bg-muted)] p-0.5">
              {(
                [
                  ["pick", "Pick saved"],
                  ["create", "Create new"],
                ] as const
              ).map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  className={`flex-1 rounded px-2 py-1.5 text-xs font-medium transition-colors ${
                    basketMode === mode
                      ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm"
                      : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                  }`}
                  onClick={() => setBasketMode(mode)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="mt-3 space-y-3">
              {basketMode === "pick" ? (
              <div>
                <label htmlFor="sip-strategy" className={labelClass}>
                  SIP basket
                </label>
                <select
                  id="sip-strategy"
                  className={`${inputClass} mt-1`}
                  value={strategyId}
                  onChange={(e) => onStrategyChange(e.target.value)}
                  disabled={strategiesLoading || !strategies.length}
                  aria-invalid={strategyInvalid}
                >
                  {strategiesLoading ? (
                    <option value="">Loading baskets…</option>
                  ) : strategies.length === 0 ? (
                    <option value="">No baskets available</option>
                  ) : (
                    strategies.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {s.n_constituents
                          ? ` (${s.n_constituents} names)`
                          : ""}
                      </option>
                    ))
                  )}
                </select>
                {!strategiesLoading && strategies.length === 0 ? (
                  <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                    Start the API and ensure strategy configs are loaded.
                  </p>
                ) : null}
                {selectedStrategy?.summary ? (
                  <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                    {selectedStrategy.summary}
                  </p>
                ) : null}

                {/* Composition peek */}
                {strategyId && !detailLoading && (nNames != null || peekTop.length > 0) ? (
                  <div className="mt-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-muted)] px-2.5 py-2">
                    <p className="text-[11px] text-[var(--text-secondary)]">
                      {nNames != null ? `${nNames} equities/ETFs` : "Basket"}
                      {modeLabel ? ` · ${modeLabel}` : ""}
                    </p>
                    {peekTop.length > 0 ? (
                      <ul className="mt-1 space-y-0.5">
                        {peekTop.map((row) => (
                          <li
                            key={row.symbol}
                            className="flex justify-between gap-2 text-[11px] tabular-nums text-[var(--text-primary)]"
                          >
                            <span>{row.symbol}</span>
                            <span className="text-[var(--text-muted)]">
                              {row.weight != null
                                ? formatWeight(row.weight)
                                : "—"}
                            </span>
                          </li>
                        ))}
                        {peekMore > 0 ? (
                          <li className="text-[11px] text-[var(--text-muted)]">
                            +{peekMore} more
                          </li>
                        ) : null}
                      </ul>
                    ) : null}
                  </div>
                ) : detailLoading && strategyId ? (
                  <div className="mt-2 h-12 animate-pulse rounded-md bg-[var(--bg-muted)]" />
                ) : null}
              </div>
              ) : (
              <div className="space-y-3">
                <div>
                  <label htmlFor="create-name" className={labelClass}>
                    Basket name
                  </label>
                  <input
                    id="create-name"
                    className={`${inputClass} mt-1`}
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="My custom basket"
                  />
                </div>
                <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  <input
                    type="checkbox"
                    checked={createEqual}
                    onChange={(e) => setCreateEqual(e.target.checked)}
                  />
                  Equal weight (ignore weight column)
                </label>
                <div className="space-y-2">
                  {createRows.map((row, idx) => (
                    <div key={idx} className="flex gap-2">
                      {priceUniverse.length > 0 ? (
                        <select
                          className={`${inputClass} flex-1`}
                          value={row.symbol}
                          onChange={(e) => {
                            const next = [...createRows];
                            next[idx] = { ...row, symbol: e.target.value };
                            setCreateRows(next);
                          }}
                        >
                          {priceUniverse.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          className={`${inputClass} flex-1`}
                          value={row.symbol}
                          onChange={(e) => {
                            const next = [...createRows];
                            next[idx] = {
                              ...row,
                              symbol: e.target.value.toUpperCase(),
                            };
                            setCreateRows(next);
                          }}
                          placeholder="SYMBOL"
                        />
                      )}
                      {!createEqual ? (
                        <input
                          className={`${inputClass} w-20`}
                          value={row.weight}
                          onChange={(e) => {
                            const next = [...createRows];
                            next[idx] = { ...row, weight: e.target.value };
                            setCreateRows(next);
                          }}
                          placeholder="0.25"
                          aria-label="Weight"
                        />
                      ) : null}
                      <button
                        type="button"
                        className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                        onClick={() =>
                          setCreateRows(createRows.filter((_, i) => i !== idx))
                        }
                        disabled={createRows.length <= 1}
                        aria-label="Remove row"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  className="text-xs font-medium text-[var(--accent)] hover:underline"
                  onClick={() => {
                    const fallback =
                      priceUniverse.find(
                        (s) => !createRows.some((r) => r.symbol === s),
                      ) ||
                      priceUniverse[0] ||
                      "TCS";
                    setCreateRows([
                      ...createRows,
                      { symbol: fallback, weight: "0" },
                    ]);
                  }}
                >
                  + Add symbol
                </button>
                {!createEqual ? (
                  <p
                    className={`text-[11px] ${
                      Math.abs(createWeightSum - 1) > 0.02
                        ? "text-[var(--danger)]"
                        : "text-[var(--text-muted)]"
                    }`}
                  >
                    Weight sum: {createWeightSum.toFixed(3)} (need ≈ 1.0)
                  </p>
                ) : null}
                <p className="text-[11px] text-[var(--text-muted)]">
                  Symbols limited to curated prices
                  {priceUniverse.length
                    ? ` (${priceUniverse.length} available)`
                    : ""}. Sync Upstox for more:{" "}
                  <code className="text-[10px]">make sync-upstox</code>
                </p>
              </div>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
            <h2 className="text-sm font-medium text-[var(--text-primary)]">
              SIP parameters
            </h2>
            <div className="mt-3 space-y-3">
              <div>
                <label htmlFor="sip-amount" className={labelClass}>
                  Monthly amount
                </label>
                <div className="relative mt-1">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--text-muted)]">
                    ₹
                  </span>
                  <input
                    id="sip-amount"
                    type="number"
                    min={1}
                    step={500}
                    className={`${inputClass} pl-7`}
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    aria-invalid={amountInvalid}
                    aria-describedby={
                      amountInvalid ? "sip-amount-error" : undefined
                    }
                  />
                </div>
                {amountInvalid ? (
                  <p
                    id="sip-amount-error"
                    className="mt-1 text-[11px] text-[var(--risk-warning)]"
                    role="alert"
                  >
                    Enter a monthly amount greater than ₹0.
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="sip-day" className={labelClass}>
                  SIP day (calendar)
                </label>
                <input
                  id="sip-day"
                  type="number"
                  min={1}
                  max={28}
                  className={`${inputClass} mt-1`}
                  value={dayOfMonth}
                  onChange={(e) => setDayOfMonth(Number(e.target.value))}
                  aria-invalid={dayInvalid}
                  aria-describedby={
                    dayInvalid ? "sip-day-error" : "sip-day-helper"
                  }
                />
                {dayInvalid ? (
                  <p
                    id="sip-day-error"
                    className="mt-1 text-[11px] text-[var(--risk-warning)]"
                    role="alert"
                  >
                    Use a day from 1 to 28 so every month has that date.
                  </p>
                ) : (
                  <p
                    id="sip-day-helper"
                    className="mt-1 text-[11px] text-[var(--text-muted)]"
                  >
                    If that day is not a trading session, we invest on the next
                    session with prices.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div>
                  <label htmlFor="sip-start" className={labelClass}>
                    Start date
                  </label>
                  <input
                    id="sip-start"
                    type="date"
                    className={`${inputClass} mt-1`}
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <label htmlFor="sip-end" className={labelClass}>
                      End date
                    </label>
                    <label className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]">
                      <input
                        type="checkbox"
                        checked={endLatest}
                        onChange={(e) => setEndLatest(e.target.checked)}
                        className="rounded border-[var(--border-default)]"
                      />
                      To latest available price
                    </label>
                  </div>
                  <input
                    id="sip-end"
                    type="date"
                    className={`${inputClass} mt-1`}
                    value={end}
                    onChange={(e) => {
                      setEnd(e.target.value);
                      setEndLatest(false);
                    }}
                    disabled={endLatest}
                    min={start}
                  />
                  {endInvalid ? (
                    <p
                      className="mt-1 text-[11px] text-[var(--risk-warning)]"
                      role="alert"
                    >
                      End date must be on or after the start date.
                    </p>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-col gap-2">
              <button
                id="sip-run"
                type="button"
                onClick={runBacktest}
                disabled={!formValid || runState === "loading"}
                aria-busy={runState === "loading"}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {runState === "loading" ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Running…
                  </>
                ) : (
                  "Run backtest"
                )}
              </button>
              {!formValid && runState !== "loading" ? (
                <p className="text-[11px] text-[var(--risk-warning)]">
                  Fix the fields above to run.
                </p>
              ) : null}

              <div className="relative" ref={exportRef}>
                <button
                  type="button"
                  disabled={runState !== "success" || !result}
                  onClick={() => setExportOpen((o) => !o)}
                  title={
                    runState !== "success" || !result
                      ? "Run a backtest to export."
                      : undefined
                  }
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Download size={14} />
                  Export
                  <ChevronDown size={14} className="opacity-60" />
                </button>
                {runState !== "success" || !result ? (
                  <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                    Run a backtest to export.
                  </p>
                ) : null}
                {exportOpen && result ? (
                  <div className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-md border border-[var(--border-default)] bg-[var(--bg-surface-raised)] shadow-lg">
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-xs text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                      onClick={() => {
                        exportSipJson(result);
                        setExportOpen(false);
                      }}
                    >
                      Download full results (JSON)
                    </button>
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-xs text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                      onClick={() => {
                        exportSipCashflowsCsv(result);
                        setExportOpen(false);
                      }}
                    >
                      Download cashflow list (CSV)
                    </button>
                    <p className="border-t border-[var(--border-subtle)] px-3 py-1.5 text-[10px] text-[var(--text-muted)]">
                      CSV matches the cashflow table (including signs).
                    </p>
                  </div>
                ) : null}
              </div>

              {/* Short under-CTA only when demo risk is high */}
              {upstoxConfigured === false ? (
                <p className="text-[11px] text-[var(--risk-warning)]">
                  Demo prices — not live market performance.
                </p>
              ) : null}
            </div>
          </div>

          {/* §4 Methodology — collapsed after successful non-demo run */}
          <MethodologyPanel
            forceOpen={idleOrDemo}
            previewMode={runState === "idle"}
          />
        </aside>

        {/* §5 Results */}
        <section
          id="results"
          className="flex min-h-[360px] flex-col gap-4 xl:col-span-8"
        >
          {stale && runState === "success" ? (
            <div
              className="rounded-md border border-[var(--risk-warning)]/40 bg-[var(--risk-warning)]/10 px-3 py-2 text-xs text-[var(--text-primary)]"
              role="status"
            >
              Parameters changed — re-run to update results.
            </div>
          ) : null}

          {runState === "idle" ? (
            <EmptyState
              title="Run a SIP backtest"
              description="Pick a basket, set monthly amount and dates, then run. You’ll get XIRR, portfolio value over time, and the cashflows behind the number."
              action={
                <div className="flex flex-col items-center gap-3">
                  <ol className="flex flex-wrap justify-center gap-x-3 gap-y-1 text-[11px] text-[var(--text-muted)]">
                    <li>1 Basket</li>
                    <li>2 Monthly amount &amp; dates</li>
                    <li>3 Run backtest</li>
                  </ol>
                  <button
                    type="button"
                    onClick={focusConfigure}
                    className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
                  >
                    Configure &amp; run →
                  </button>
                  <span className="text-xs text-[var(--text-muted)]">
                    Results appear here after you run.
                  </span>
                </div>
              }
              className="min-h-[360px]"
            />
          ) : null}

          {runState === "error" ? (
            <ErrorBanner
              message={error ?? "Backtest failed. Retry or check API logs."}
              onRetry={() => {
                if (lastBodyRef.current) void runBacktest();
              }}
            />
          ) : null}

          {runState === "loading" || runState === "success" ? (
            <>
              {runState === "success" && result ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <DataSourceChip dataSource={result.data_source} />
                    {result.name ? (
                      <span className="text-xs text-[var(--text-secondary)]">
                        {result.name}
                      </span>
                    ) : null}
                  </div>
                  <SipDataSourceBanner dataSource={result.data_source} />
                  {result.warnings?.length ? (
                    <ul className="list-disc space-y-1 rounded-md border border-[var(--border-default)] bg-[var(--bg-muted)] px-4 py-2 pl-8 text-xs text-[var(--text-secondary)]">
                      {result.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                </>
              ) : null}

              {/* KPI strip — XIRR hero, then money trio, then risk/count */}
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-12">
                <div
                  className={`col-span-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 lg:col-span-4 ${
                    demoResult
                      ? "border-l-2 border-l-[var(--risk-warning)]"
                      : ""
                  }`}
                  title="Uses contribution dates and amounts plus ending portfolio value. Not the same as the Dashboard’s index-style return."
                >
                  {runState === "loading" ? (
                    <>
                      <div className="h-3 w-12 animate-pulse rounded bg-[var(--bg-muted)]" />
                      <div className="mt-2 h-9 w-28 animate-pulse rounded bg-[var(--bg-muted)]" />
                      <div className="mt-2 h-3 w-40 animate-pulse rounded bg-[var(--bg-muted)]" />
                    </>
                  ) : (
                    <>
                      <span className="text-xs font-medium tracking-wide text-[var(--text-secondary)]">
                        XIRR
                      </span>
                      <p
                        className={`mt-1 text-3xl font-semibold tabular-nums leading-tight ${
                          result?.xirr == null
                            ? "text-[var(--text-primary)]"
                            : sentimentFromSigned(result.xirr) === "pos"
                              ? "text-[var(--pnl-pos)]"
                              : sentimentFromSigned(result.xirr) === "neg"
                                ? "text-[var(--pnl-neg)]"
                                : "text-[var(--text-primary)]"
                        }`}
                      >
                        {result?.xirr == null
                          ? "—"
                          : formatPercent(result.xirr)}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">
                        {result?.xirr == null
                          ? "Need at least two cashflows"
                          : "Annualized return on all SIPs + ending value."}
                      </p>
                      {xirrSublabel ? (
                        <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                          {xirrSublabel}
                        </p>
                      ) : null}
                    </>
                  )}
                </div>

                <div className="col-span-2 grid grid-cols-3 gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-2 sm:col-span-2 lg:col-span-5">
                  <MetricCard
                    label="Total invested"
                    value={
                      runState === "success"
                        ? formatInr(result?.total_invested)
                        : null
                    }
                    loading={runState === "loading"}
                    sublabel="Cash you put in"
                    hint="Sum of all monthly SIP contributions."
                    size="compact"
                    className="border-0 bg-transparent shadow-none"
                  />
                  <MetricCard
                    label="Final value"
                    value={
                      runState === "success"
                        ? formatInr(result?.final_value)
                        : null
                    }
                    loading={runState === "loading"}
                    sublabel="What basket is worth"
                    hint="Market value of units held at the end date."
                    size="compact"
                    className="border-0 bg-transparent shadow-none"
                  />
                  <MetricCard
                    label="Absolute gain"
                    value={
                      runState === "success"
                        ? formatInrSigned(absoluteGain)
                        : null
                    }
                    sentiment={
                      runState === "success"
                        ? sentimentFromSigned(absoluteGain)
                        : "none"
                    }
                    loading={runState === "loading"}
                    sublabel="Final − invested"
                    hint="Final value minus total invested."
                    size="compact"
                    className="border-0 bg-transparent shadow-none"
                  />
                  <p className="col-span-3 px-1 pb-1 text-[11px] text-[var(--text-muted)]">
                    Invested is cash in. Final value is what those units are
                    worth. XIRR annualizes the path between them.
                  </p>
                </div>

                <div className="col-span-2 grid grid-cols-2 gap-3 lg:col-span-3 lg:grid-cols-1">
                  <MetricCard
                    label="Max drawdown"
                    value={
                      runState === "success"
                        ? formatPercent(result?.max_drawdown)
                        : null
                    }
                    sentiment={
                      runState === "success"
                        ? sentimentMaxDrawdown(result?.max_drawdown)
                        : "none"
                    }
                    loading={runState === "loading"}
                    sublabel="Worst drop from a peak — path risk, not XIRR"
                    size="compact"
                  />
                  <MetricCard
                    label="SIP count"
                    value={
                      runState === "success" && result
                        ? String(result.n_sips)
                        : null
                    }
                    loading={runState === "loading"}
                    sublabel="Number of monthly SIPs in this run"
                    size="compact"
                  />
                </div>
              </div>

              <PerformanceChart
                variant="equity"
                title="Portfolio value"
                subtitle="Market value of SIP units · zero costs"
                series={equitySeries}
                height={360}
                loading={runState === "loading"}
                emptyMessage="No series — run a backtest"
                yTickFormatter={(n) => formatInrCompact(n)}
                syncId="sip-lab"
              />

              <PerformanceChart
                variant="drawdown"
                title="Drawdown (market value)"
                series={drawdownSeries}
                height={220}
                loading={runState === "loading"}
                emptyMessage="No series — run a backtest"
                syncId="sip-lab"
              />

              {/* Tables */}
              <div>
                <div
                  className="mb-2 flex gap-1 border-b border-[var(--border-subtle)]"
                  role="tablist"
                  aria-label="Result tables"
                >
                  {(
                    [
                      ["cashflows", "Cashflows"],
                      ["holdings", "By holding"],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={tab === id}
                      onClick={() => setTab(id)}
                      className={`px-3 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${
                        tab === id
                          ? "border-b-2 border-[var(--accent)] text-[var(--accent)]"
                          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {tab === "cashflows" ? (
                  <SipCashflowTable
                    cashflows={result?.cashflows ?? []}
                    loading={runState === "loading"}
                  />
                ) : (
                  <SipHoldingTable
                    contribution={result?.contribution ?? []}
                    loading={runState === "loading"}
                  />
                )}
              </div>
            </>
          ) : null}

          {/* §6 How to read — collapsed on idle, open after success */}
          <HowToReadPanel defaultOpen={runState === "success"} />

          {/* §7 Assumptions footer */}
          {runState === "success" && result?.assumptions ? (
            <footer
              id="assumptions"
              className="border-t border-[var(--border-subtle)] pt-3 text-[11px] leading-relaxed text-[var(--text-muted)]"
            >
              <p>
                SIPs on calendar day{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  {dayOfMonth}
                </strong>{" "}
                (next trading day if closed) ·{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  {result.assumptions.costs_zero
                    ? "No costs"
                    : result.assumptions.costs}
                </strong>{" "}
                in this version · Prices:{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  session {result.assumptions.price_field || "close"}
                </strong>{" "}
                · XIRR uses{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  {result.assumptions.xirr_day_count || "actual/365"}
                </strong>{" "}
                day count · Currency{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  {result.assumptions.currency || "INR"}
                </strong>{" "}
                · Headline metric:{" "}
                <strong className="font-medium text-[var(--text-secondary)]">
                  XIRR
                </strong>{" "}
                (not the Dashboard index return).
              </p>
            </footer>
          ) : (
            <footer
              id="assumptions"
              className="border-t border-[var(--border-subtle)] pt-3 text-[11px] text-[var(--text-muted)]"
            >
              Fixed calendar SIP day → next trading day if closed · Zero costs
              MVP · XIRR primary · Upstox only for real history
            </footer>
          )}
        </section>
      </div>
    </div>
  );
}
