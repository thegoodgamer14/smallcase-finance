"use client";

import { useEffect, useMemo, useState } from "react";

import {
  aggregateSectors,
  SectorBreakdown,
} from "@/components/charts/SectorBreakdown";
import { PerformanceChart } from "@/components/charts/PerformanceChart";
import { PeriodReturnsGrid } from "@/components/dashboard/PeriodReturnsGrid";
import { TopContributors } from "@/components/dashboard/TopContributors";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { RangeChips } from "@/components/filters/RangeChips";
import { MetricCard } from "@/components/kpis/MetricCard";
import { SipDashCallout } from "@/components/sip/SipDashCallout";
import {
  getHoldings,
  getMetrics,
  getMetricsMulti,
  getPerformance,
} from "@/lib/api";
import { useApp } from "@/lib/context";
import {
  formatDate,
  formatNav,
  formatPercent,
  formatPercentAbs,
  formatRatio,
} from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import {
  sentimentFromSigned,
  sentimentMaxDrawdown,
} from "@/lib/sentiment";
import type {
  ChartSeries,
  HoldingRow,
  MetricsResponse,
  WindowKey,
} from "@/lib/types";
import { WINDOW_OPTIONS } from "@/lib/windows";

export default function DashboardPage() {
  const {
    smallcaseId,
    activeSmallcase,
    window,
    setWindow,
    customRange,
    smallcasesLoading,
    smallcasesError,
    refreshSmallcases,
    smallcases,
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

  const holdings = useAsync(
    () => getHoldings(smallcaseId!),
    [smallcaseId],
    enabled,
  );

  const [periodMetrics, setPeriodMetrics] = useState<
    Partial<Record<WindowKey, MetricsResponse>>
  >({});
  const [periodLoading, setPeriodLoading] = useState(false);

  useEffect(() => {
    if (!smallcaseId) return;
    let cancelled = false;
    setPeriodLoading(true);
    getMetricsMulti(smallcaseId, WINDOW_OPTIONS)
      .then((res) => {
        if (!cancelled) setPeriodMetrics(res);
      })
      .finally(() => {
        if (!cancelled) setPeriodLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [smallcaseId]);

  const latestNav = useMemo(() => {
    const series = performance.data?.series;
    if (!series?.length) return null;
    return series[series.length - 1].nav;
  }, [performance.data]);

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

  const holdingRows: HoldingRow[] = useMemo(
    () =>
      (holdings.data?.holdings ?? []).map((h) => ({
        symbol: h.symbol,
        name: h.name,
        weight: h.weight,
        sector: h.sector,
      })),
    [holdings.data],
  );

  const sectors = useMemo(
    () => aggregateSectors(holdingRows),
    [holdingRows],
  );
  const hasSectors = holdingRows.some((h) => h.sector);

  const periodReturns = useMemo(() => {
    const out: Partial<Record<WindowKey, number | null>> = {};
    for (const w of WINDOW_OPTIONS) {
      out[w] = periodMetrics[w]?.metrics.total_return ?? null;
    }
    return out;
  }, [periodMetrics]);

  const m = metrics.data?.metrics;
  const anyError =
    metrics.error || performance.error || holdings.error || smallcasesError;

  if (!smallcasesLoading && smallcases.length === 0 && !smallcasesError) {
    return (
      <div className="mx-auto max-w-content px-6 py-10">
        <EmptyState
          title="No smallcases loaded"
          description="Run the data pipeline so curated smallcases exist under data/curated/smallcases/, then start the API (make api)."
        />
      </div>
    );
  }

  if (!smallcasesLoading && smallcasesError && smallcases.length === 0) {
    return (
      <div className="mx-auto max-w-content space-y-4 px-6 py-10">
        <ErrorBanner message={smallcasesError} onRetry={refreshSmallcases} />
        <EmptyState
          title="API unavailable"
          description={`Could not load smallcases from the backend. Ensure FastAPI is running at ${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}.`}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6 px-6 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">
            Dashboard
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {activeSmallcase?.name ?? "—"}
            {activeSmallcase?.theme ? ` · ${activeSmallcase.theme}` : ""}
            {activeSmallcase?.as_of
              ? ` · As-of ${formatDate(activeSmallcase.as_of)}`
              : ""}
          </p>
        </div>
        <RangeChips value={window} onChange={setWindow} />
      </header>

      {anyError ? (
        <ErrorBanner
          message={
            metrics.error ||
            performance.error ||
            holdings.error ||
            smallcasesError ||
            "Failed to load"
          }
          onRetry={() => {
            metrics.reload();
            performance.reload();
            holdings.reload();
          }}
        />
      ) : null}

      <SipDashCallout />

      {/* KPI strip */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Current NAV"
          value={formatNav(latestNav)}
          loading={performance.loading}
          hint="Latest NAV from performance series"
        />
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
        />
        <MetricCard
          label="Max drawdown"
          value={formatPercent(m?.max_drawdown)}
          sentiment={sentimentMaxDrawdown(m?.max_drawdown)}
          loading={metrics.loading}
          href="/performance#drawdown"
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
          hint={
            metrics.data
              ? `rf ${metrics.data.assumptions.risk_free_rate}`
              : undefined
          }
        />
      </section>

      {/* Equity + contributors */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <PerformanceChart
            variant="equity"
            title="Equity curve"
            subtitle="NAV series"
            series={equitySeries}
            height={360}
            loading={performance.loading}
            emptyMessage="No NAV series for selected range"
            error={performance.error}
          />
        </div>
        <div className="lg:col-span-4">
          <TopContributors
            rows={holdingRows}
            loading={holdings.loading}
            mode="weight"
          />
        </div>
      </section>

      {/* Allocation + period returns */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-5">
          {hasSectors ? (
            <SectorBreakdown
              data={sectors}
              title="Allocation"
              loading={holdings.loading}
            />
          ) : (
            <TopContributors
              rows={holdingRows}
              loading={holdings.loading}
              mode="weight"
              className="min-h-[320px]"
            />
          )}
        </div>
        <div className="lg:col-span-7">
          <PeriodReturnsGrid
            returns={periodReturns}
            activeWindow={window}
            onSelectWindow={setWindow}
            loading={periodLoading}
          />
        </div>
      </section>
    </div>
  );
}
