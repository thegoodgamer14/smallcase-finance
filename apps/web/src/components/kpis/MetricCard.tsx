import Link from "next/link";
import type { ReactNode } from "react";

import { sentimentClass } from "@/lib/sentiment";
import type { Sentiment } from "@/lib/types";

interface MetricCardProps {
  label: string;
  value: string | null;
  sentiment?: Sentiment;
  delta?: string | null;
  deltaSentiment?: Sentiment;
  hint?: string;
  loading?: boolean;
  onClick?: () => void;
  href?: string;
  size?: "default" | "compact";
  className?: string;
}

export function MetricCard({
  label,
  value,
  sentiment = "none",
  delta,
  deltaSentiment,
  hint,
  loading = false,
  onClick,
  href,
  size = "default",
  className = "",
}: MetricCardProps) {
  const display = value ?? "—";
  const valueSentiment = value == null ? "none" : sentiment;
  const valueColor = sentimentClass(valueSentiment);
  const deltaColor = sentimentClass(deltaSentiment ?? "none");

  const pad = size === "compact" ? "p-3" : "p-4";
  const valueSize =
    size === "compact" ? "text-lg sm:text-xl" : "text-2xl sm:text-[26px]";

  const interactive =
    Boolean(onClick || href) &&
    "transition-colors hover:border-[var(--accent)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50";

  const body: ReactNode = loading ? (
    <>
      <div className="h-3 w-16 animate-pulse rounded bg-[var(--bg-muted)]" />
      <div className="mt-2 h-7 w-24 animate-pulse rounded bg-[var(--bg-muted)]" />
      {size === "default" ? (
        <div className="mt-2 h-3 w-20 animate-pulse rounded bg-[var(--bg-muted)]" />
      ) : null}
    </>
  ) : (
    <>
      <span className="text-xs font-medium tracking-wide text-[var(--text-secondary)]">
        {label}
      </span>
      <span
        className={`${valueSize} font-semibold tabular-nums leading-tight ${valueColor}`}
      >
        {display}
      </span>
      {delta ? (
        <span className={`text-xs tabular-nums ${deltaColor || "text-[var(--text-secondary)]"}`}>
          {delta}
        </span>
      ) : null}
    </>
  );

  const sharedClass = `rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] ${pad} flex flex-col gap-1 min-w-0 ${interactive} ${className}`;

  if (href) {
    return (
      <Link href={href} className={sharedClass} title={hint}>
        {body}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${sharedClass} text-left`}
        title={hint}
      >
        {body}
      </button>
    );
  }

  return (
    <div className={sharedClass} title={hint}>
      {body}
    </div>
  );
}
