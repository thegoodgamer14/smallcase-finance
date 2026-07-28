"use client";

import { useEffect, useState } from "react";

import type { CustomRange } from "@/lib/context";

interface CustomRangePickerProps {
  value: CustomRange | null;
  onChange: (range: CustomRange | null) => void;
  className?: string;
}

/**
 * Optional custom inclusive timeline for performance evaluation.
 * When applied, preset window chips are cleared (see AppProvider).
 */
export function CustomRangePicker({
  value,
  onChange,
  className = "",
}: CustomRangePickerProps) {
  const [start, setStart] = useState(value?.start ?? "");
  const [end, setEnd] = useState(value?.end ?? "");

  useEffect(() => {
    setStart(value?.start ?? "");
    setEnd(value?.end ?? "");
  }, [value?.start, value?.end]);

  const valid = Boolean(start && end && start <= end);
  const active = Boolean(value);

  return (
    <div
      className={`flex flex-wrap items-end gap-2 ${className}`}
      role="group"
      aria-label="Custom date range"
    >
      <label className="flex flex-col gap-0.5 text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
        From
        <input
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          className="h-8 rounded-md border border-[var(--border-default)] bg-[var(--bg-elevated)] px-2 text-xs text-[var(--text-primary)]"
        />
      </label>
      <label className="flex flex-col gap-0.5 text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
        To
        <input
          type="date"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          className="h-8 rounded-md border border-[var(--border-default)] bg-[var(--bg-elevated)] px-2 text-xs text-[var(--text-primary)]"
        />
      </label>
      <button
        type="button"
        disabled={!valid}
        onClick={() => onChange({ start, end })}
        className={`h-8 rounded-md px-2.5 text-xs font-medium transition-colors disabled:opacity-40 ${
          active
            ? "bg-[var(--accent-subtle)] text-[var(--accent)]"
            : "border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
        }`}
      >
        Apply range
      </button>
      {active ? (
        <button
          type="button"
          onClick={() => onChange(null)}
          className="h-8 rounded-md px-2 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          Clear
        </button>
      ) : null}
    </div>
  );
}
