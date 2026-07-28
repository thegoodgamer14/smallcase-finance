"use client";

import { useEffect, useMemo, useState } from "react";

import { PerformanceChart } from "@/components/charts/PerformanceChart";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { RangeChips } from "@/components/filters/RangeChips";
import { MetricCard } from "@/components/kpis/MetricCard";
import {
  getMetrics,
  getMetricsMulti,
  getPerformance,
} from "@/lib/api";
import { useApp } from "@/lib/context";
import { drawdownFromNav } from "@/lib/drawdown";
import {
  formatCount,
  formatDate,
  formatPercent,
  formatPercentAbs,
  formatRatio,
} from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import {
  sentimentClass,
  sentimentFromSigned,
  sentimentMaxDrawdown,
} from "@/lib/sentiment";
import type { ChartSeries, MetricsResponse, WindowKey } from "@/lib/types";
import { WINDOW_OPTIONS } from "@/lib/windows";

export default function PerformancePage() {
  const {
    smallcaseId,
    activeSmallcase,
    window,
    setWindow,
    customRange,
    smallcasesLoading,
    smallcasesError,
    smallcases,
    refreshSmallcases,
  } = useApp();

  const enabled = Boolean(smallcaseId);

  const metrics = useAsync(
    () =>
      getMetrics(
        smallcaseId!,
        window,
        customRange
          ? { start: customRange.start, end: customRange.end }
          : undefined,
      ),
    [smallcaseId, window, customRange?.start, customRange?.end],
    enabled,
  );

  const performance = useAsync(
    () =>
      getPerformance(
        smallcaseId!,
        customRange
          ? { start: customRange.start, end: customRange.end }
          : undefined,
      ),
    [smallcaseId, customRange?.start, customRange?.end],
    enabled,
  );

  const [periodMetrics, setPeriodMetrics] = useState<
    Partial<Record<WindowKey, MetricsResponse>>
  >({});

  useEffect(() => {
    if (!smallcaseId) return;
    let cancelled = false;
    getMetricsMulti(smallcaseId, WINDOW_OPTIONS).then((res) => {
      if (!cancelled) setPeriodMetrics(res);
    });
    return () => {
      cancelled = true;
    };
  }, [smallcaseId]);

  const equitySeries: ChartSeries[] = useMemo(() => {
    const series = performance.data?.series ?? [];
    const out: ChartSeries[] = [
      {
        id: "portfolio",
        name: "Portfolio",
        role: "portfolio",
        data: series.map((p) => ({ date: p.date, value: p.nav })),
      },
    ];
    const bm = performance.data?.benchmark_series;
    if (bm?.length) {
      out.push({
        id: "benchmark",
        name: "Benchmark",
        role: "benchmark",
        data: bm.map((p) => ({ date: p.date, value: p.nav })),
      });
    }
    return out;
  }, [performance.data]);

  const drawdownSeries: ChartSeries[] = useMemo(() => {
    const series = performance.data?.series ?? [];
    return [
      {
        id: "drawdown",
        name: "Drawdown",
        role: "drawdown",
        data: drawdownFromNav(series),
      },
    ];
  }, [performance.data]);

  const m = metrics.data?.metrics;
  const assumptions = metrics.data?.assumptions;

  if (!smallcasesLoading && smallcases.length === 0) {
    return (
      <div className="mx-auto max-w-content space-y-4 px-6 py-10">
        {smallcasesError ? (
          <ErrorBanner message={smallcasesError} onRetry={refreshSmallcases} />
        ) : null}
        <EmptyState
          title="No smallcases loaded"
          description="Load curated smallcases via the data pipeline and start the API."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6 px-6 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">
            Performance &amp; Risk
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {activeSmallcase?.name ?? "—"}
            {metrics.data?.end
              ? ` · Through ${formatDate(metrics.data.end)}`
              : ""}
          </p>
        </div>
        <RangeChips value={window} onChange={setWindow} />
      </header>

      {metrics.error || performance.error ? (
        <ErrorBanner
          message={metrics.error || performance.error || "Failed to load"}
          onRetry={() => {
            metrics.reload();
            performance.reload();
          }}
        />
      ) : null}

      {/* KPI strip */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Total return"
          value={formatPercent(m?.total_return)}
          sentiment={sentimentFromSigned(m?.total_return)}
          delta={window}
          loading={metrics.loading}
        />
        <MetricCard
          label="CAGR"
          value={formatPercent(m?.cagr)}
          sentiment={sentimentFromSigned(m?.cagr)}
          loading={metrics.loading}
          hint="Need sufficient history; null for short windows"
        />
        <MetricCard
          label="Volatility"
          value={formatPercentAbs(m?.volatility)}
          loading={metrics.loading}
        />
        <MetricCard
          label="Sharpe"
          value={formatRatio(m?.sharpe)}
          loading={metrics.loading}
          delta={
            assumptions
              ? `rf ${(assumptions.risk_free_rate * 100).toFixed(1)}%`
              : undefined
          }
        />
        <MetricCard
          label="Max drawdown"
          value={formatPercent(m?.max_drawdown)}
          sentiment={sentimentMaxDrawdown(m?.max_drawdown)}
          loading={metrics.loading}
        />
        <MetricCard
          label="Observations"
          value={
            m?.n_observations != null
              ? `${formatCount(m.n_observations)} days`
              : null
          }
          loading={metrics.loading}
        />
      </section>

      <section id="equity" className="scroll-mt-20">
        <PerformanceChart
          variant="equity"
          title="Equity curve"
          subtitle="NAV (base often 100)"
          series={equitySeries}
          height={380}
          loading={performance.loading}
          emptyMessage="No performance series for this range"
          error={performance.error}
          syncId="perf"
        />
      </section>

      <section id="drawdown" className="scroll-mt-20">
        <PerformanceChart
          variant="drawdown"
          title="Drawdown"
          subtitle="Peak-to-trough from running NAV high"
          series={drawdownSeries}
          height={260}
          loading={performance.loading}
          emptyMessage="No drawdown series"
          error={performance.error}
          syncId="perf"
        />
      </section>

      {/* Period returns table */}
      <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
        <h3 className="mb-3 text-base font-medium text-[var(--text-primary)]">
          Returns by window
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-muted)] text-xs font-medium text-[var(--text-secondary)]">
              <tr>
                <th className="px-3 py-2 text-left">Window</th>
                <th className="px-3 py-2 text-right">Total return</th>
                <th className="px-3 py-2 text-right">CAGR</th>
                <th className="px-3 py-2 text-right">Vol</th>
                <th className="px-3 py-2 text-right">Max DD</th>
                <th className="px-3 py-2 text-right">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {WINDOW_OPTIONS.map((w) => {
                const row = periodMetrics[w]?.metrics;
                const active = w === window;
                return (
                  <tr
                    key={w}
                    className={`border-b border-[var(--border-subtle)] hover:bg-[var(--bg-hover)] ${
                      active ? "bg-[var(--accent-subtle)]" : ""
                    }`}
                  >
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => setWindow(w)}
                        className={`font-medium ${
                          active
                            ? "text-[var(--accent)]"
                            : "text-[var(--text-primary)]"
                        }`}
                      >
                        {w}
                      </button>
                    </td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${sentimentClass(sentimentFromSigned(row?.total_return))}`}
                    >
                      {formatPercent(row?.total_return)}
                    </td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${sentimentClass(sentimentFromSigned(row?.cagr))}`}
                    >
                      {formatPercent(row?.cagr)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--text-primary)]">
                      {formatPercentAbs(row?.volatility)}
                    </td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${sentimentClass(sentimentMaxDrawdown(row?.max_drawdown))}`}
                    >
                      {formatPercent(row?.max_drawdown)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--text-primary)]">
                      {formatRatio(row?.sharpe)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <p className="text-[11px] text-[var(--text-muted)]">
        Assumptions:{" "}
        {assumptions
          ? `${assumptions.periods_per_year} trading days/year · rf = ${assumptions.risk_free_rate} · return_type = ${assumptions.return_type} · price = ${assumptions.price_field}`
          : "—"}
        {" · "}
        max DD from NAV peaks · currency{" "}
        {metrics.data?.currency ?? activeSmallcase?.currency ?? "INR"}
        {metrics.data?.end ? ` · as-of ${formatDate(metrics.data.end)}` : ""}
        {` · window ${window}`}
      </p>
    </div>
  );
}
