import { formatInr, formatWeight } from "@/lib/format";
import type { SipSymbolContribution } from "@/lib/types";

interface SipHoldingTableProps {
  contribution: SipSymbolContribution[];
  loading?: boolean;
  className?: string;
}

export function SipHoldingTable({
  contribution,
  loading = false,
  className = "",
}: SipHoldingTableProps) {
  return (
    <div
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] ${className}`}
    >
      <div className="space-y-1 border-b border-[var(--border-subtle)] px-4 py-3">
        <h3 className="text-sm font-medium text-[var(--text-primary)]">
          By holding
        </h3>
        <p className="text-[11px] text-[var(--text-muted)]">
          How each name contributed cash and ending value.
        </p>
      </div>
      {loading ? (
        <div className="space-y-2 px-4 py-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-4 w-full animate-pulse rounded bg-[var(--bg-muted)]"
            />
          ))}
        </div>
      ) : !contribution.length ? (
        <p className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">
          No holding breakdown for this run
        </p>
      ) : (
        <div className="max-h-[360px] overflow-auto">
          <table className="w-full min-w-[520px] border-collapse text-left text-sm">
            <thead className="sticky top-0 z-10 bg-[var(--bg-surface)]">
              <tr className="border-b border-[var(--border-subtle)] text-xs text-[var(--text-secondary)]">
                <th scope="col" className="px-4 py-2 font-medium">
                  Symbol
                </th>
                <th scope="col" className="px-4 py-2 text-right font-medium">
                  End weight
                </th>
                <th scope="col" className="px-4 py-2 text-right font-medium">
                  Units
                </th>
                <th scope="col" className="px-4 py-2 text-right font-medium">
                  Value (end)
                </th>
                <th scope="col" className="px-4 py-2 text-right font-medium">
                  Cash put in
                </th>
              </tr>
            </thead>
            <tbody>
              {contribution.map((row) => (
                <tr
                  key={row.symbol}
                  className="border-b border-[var(--border-subtle)] last:border-0"
                >
                  <td className="px-4 py-2 font-medium tabular-nums text-[var(--text-primary)]">
                    {row.symbol}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-[var(--text-secondary)]">
                    {formatWeight(row.weight_end)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-[var(--text-secondary)]">
                    {row.units_end.toLocaleString("en-IN", {
                      maximumFractionDigits: 4,
                    })}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-[var(--text-primary)]">
                    {formatInr(row.market_value_end)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-[var(--text-secondary)]">
                    {formatInr(row.cash_in)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
