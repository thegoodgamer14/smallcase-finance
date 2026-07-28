"use client";

import { Check, ChevronDown, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { formatPercent } from "@/lib/format";
import { sentimentClass, sentimentFromSigned } from "@/lib/sentiment";
import type { SmallcaseListItem } from "@/lib/types";

export interface SmallcaseOption {
  id: string;
  name: string;
  constituentCount?: number | null;
  theme?: string | null;
  asOf?: string | null;
}

interface SmallcaseSelectProps {
  items: SmallcaseOption[];
  value: string | null;
  onChange: (id: string) => void;
  loading?: boolean;
  disabled?: boolean;
  periodReturnById?: Record<string, number>;
  placeholder?: string;
  className?: string;
}

export function toOptions(items: SmallcaseListItem[]): SmallcaseOption[] {
  return items.map((s) => ({
    id: s.id,
    name: s.name,
    constituentCount: s.constituent_count,
    theme: s.theme,
    asOf: s.as_of,
  }));
}

export function SmallcaseSelect({
  items,
  value,
  onChange,
  loading = false,
  disabled = false,
  periodReturnById,
  placeholder = "Select smallcase",
  className = "",
}: SmallcaseSelectProps) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const active = items.find((i) => i.id === value) ?? null;
  const activeReturn =
    value && periodReturnById ? periodReturnById[value] : undefined;

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.id.toLowerCase().includes(q),
    );
  }, [items, filter]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (loading) {
    return (
      <div
        className={`h-9 min-w-[200px] max-w-[280px] animate-pulse rounded-md bg-[var(--bg-muted)] ${className}`}
      />
    );
  }

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled || items.length === 0}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex h-9 min-w-[200px] max-w-[280px] items-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <span className="min-w-0 flex-1 truncate text-left">
          {active?.name ?? placeholder}
        </span>
        {activeReturn != null ? (
          <span
            className={`shrink-0 text-xs tabular-nums ${sentimentClass(sentimentFromSigned(activeReturn))}`}
          >
            {formatPercent(activeReturn)}
          </span>
        ) : null}
        <ChevronDown size={14} className="shrink-0 text-[var(--text-muted)]" />
      </button>

      {open ? (
        <div
          className="absolute left-0 top-full z-50 mt-1 w-[min(100vw-2rem,320px)] overflow-hidden rounded-md border border-[var(--border-default)] bg-[var(--bg-surface-raised)] shadow-[0_8px_24px_rgba(0,0,0,0.35)]"
          role="listbox"
        >
          {items.length > 5 ? (
            <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2">
              <Search size={14} className="text-[var(--text-muted)]" />
              <input
                autoFocus
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter…"
                className="w-full bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
              />
            </div>
          ) : null}

          <ul className="max-h-80 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-3 py-4 text-center text-sm text-[var(--text-secondary)]">
                {items.length === 0
                  ? "No smallcases loaded"
                  : "No matches"}
              </li>
            ) : (
              filtered.map((item) => {
                const selected = item.id === value;
                const ret = periodReturnById?.[item.id];
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selected}
                      onClick={() => {
                        onChange(item.id);
                        setOpen(false);
                        setFilter("");
                      }}
                      className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-[var(--bg-hover)] ${
                        selected
                          ? "bg-[var(--accent-subtle)] text-[var(--accent)]"
                          : "text-[var(--text-primary)]"
                      }`}
                    >
                      <span className="w-4 shrink-0">
                        {selected ? <Check size={14} /> : null}
                      </span>
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {item.name}
                      </span>
                      {item.constituentCount != null ? (
                        <span className="shrink-0 text-xs text-[var(--text-muted)] tabular-nums">
                          {item.constituentCount}
                        </span>
                      ) : null}
                      {ret != null ? (
                        <span
                          className={`shrink-0 text-xs tabular-nums ${sentimentClass(sentimentFromSigned(ret))}`}
                        >
                          {formatPercent(ret)}
                        </span>
                      ) : null}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
