"use client";

import type { WindowKey } from "@/lib/types";
import { WINDOW_OPTIONS } from "@/lib/windows";

interface RangeChipsProps {
  /** null = no preset selected (custom range active) */
  value: WindowKey | null;
  onChange: (w: WindowKey) => void;
  options?: WindowKey[];
  className?: string;
}

export function RangeChips({
  value,
  onChange,
  options = WINDOW_OPTIONS,
  className = "",
}: RangeChipsProps) {
  return (
    <div
      className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}
      role="group"
      aria-label="Date range"
    >
      {options.map((opt) => {
        const selected = value != null && opt === value;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            aria-pressed={selected}
            className={`h-8 rounded-md px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${
              selected
                ? "border border-transparent bg-[var(--accent-subtle)] text-[var(--accent)]"
                : "border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
