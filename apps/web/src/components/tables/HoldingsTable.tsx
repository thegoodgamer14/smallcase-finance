"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useMemo, useState } from "react";

import {
  formatInr,
  formatPercent,
  formatWeight,
} from "@/lib/format";
import { sentimentClass, sentimentFromSigned } from "@/lib/sentiment";
import type { HoldingRow } from "@/lib/types";

export type ColumnKey =
  | "symbol"
  | "name"
  | "weight"
  | "price"
  | "periodReturn"
  | "contribution"
  | "sector";

type SortDir = "asc" | "desc";

interface HoldingsTableProps {
  rows: HoldingRow[];
  columns?: ColumnKey[];
  sort?: { key: ColumnKey; dir: SortDir };
  onSortChange?: (sort: { key: ColumnKey; dir: SortDir }) => void;
  loading?: boolean;
  emptyMessage?: string;
  maxWeightForBar?: number;
  stickyHeader?: boolean;
  compact?: boolean;
  className?: string;
}

const DEFAULT_COLUMNS: ColumnKey[] = [
  "symbol",
  "name",
  "weight",
  "sector",
];

const HEADERS: Record<ColumnKey, string> = {
  symbol: "Ticker",
  name: "Name",
  weight: "Weight",
  price: "Price",
  periodReturn: "Return",
  contribution: "Contrib",
  sector: "Sector",
};

const NUMERIC: ColumnKey[] = [
  "weight",
  "price",
  "periodReturn",
  "contribution",
];

function WeightBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--bg-muted)] md:w-24">
      <div
        className="h-full rounded-full bg-[var(--accent)]"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function HoldingsTable({
  rows,
  columns = DEFAULT_COLUMNS,
  sort: controlledSort,
  onSortChange,
  loading = false,
  emptyMessage = "No holdings",
  maxWeightForBar,
  stickyHeader = true,
  compact = true,
  className = "",
}: HoldingsTableProps) {
  const [internalSort, setInternalSort] = useState<{
    key: ColumnKey;
    dir: SortDir;
  }>({ key: "weight", dir: "desc" });

  const sort = controlledSort ?? internalSort;

  const setSort = (key: ColumnKey) => {
    const next: { key: ColumnKey; dir: SortDir } =
      sort.key === key
        ? { key, dir: sort.dir === "asc" ? "desc" : "asc" }
        : { key, dir: NUMERIC.includes(key) ? "desc" : "asc" };
    if (onSortChange) onSortChange(next);
    else setInternalSort(next);
  };

  const maxW =
    maxWeightForBar ??
    (rows.length ? Math.max(...rows.map((r) => r.weight)) : 1);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const dir = sort.dir === "asc" ? 1 : -1;
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * dir;
      }
      return String(av).localeCompare(String(bv)) * dir;
    });
    return copy;
  }, [rows, sort]);

  const py = compact ? "py-2" : "py-2.5";

  if (loading) {
    return (
      <div className={`overflow-x-auto ${className}`}>
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-muted)] text-xs font-medium text-[var(--text-secondary)]">
            <tr>
              {columns.map((c) => (
                <th key={c} className={`px-3 ${py} text-left`}>
                  {HEADERS[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className="border-b border-[var(--border-subtle)]">
                {columns.map((c) => (
                  <td key={c} className={`px-3 ${py}`}>
                    <div className="h-4 w-16 animate-pulse rounded bg-[var(--bg-muted)]" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead
          className={`bg-[var(--bg-muted)] text-xs font-medium text-[var(--text-secondary)] ${
            stickyHeader ? "sticky top-0 z-10" : ""
          }`}
        >
          <tr>
            {columns.map((c) => {
              const numeric = NUMERIC.includes(c);
              const active = sort.key === c;
              return (
                <th
                  key={c}
                  className={`px-3 ${py} ${numeric ? "text-right" : "text-left"}`}
                  aria-sort={
                    active
                      ? sort.dir === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  <button
                    type="button"
                    onClick={() => setSort(c)}
                    className={`inline-flex items-center gap-1 font-medium hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${
                      numeric ? "flex-row-reverse" : ""
                    } ${active ? "text-[var(--text-primary)]" : ""}`}
                  >
                    {HEADERS[c]}
                    {active ? (
                      sort.dir === "asc" ? (
                        <ChevronUp size={12} />
                      ) : (
                        <ChevronDown size={12} />
                      )
                    ) : null}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-10 text-center text-[var(--text-muted)]"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr
                key={row.symbol}
                className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-hover)]"
              >
                {columns.map((c) => {
                  if (c === "symbol") {
                    return (
                      <td
                        key={c}
                        className={`px-3 ${py} font-mono text-sm tracking-tight text-[var(--text-primary)]`}
                      >
                        {row.symbol}
                      </td>
                    );
                  }
                  if (c === "name") {
                    return (
                      <td
                        key={c}
                        className={`max-w-[28ch] truncate px-3 ${py} text-[var(--text-primary)]`}
                        title={row.name ?? undefined}
                      >
                        {row.name ?? "—"}
                      </td>
                    );
                  }
                  if (c === "weight") {
                    return (
                      <td key={c} className={`px-3 ${py}`}>
                        <div className="flex items-center justify-end gap-2">
                          <span className="tabular-nums text-[var(--text-primary)]">
                            {formatWeight(row.weight)}
                          </span>
                          <WeightBar value={row.weight} max={maxW} />
                        </div>
                      </td>
                    );
                  }
                  if (c === "price") {
                    return (
                      <td
                        key={c}
                        className={`px-3 ${py} text-right tabular-nums text-[var(--text-primary)]`}
                      >
                        {formatInr(row.price)}
                      </td>
                    );
                  }
                  if (c === "periodReturn") {
                    const s = sentimentFromSigned(row.periodReturn);
                    return (
                      <td
                        key={c}
                        className={`px-3 ${py} text-right tabular-nums ${sentimentClass(s)}`}
                      >
                        {formatPercent(row.periodReturn)}
                      </td>
                    );
                  }
                  if (c === "contribution") {
                    const s = sentimentFromSigned(row.contribution);
                    return (
                      <td
                        key={c}
                        className={`px-3 ${py} text-right tabular-nums ${sentimentClass(s)}`}
                      >
                        {formatPercent(row.contribution)}
                      </td>
                    );
                  }
                  return (
                    <td
                      key={c}
                      className={`px-3 ${py} text-[var(--text-secondary)]`}
                    >
                      {row.sector ?? "—"}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
