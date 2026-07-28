"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import {
  aggregateSectors,
  SectorBreakdown,
} from "@/components/charts/SectorBreakdown";
import { WeightBars } from "@/components/charts/WeightBars";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { RangeChips } from "@/components/filters/RangeChips";
import { HoldingsTable } from "@/components/tables/HoldingsTable";
import { getHoldings } from "@/lib/api";
import { useApp } from "@/lib/context";
import { formatDate, formatWeight } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import type { HoldingRow } from "@/lib/types";

export default function HoldingsPage() {
  const {
    smallcaseId,
    activeSmallcase,
    window,
    setWindow,
    smallcasesLoading,
    smallcasesError,
    smallcases,
    refreshSmallcases,
  } = useApp();

  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState<string>("all");
  const [topN, setTopN] = useState<"all" | "10" | "20">("all");

  const enabled = Boolean(smallcaseId);
  const holdings = useAsync(
    () => getHoldings(smallcaseId!),
    [smallcaseId],
    enabled,
  );

  const rows: HoldingRow[] = useMemo(
    () =>
      (holdings.data?.holdings ?? []).map((h) => ({
        symbol: h.symbol,
        name: h.name,
        weight: h.weight,
        sector: h.sector,
      })),
    [holdings.data],
  );

  const sectors = useMemo(() => {
    const set = new Set<string>();
    for (const r of rows) {
      if (r.sector) set.add(r.sector);
    }
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = rows;
    if (q) {
      list = list.filter(
        (r) =>
          r.symbol.toLowerCase().includes(q) ||
          (r.name?.toLowerCase().includes(q) ?? false),
      );
    }
    if (sectorFilter !== "all") {
      list = list.filter((r) => r.sector === sectorFilter);
    }
    const sorted = [...list].sort((a, b) => b.weight - a.weight);
    if (topN === "10") return sorted.slice(0, 10);
    if (topN === "20") return sorted.slice(0, 20);
    return sorted;
  }, [rows, search, sectorFilter, topN]);

  const summary = useMemo(() => {
    const names = rows.length;
    const sectorCount = new Set(
      rows.map((r) => r.sector).filter(Boolean),
    ).size;
    const top10 = [...rows]
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 10)
      .reduce((s, r) => s + r.weight, 0);
    const weightSum = holdings.data?.weight_sum ?? rows.reduce((s, r) => s + r.weight, 0);
    return { names, sectorCount, top10, weightSum };
  }, [rows, holdings.data]);

  const sectorData = useMemo(() => aggregateSectors(rows), [rows]);
  const hasSectors = rows.some((r) => r.sector);
  const weightOff = Math.abs(summary.weightSum - 1) > 1e-3;

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
            Holdings
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {activeSmallcase?.name ?? "—"}
            {holdings.data?.as_of
              ? ` · As-of ${formatDate(holdings.data.as_of)}`
              : ""}
            {holdings.data?.methodology
              ? ` · ${holdings.data.methodology}`
              : ""}
          </p>
        </div>
        <RangeChips value={window} onChange={setWindow} />
      </header>

      {holdings.error ? (
        <ErrorBanner message={holdings.error} onRetry={holdings.reload} />
      ) : null}

      {/* Summary strip */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-secondary)]">
        {holdings.loading ? (
          <span className="h-4 w-48 animate-pulse rounded bg-[var(--bg-muted)]" />
        ) : (
          <>
            <span>
              <span className="tabular-nums text-[var(--text-primary)]">
                {summary.names}
              </span>{" "}
              names
            </span>
            <span>
              <span className="tabular-nums text-[var(--text-primary)]">
                {summary.sectorCount || "—"}
              </span>{" "}
              sectors
            </span>
            <span>
              Top 10:{" "}
              <span className="tabular-nums text-[var(--text-primary)]">
                {formatWeight(summary.top10)}
              </span>
            </span>
            <span>
              Σw:{" "}
              <span
                className={`tabular-nums ${
                  weightOff
                    ? "text-[var(--risk-warning)]"
                    : "text-[var(--text-primary)]"
                }`}
              >
                {formatWeight(summary.weightSum)}
              </span>
            </span>
          </>
        )}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1 max-w-sm">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search ticker or name"
            className="h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
          />
        </div>

        {sectors.length > 0 ? (
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="h-9 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
            aria-label="Filter by sector"
          >
            <option value="all">All sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        ) : null}

        <div className="inline-flex gap-1">
          {(["all", "10", "20"] as const).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setTopN(n)}
              className={`h-8 rounded-md px-2.5 text-xs font-medium ${
                topN === n
                  ? "bg-[var(--accent-subtle)] text-[var(--accent)]"
                  : "border border-[var(--border-default)] text-[var(--text-secondary)]"
              }`}
            >
              {n === "all" ? "All" : `Top ${n}`}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <section className="overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <HoldingsTable
          rows={filtered}
          columns={["symbol", "name", "weight", "sector"]}
          loading={holdings.loading}
          emptyMessage={
            search
              ? `No names match “${search}”`
              : "No constituents for this smallcase / as-of"
          }
        />
      </section>

      {/* Charts */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WeightBars
          data={rows.map((r) => ({
            label: r.symbol,
            weight: r.weight,
          }))}
          loading={holdings.loading}
        />
        {hasSectors ? (
          <SectorBreakdown data={sectorData} loading={holdings.loading} />
        ) : (
          <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 text-sm text-[var(--text-muted)]">
            Sector data not available for these holdings.
          </div>
        )}
      </section>
    </div>
  );
}
