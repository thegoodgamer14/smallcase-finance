"use client";

import { FlaskConical } from "lucide-react";
import Link from "next/link";

interface SipDashCalloutProps {
  className?: string;
}

/** Dashboard strip → SIP Lab (external visitor copy). */
export function SipDashCallout({ className = "" }: SipDashCalloutProps) {
  return (
    <aside
      className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3 ${className}`}
      aria-label="SIP Lab"
    >
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[var(--accent-subtle)] text-[var(--accent)]">
          <FlaskConical size={16} aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            Try SIP Lab
          </p>
          <p className="mt-0.5 max-w-xl text-xs text-[var(--text-secondary)]">
            This page shows how a rebalanced basket’s index performed. SIP Lab is
            different: it simulates putting a fixed ₹ amount into a basket every
            month and reports one annualized return (XIRR).
          </p>
          <p className="mt-1 text-[11px] text-[var(--text-muted)]">
            No orders · equities &amp; ETFs only
          </p>
        </div>
      </div>
      <Link
        href="/sip-lab"
        className="shrink-0 rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
      >
        Open SIP Lab
      </Link>
    </aside>
  );
}
