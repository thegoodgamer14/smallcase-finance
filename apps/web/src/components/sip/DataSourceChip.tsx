import type { SipDataSource } from "@/lib/types";

const COPY = {
  upstox: "Prices: Upstox (cached)",
  sample: "Demo / sample prices — not live market SIP performance",
  partial: "Partial Upstox coverage · some symbols sample or missing",
  fixture: "Demo / sample prices — not live market SIP performance",
  mixed: "Partial Upstox coverage · some symbols sample or missing",
  unknown: "Price source unknown",
} as const;

function normalizeSource(
  source: SipDataSource | string | null | undefined,
): keyof typeof COPY {
  if (!source) return "unknown";
  if (source === "upstox") return "upstox";
  if (source === "sample" || source === "fixture") return "sample";
  if (source === "mixed") return "mixed";
  return "unknown";
}

export function isDemoSource(
  source: SipDataSource | string | null | undefined,
): boolean {
  const s = normalizeSource(source);
  return s === "sample" || s === "mixed" || s === "unknown";
}

interface DataSourceChipProps {
  dataSource: SipDataSource | string | null | undefined;
  className?: string;
}

/** Result-scoped chip: demo vs Upstox (ADR 005). */
export function DataSourceChip({
  dataSource,
  className = "",
}: DataSourceChipProps) {
  const key = normalizeSource(dataSource);
  const label = COPY[key];
  const demo = isDemoSource(dataSource);

  return (
    <span
      className={`inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        demo
          ? "border-[var(--risk-warning)]/50 bg-[var(--risk-warning)]/10 text-[var(--risk-warning)]"
          : "border-[var(--accent)]/40 bg-[var(--accent-subtle)] text-[var(--accent)]"
      } ${className}`}
      title={label}
    >
      <span className="truncate">{label}</span>
    </span>
  );
}

interface DataSourceBannerProps {
  dataSource: SipDataSource | string | null | undefined;
  className?: string;
}

/** Full-width banner under result chip when sample/demo. */
export function SipDataSourceBanner({
  dataSource,
  className = "",
}: DataSourceBannerProps) {
  const demo = isDemoSource(dataSource);
  const message = demo
    ? "These results use demo or sample prices. Do not treat them as real market SIP performance. Connect Upstox and sync history for real claims."
    : "Prices from Upstox history (cached). Sole market-data source for real runs.";

  return (
    <div
      className={`rounded-md border px-3 py-2 text-xs ${
        demo
          ? "border-[var(--risk-warning)]/40 bg-[var(--risk-warning)]/10 text-[var(--text-primary)]"
          : "border-[var(--border-default)] bg-[var(--bg-muted)] text-[var(--text-secondary)]"
      } ${className}`}
      role="status"
    >
      {message}
    </div>
  );
}
