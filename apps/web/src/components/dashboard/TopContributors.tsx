import Link from "next/link";

import { formatPercent, formatWeight } from "@/lib/format";
import { sentimentClass, sentimentFromSigned } from "@/lib/sentiment";
import type { HoldingRow } from "@/lib/types";

interface TopContributorsProps {
  rows: HoldingRow[];
  loading?: boolean;
  className?: string;
  /** When no contribution data, show top weights instead. */
  mode?: "contribution" | "weight";
}

export function TopContributors({
  rows,
  loading = false,
  className = "",
  mode = "weight",
}: TopContributorsProps) {
  const sorted = [...rows].sort((a, b) => {
    if (mode === "contribution") {
      return (b.contribution ?? 0) - (a.contribution ?? 0);
    }
    return b.weight - a.weight;
  });
  const top = sorted.slice(0, 8);

  return (
    <div
      className={`flex h-full flex-col rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 ${className}`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-base font-medium text-[var(--text-primary)]">
          {mode === "contribution" ? "Top contributors" : "Largest holdings"}
        </h3>
      </div>

      {loading ? (
        <div className="flex flex-1 flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-9 animate-pulse rounded bg-[var(--bg-muted)]"
            />
          ))}
        </div>
      ) : top.length === 0 ? (
        <p className="flex flex-1 items-center justify-center text-sm text-[var(--text-muted)]">
          Attribution unavailable
        </p>
      ) : (
        <ul className="min-h-0 flex-1 overflow-y-auto">
          {top.map((row) => {
            const metric =
              mode === "contribution" ? row.contribution : row.weight;
            const s =
              mode === "contribution"
                ? sentimentFromSigned(metric)
                : "none";
            return (
              <li
                key={row.symbol}
                className="flex items-center gap-2 border-b border-[var(--border-subtle)] py-2 last:border-0"
              >
                <span className="w-16 shrink-0 font-mono text-sm tracking-tight text-[var(--text-primary)]">
                  {row.symbol}
                </span>
                <span
                  className="min-w-0 flex-1 truncate text-sm text-[var(--text-secondary)]"
                  title={row.name ?? undefined}
                >
                  {row.name ?? "—"}
                </span>
                <span
                  className={`shrink-0 text-sm tabular-nums ${
                    mode === "contribution"
                      ? sentimentClass(s)
                      : "text-[var(--text-primary)]"
                  }`}
                >
                  {mode === "contribution"
                    ? formatPercent(metric)
                    : formatWeight(metric)}
                </span>
              </li>
            );
          })}
        </ul>
      )}

      <Link
        href="/holdings"
        className="mt-3 text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]"
      >
        View all holdings →
      </Link>
    </div>
  );
}
