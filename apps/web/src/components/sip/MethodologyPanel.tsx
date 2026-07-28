"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "sf-sip-methodology-open";

const BLOCKS: {
  id: string;
  title: string;
  body: string;
  severity: "info" | "warning";
  /** Shown when collapsed “preview” mode (idle first paint). */
  priority?: "high" | "normal";
}[] = [
  {
    id: "zero_costs",
    title: "Zero costs",
    severity: "info",
    priority: "high",
    body: "This version assumes zero brokerage, STT, stamp duty, slippage, and expense drag. Each SIP buys at the session close (or documented price field) for the full monthly amount.",
  },
  {
    id: "sip_day",
    title: "SIP day rule",
    severity: "info",
    priority: "high",
    body: "Contributions use a fixed calendar day of the month. If markets are closed that day, the SIP invests on the next trading day with available prices.",
  },
  {
    id: "xirr_primary",
    title: "XIRR is primary",
    severity: "info",
    priority: "high",
    body: "Headline performance is XIRR on cashflows (contributions + ending portfolio value). Path metrics (drawdown, market-value curve) support the story but do not replace XIRR.",
  },
  {
    id: "not_v0",
    title: "Not the same as the Dashboard return",
    severity: "warning",
    body: "This is not the same as the Dashboard’s index-style return. Don’t mix the two numbers.",
  },
  {
    id: "sample",
    title: "Demo prices",
    severity: "warning",
    priority: "high",
    body: "Sample or synthetic prices are for demos only — not live market SIP performance. Configure Upstox and sync for real history.",
  },
  {
    id: "upstox_only",
    title: "Upstox only for real history",
    severity: "info",
    body: "Equity/ETF history for real runs comes only from Upstox. Sample/demo prices are labeled separately.",
  },
];

interface MethodologyPanelProps {
  /** Prefer expanded for demo/sample results or idle first visit. */
  forceOpen?: boolean;
  /** When true and open, show only high-priority blocks until expanded. */
  previewMode?: boolean;
  className?: string;
}

export function MethodologyPanel({
  forceOpen,
  previewMode = false,
  className = "",
}: MethodologyPanelProps) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "0") setOpen(false);
      else if (stored === "1") setOpen(true);
      else if (forceOpen) setOpen(true);
    } catch {
      if (forceOpen) setOpen(true);
    }
  }, [forceOpen]);

  useEffect(() => {
    if (forceOpen) setOpen(true);
  }, [forceOpen]);

  function toggle() {
    setOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  const visible =
    previewMode && !showAll
      ? BLOCKS.filter((b) => b.priority === "high")
      : BLOCKS;
  const hasMore = previewMode && !showAll && visible.length < BLOCKS.length;

  return (
    <section
      id="methodology"
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] ${className}`}
    >
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
      >
        <span className="text-sm font-medium text-[var(--text-primary)]">
          How SIP Lab works
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 text-[var(--text-secondary)] transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open ? (
        <div className="space-y-3 border-t border-[var(--border-subtle)] px-4 py-3">
          {visible.map((b) => (
            <div key={b.id}>
              <p
                className={`text-xs font-medium ${
                  b.severity === "warning"
                    ? "text-[var(--risk-warning)]"
                    : "text-[var(--text-primary)]"
                }`}
              >
                {b.title}
              </p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">
                {b.body}
              </p>
            </div>
          ))}
          {hasMore ? (
            <button
              type="button"
              onClick={() => setShowAll(true)}
              className="text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]"
            >
              Show more methodology
            </button>
          ) : null}
          {previewMode && showAll ? (
            <button
              type="button"
              onClick={() => setShowAll(false)}
              className="text-xs font-medium text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            >
              Show less
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
