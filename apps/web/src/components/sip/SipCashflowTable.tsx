import { formatDate, formatInr } from "@/lib/format";
import type { SipCashflow } from "@/lib/types";

interface SipCashflowTableProps {
  cashflows: SipCashflow[];
  loading?: boolean;
  className?: string;
}

function kindLabel(kind: string): string {
  if (kind === "contribution") return "Contribution";
  if (kind === "terminal") return "Ending value";
  if (kind === "redemption") return "Redemption";
  return kind;
}

function kindRole(kind: string): string {
  if (kind === "contribution") return "Cash out of pocket";
  if (kind === "terminal") return "What the basket is worth";
  if (kind === "redemption") return "Cash received";
  return "";
}

/** Ending portfolio value (terminal) is the only row that should read as a positive outcome. */
function amountClass(kind: string, amount: number): string {
  if (kind === "terminal" && amount > 0) return "text-[var(--pnl-pos)]";
  if (kind === "redemption" && amount > 0) return "text-[var(--pnl-pos)]";
  // Contributions are cash you paid in — neutral, not “losses”
  return "text-[var(--text-primary)]";
}

export function SipCashflowTable({
  cashflows,
  loading = false,
  className = "",
}: SipCashflowTableProps) {
  return (
    <div
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] ${className}`}
    >
      <div className="space-y-1 border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-medium text-[var(--text-primary)]">
            Cashflows
          </h3>
          <p className="text-[11px] text-[var(--text-muted)]">
            − cash in · + ending value
          </p>
        </div>
        <p className="text-[11px] leading-relaxed text-[var(--text-muted)]">
          Each monthly SIP is cash you paid in (shown as −). The last row is the
          ending portfolio value (shown as +). XIRR uses both.
        </p>
      </div>

      <div className="max-h-[360px] overflow-auto">
        <table className="w-full min-w-[480px] border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-[var(--bg-surface)]">
            <tr className="border-b border-[var(--border-subtle)] text-xs text-[var(--text-secondary)]">
              <th scope="col" className="px-4 py-2 font-medium">
                Date
              </th>
              <th scope="col" className="px-4 py-2 font-medium">
                Type
              </th>
              <th scope="col" className="px-4 py-2 font-medium">
                Role
              </th>
              <th scope="col" className="px-4 py-2 text-right font-medium">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    <td className="px-4 py-2" colSpan={4}>
                      <div className="h-4 w-full animate-pulse rounded bg-[var(--bg-muted)]" />
                    </td>
                  </tr>
                ))
              : cashflows.map((cf, i) => {
                  const role = kindRole(cf.kind);
                  return (
                    <tr
                      key={`${cf.date}-${cf.kind}-${i}`}
                      className="border-b border-[var(--border-subtle)] last:border-0"
                    >
                      <td className="px-4 py-2 tabular-nums text-[var(--text-primary)]">
                        {formatDate(cf.date)}
                      </td>
                      <td className="px-4 py-2 text-[var(--text-secondary)]">
                        {kindLabel(cf.kind)}
                      </td>
                      <td className="px-4 py-2 text-[11px] text-[var(--text-muted)]">
                        {role || "—"}
                      </td>
                      <td
                        className={`px-4 py-2 text-right tabular-nums ${amountClass(cf.kind, cf.amount)}`}
                      >
                        {formatInr(cf.amount)}
                      </td>
                    </tr>
                  );
                })}
            {!loading && cashflows.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-8 text-center text-sm text-[var(--text-muted)]"
                >
                  No cashflows yet
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
