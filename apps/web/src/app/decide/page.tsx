"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PerformanceChart } from "@/components/charts/PerformanceChart";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { MetricCard } from "@/components/kpis/MetricCard";
import {
  ApiError,
  getPortfolioSymbols,
  getPriceCoverage,
  postDecisionRun,
} from "@/lib/api";
import {
  formatInrCompact,
  formatPercent,
  formatWeight,
} from "@/lib/format";
import { sentimentFromSigned, sentimentMaxDrawdown } from "@/lib/sentiment";
import type {
  ChartSeries,
  DecisionRunResponse,
  WeightGapRow,
} from "@/lib/types";

function defaultStartDate(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 3);
  return d.toISOString().slice(0, 10);
}

export default function DecidePage() {
  const searchParams = useSearchParams();
  const urlSymbols = searchParams.get("symbols");

  const [heldSymbols, setHeldSymbols] = useState<string[]>([]);
  const [mode, setMode] = useState<"equal_weight" | "custom_weights">(
    "equal_weight",
  );
  const [rows, setRows] = useState<{ symbol: string; weight: string }[]>([
    { symbol: "", weight: "" },
  ]);
  const [amount, setAmount] = useState(10000);
  const [day, setDay] = useState(1);
  const [start, setStart] = useState(defaultStartDate);
  const [end, setEnd] = useState("");
  const [benchmark, setBenchmark] = useState("NIFTYBEES");
  const [includeBenchmark, setIncludeBenchmark] = useState(true);
  const [includeGap, setIncludeGap] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecisionRunResponse | null>(null);
  const [coverageHint, setCoverageHint] = useState<string | null>(null);

  useEffect(() => {
    void getPortfolioSymbols()
      .then((r) => setHeldSymbols(r.symbols))
      .catch(() => setHeldSymbols([]));
  }, []);

  useEffect(() => {
    if (!urlSymbols) return;
    const syms = urlSymbols
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    if (syms.length) {
      setRows(syms.map((symbol) => ({ symbol, weight: "" })));
    }
  }, [urlSymbols]);

  const addRow = () => setRows((r) => [...r, { symbol: "", weight: "" }]);
  const updateRow = (i: number, patch: Partial<{ symbol: string; weight: string }>) => {
    setRows((prev) =>
      prev.map((row, idx) => (idx === i ? { ...row, ...patch } : row)),
    );
  };
  const removeRow = (i: number) =>
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((_, idx) => idx !== i)));

  const addHeld = (sym: string) => {
    setRows((prev) => {
      if (prev.some((r) => r.symbol.toUpperCase() === sym)) return prev;
      const empty = prev.findIndex((r) => !r.symbol.trim());
      if (empty >= 0) {
        return prev.map((r, i) => (i === empty ? { ...r, symbol: sym } : r));
      }
      return [...prev, { symbol: sym, weight: "" }];
    });
  };

  const checkCoverage = useCallback(async () => {
    const syms = rows
      .map((r) => r.symbol.trim().toUpperCase())
      .filter(Boolean);
    if (!syms.length) {
      setCoverageHint(null);
      return;
    }
    try {
      const cov = await getPriceCoverage(
        includeBenchmark ? [...syms, benchmark] : syms,
      );
      const missing = cov.symbols.filter((s) => !s.has_prices).map((s) => s.symbol);
      if (missing.length) {
        setCoverageHint(
          `Missing prices for: ${missing.join(", ")}. Sync via make sync-upstox or remove them. Source: ${cov.data_source}.`,
        );
      } else {
        setCoverageHint(`Price coverage OK (${cov.data_source}).`);
      }
    } catch {
      setCoverageHint(null);
    }
  }, [rows, includeBenchmark, benchmark]);

  const onRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const constituents = rows
        .map((r) => ({
          symbol: r.symbol.trim().toUpperCase(),
          weight: r.weight,
        }))
        .filter((r) => r.symbol);
      if (!constituents.length) {
        throw new Error("Add at least one symbol");
      }
      const body = {
        basket: {
          mode,
          constituents: constituents.map((c) => ({
            symbol: c.symbol,
            target_weight:
              mode === "custom_weights"
                ? Number(c.weight) / 100
                : undefined,
          })),
        },
        sip: {
          amount,
          day_of_month: day,
          start_date: start,
          end_date: end || null,
        },
        benchmark_symbol: benchmark,
        include_benchmark: includeBenchmark,
        include_weight_gap: includeGap,
        strict_market_data: false,
      };
      const res = await postDecisionRun(body);
      setResult(res);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Run failed",
      );
    } finally {
      setRunning(false);
    }
  };

  const chartSeries: ChartSeries[] = useMemo(() => {
    if (!result) return [];
    const series: ChartSeries[] = [
      {
        id: "candidate",
        name: "Candidate",
        role: "portfolio",
        data: result.candidate.series.map((p) => ({
          date: p.date,
          value: p.market_value,
        })),
      },
    ];
    if (result.benchmark?.series?.length) {
      series.push({
        id: "benchmark",
        name: result.benchmark.symbol || "Benchmark",
        role: "benchmark",
        strokeDasharray: "4 4",
        data: result.benchmark.series.map((p) => ({
          date: p.date,
          value: p.market_value,
        })),
      });
    }
    return series;
  }, [result]);

  const isDemo =
    result?.data_source === "sample" || result?.data_source === "mixed";

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Decision Lab</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          Build a candidate basket, run a monthly SIP (XIRR primary), compare to a
          benchmark, and see weight gaps vs your Kite book.{" "}
          <Link href="/sip-lab" className="text-[var(--accent)] underline">
            Advanced SIP Lab
          </Link>
        </p>
      </div>

      <section className="space-y-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
        <h2 className="text-sm font-semibold">Basket</h2>
        <div className="flex flex-wrap gap-3 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={mode === "equal_weight"}
              onChange={() => setMode("equal_weight")}
            />
            Equal weight
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={mode === "custom_weights"}
              onChange={() => setMode("custom_weights")}
            />
            Custom weights (%)
          </label>
        </div>

        {heldSymbols.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs text-[var(--text-muted)]">From book:</span>
            {heldSymbols.slice(0, 20).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => addHeld(s)}
                className="rounded border border-[var(--border-default)] px-2 py-0.5 text-xs hover:bg-[var(--bg-hover)]"
              >
                {s}
              </button>
            ))}
          </div>
        ) : null}

        <div className="space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              <input
                className="w-32 rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5 text-sm uppercase"
                placeholder="SYMBOL"
                value={row.symbol}
                onChange={(e) =>
                  updateRow(i, { symbol: e.target.value.toUpperCase() })
                }
              />
              {mode === "custom_weights" ? (
                <input
                  className="w-24 rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5 text-sm"
                  placeholder="%"
                  value={row.weight}
                  onChange={(e) => updateRow(i, { weight: e.target.value })}
                />
              ) : null}
              <button
                type="button"
                className="text-xs text-[var(--text-muted)]"
                onClick={() => removeRow(i)}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addRow}
            className="text-sm text-[var(--accent)]"
          >
            + Add symbol
          </button>
        </div>
      </section>

      <section className="grid gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 md:grid-cols-2">
        <label className="text-sm">
          SIP amount (₹)
          <input
            type="number"
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
          />
        </label>
        <label className="text-sm">
          Day of month (1–28)
          <input
            type="number"
            min={1}
            max={28}
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5"
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
          />
        </label>
        <label className="text-sm">
          Start
          <input
            type="date"
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="text-sm">
          End (optional)
          <input
            type="date"
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <label className="text-sm md:col-span-2">
          Benchmark symbol
          <input
            className="mt-1 w-full rounded border border-[var(--border-default)] bg-[var(--bg-app)] px-2 py-1.5 uppercase"
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value.toUpperCase())}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeBenchmark}
            onChange={(e) => setIncludeBenchmark(e.target.checked)}
          />
          Include benchmark SIP
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeGap}
            onChange={(e) => setIncludeGap(e.target.checked)}
          />
          Weight gap vs portfolio
        </label>
      </section>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void onRun()}
          disabled={running}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? <Loader2 size={16} className="animate-spin" /> : null}
          Run decision backtest
        </button>
        <button
          type="button"
          onClick={() => void checkCoverage()}
          className="rounded-md border border-[var(--border-default)] px-3 py-2 text-sm hover:bg-[var(--bg-hover)]"
        >
          Check price coverage
        </button>
      </div>

      {coverageHint ? (
        <p className="text-sm text-[var(--text-secondary)]">{coverageHint}</p>
      ) : null}
      {error ? <ErrorBanner message={error} /> : null}

      {result ? (
        <div className="space-y-4">
          {isDemo ? (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              These results use demo/sample (or mixed) prices. Do not use them to
              size real positions. Sync Upstox for live history.
            </div>
          ) : null}

          {result.warnings.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard
              label="XIRR (candidate)"
              value={formatPercent(result.candidate.xirr)}
              sentiment={sentimentFromSigned(result.candidate.xirr)}
            />
            <MetricCard
              label="Benchmark XIRR"
              value={formatPercent(result.benchmark?.xirr)}
              sentiment={sentimentFromSigned(result.benchmark?.xirr)}
            />
            <MetricCard
              label="Δ XIRR"
              value={formatPercent(result.delta_xirr)}
              sentiment={sentimentFromSigned(result.delta_xirr)}
            />
            <MetricCard
              label="Max drawdown"
              value={formatPercent(result.candidate.max_drawdown)}
              sentiment={sentimentMaxDrawdown(result.candidate.max_drawdown)}
            />
            <MetricCard
              label="Invested"
              value={formatInrCompact(result.candidate.total_invested)}
            />
            <MetricCard
              label="Final value"
              value={formatInrCompact(result.candidate.final_value)}
            />
            <MetricCard
              label="Data source"
              value={result.data_source}
            />
            <MetricCard
              label="Coverage"
              value={`${result.coverage.basket_with_prices}/${result.coverage.basket_symbols}`}
            />
          </div>

          {chartSeries[0]?.data.length ? (
            <div className="rounded-lg border border-[var(--border-default)] p-3">
              <p className="mb-2 text-sm font-medium">Market value path</p>
              <PerformanceChart
                variant="equity"
                series={chartSeries}
                height={280}
              />
            </div>
          ) : (
            <EmptyState
              title="No series"
              description="Run produced no market-value points."
            />
          )}

          {result.weight_gap.length > 0 ? (
            <div>
              <h3 className="mb-2 text-sm font-semibold">Weight gap</h3>
              <p className="mb-2 text-xs text-[var(--text-muted)]">
                Suggested weight changes only — place orders yourself on Kite.
              </p>
              <WeightGapTable rows={result.weight_gap} />
            </div>
          ) : null}

          <p className="text-xs text-[var(--text-muted)]">{result.disclaimer}</p>
        </div>
      ) : null}
    </div>
  );
}

function WeightGapTable({ rows }: { rows: WeightGapRow[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--border-default)]">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-[var(--bg-surface)] text-[11px] uppercase text-[var(--text-muted)]">
          <tr>
            <th className="px-3 py-2">Symbol</th>
            <th className="px-3 py-2 text-right">Book</th>
            <th className="px-3 py-2 text-right">Target</th>
            <th className="px-3 py-2 text-right">Δ weight</th>
            <th className="px-3 py-2 text-right">≈ ₹ delta</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.symbol}
              className="border-t border-[var(--border-subtle)]"
            >
              <td className="px-3 py-2 font-medium">{r.symbol}</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatWeight(r.portfolio_weight)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatWeight(r.target_weight)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatWeight(r.delta_weight)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {r.approx_value_delta != null
                  ? formatInrCompact(r.approx_value_delta)
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
