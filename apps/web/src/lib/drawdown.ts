import type { ChartPoint, PerformancePoint } from "./types";

/** Peak-to-trough drawdown from NAV: dd_t = nav_t / peak_t - 1 (≤ 0). */
export function drawdownFromNav(series: PerformancePoint[]): ChartPoint[] {
  let peak = -Infinity;
  return series.map((p) => {
    if (p.nav > peak) peak = p.nav;
    const dd = peak > 0 ? p.nav / peak - 1 : 0;
    return { date: p.date, value: dd };
  });
}
