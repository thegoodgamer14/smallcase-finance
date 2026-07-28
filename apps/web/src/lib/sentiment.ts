import type { Sentiment } from "./types";

const FLAT_EPS = 1e-6;

/** Map a signed fraction (return, contrib) to P&L sentiment. */
export function sentimentFromSigned(
  value: number | null | undefined,
): Sentiment {
  if (value == null || Number.isNaN(value)) return "none";
  if (Math.abs(value) < FLAT_EPS) return "flat";
  return value > 0 ? "pos" : "neg";
}

/** Max drawdown is always negative when present. */
export function sentimentMaxDrawdown(
  value: number | null | undefined,
): Sentiment {
  if (value == null || Number.isNaN(value)) return "none";
  return "neg";
}

export function sentimentClass(sentiment: Sentiment): string {
  switch (sentiment) {
    case "pos":
      return "text-[var(--pnl-pos)]";
    case "neg":
      return "text-[var(--pnl-neg)]";
    case "flat":
      return "text-[var(--text-secondary)]";
    default:
      return "text-[var(--text-primary)]";
  }
}
