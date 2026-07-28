"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

const ITEMS = [
  {
    key: "xirr",
    text: "Start with XIRR. It answers: “If I had SIP’d this amount every month, what annualized return would I have earned?”",
  },
  {
    key: "invested_final",
    text: "Total invested is cash contributed. Final value is what the holdings are worth at the end. The gap is absolute gain or loss — not annualized.",
  },
  {
    key: "chart",
    text: "The portfolio value line is market value of units over time. The dashed line (if shown) is cumulative cash invested.",
  },
  {
    key: "cashflows",
    text: "The cashflow table is what XIRR uses: each monthly SIP is cash you paid in (shown as −); the last row is ending portfolio value (shown as +).",
  },
  {
    key: "drawdown",
    text: "Max drawdown is the worst peak-to-trough drop in portfolio market value — path risk, not XIRR.",
  },
  {
    key: "not_v0",
    text: "This is not the same as the Dashboard’s index-style return. Don’t mix the two numbers.",
  },
] as const;

interface HowToReadPanelProps {
  /** Expand by default after a successful run; collapse on idle. */
  defaultOpen?: boolean;
  className?: string;
}

export function HowToReadPanel({
  defaultOpen = false,
  className = "",
}: HowToReadPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    setOpen(defaultOpen);
  }, [defaultOpen]);

  return (
    <section
      id="how-to-read"
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] ${className}`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
      >
        <h3 className="text-sm font-medium text-[var(--text-primary)]">
          How to read these results
        </h3>
        <ChevronDown
          size={16}
          className={`shrink-0 text-[var(--text-secondary)] transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open ? (
        <ol className="list-decimal space-y-2 border-t border-[var(--border-subtle)] px-4 py-3 pl-8">
          {ITEMS.map((item) => (
            <li
              key={item.key}
              className="text-xs leading-relaxed text-[var(--text-secondary)]"
            >
              {item.text}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
