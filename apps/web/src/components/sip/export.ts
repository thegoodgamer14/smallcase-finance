import type { SipBacktestResponse } from "@/lib/types";

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Client-side summary JSON export from SIP response. */
export function exportSipJson(result: SipBacktestResponse) {
  const payload = {
    strategy_id: result.strategy_id,
    name: result.name,
    xirr: result.xirr,
    total_invested: result.total_invested,
    final_value: result.final_value,
    absolute_gain: result.absolute_gain,
    max_drawdown: result.max_drawdown,
    n_sips: result.n_sips,
    data_source: result.data_source,
    assumptions: result.assumptions,
    warnings: result.warnings,
    cashflows: result.cashflows,
    series: result.series,
    contribution: result.contribution,
    invest_dates: result.invest_dates,
    notes: result.notes,
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  downloadBlob(`sip-backtest-${result.strategy_id}.json`, blob);
}

/** Client-side cashflows CSV export. */
export function exportSipCashflowsCsv(result: SipBacktestResponse) {
  const header = "date,kind,amount";
  const rows = result.cashflows.map(
    (cf) => `${cf.date},${cf.kind},${cf.amount}`,
  );
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  downloadBlob(`sip-cashflows-${result.strategy_id}.csv`, blob);
}
