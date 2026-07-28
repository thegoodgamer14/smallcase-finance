/** Number / date formatters — INR-friendly, tabular-friendly display strings. */

const EN_IN = "en-IN";

export function formatPercent(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const pct = value * 100;
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(digits)}%`;
}

export function formatPercentAbs(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatNav(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(EN_IN, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatWeight(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatRatio(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatInr(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `₹${value.toLocaleString(EN_IN, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

/** Compact INR for chart axis ticks (₹2.5L, ₹1.2Cr). */
export function formatInrCompact(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (abs >= 1e7) {
    return `${sign}₹${(abs / 1e7).toFixed(digits)}Cr`;
  }
  if (abs >= 1e5) {
    return `${sign}₹${(abs / 1e5).toFixed(digits)}L`;
  }
  if (abs >= 1e3) {
    return `${sign}₹${(abs / 1e3).toFixed(digits)}k`;
  }
  return `${sign}₹${abs.toFixed(0)}`;
}

/** Signed INR with +/− for gains. */
export function formatInrSigned(
  value: number | null | undefined,
  digits = 0,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}₹${Math.abs(value).toLocaleString(EN_IN, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function formatCount(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(EN_IN);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(EN_IN, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatShortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(EN_IN, {
    day: "numeric",
    month: "short",
  });
}
