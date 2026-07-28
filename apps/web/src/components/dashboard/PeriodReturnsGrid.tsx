"use client";

import { formatPercent } from "@/lib/format";
import { sentimentClass, sentimentFromSigned } from "@/lib/sentiment";
import type { WindowKey } from "@/lib/types";
import { WINDOW_OPTIONS } from "@/lib/windows";

interface PeriodReturnsGridProps {
  returns: Partial<Record<WindowKey, number | null>>;
  activeWindow: WindowKey;
  onSelectWindow: (w: WindowKey) => void;
  loading?: boolean;
  className?: string;
}

export function PeriodReturnsGrid({
  returns,
  activeWindow,
  onSelectWindow,
  loading = false,
  className = "",
}: PeriodReturnsGridProps) {
  return (
    <div
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 ${className}`}
    >
      <h3 className="mb-3 text-base font-medium text-[var(--text-primary)]">
        Returns by period
      </h3>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {WINDOW_OPTIONS.map((w) => {
          const active = w === activeWindow;
          const val = returns[w];
          const s = sentimentFromSigned(val ?? null);
          return (
            <button
              key={w}
              type="button"
              onClick={() => onSelectWindow(w)}
              className={`flex flex-col gap-1 rounded-md border px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent-subtle)]"
                  : "border-[var(--border-default)] hover:bg-[var(--bg-hover)]"
              }`}
            >
              <span className="text-xs font-medium text-[var(--text-secondary)]">
                {w}
              </span>
              {loading ? (
                <span className="h-5 w-14 animate-pulse rounded bg-[var(--bg-muted)]" />
              ) : (
                <span
                  className={`text-lg font-semibold tabular-nums ${sentimentClass(s)}`}
                >
                  {formatPercent(val ?? null)}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
