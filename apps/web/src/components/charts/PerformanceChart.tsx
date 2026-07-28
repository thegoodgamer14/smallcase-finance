"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatNav, formatPercent, formatShortDate } from "@/lib/format";
import type { ChartSeries } from "@/lib/types";

interface PerformanceChartProps {
  variant: "equity" | "drawdown";
  title?: string;
  subtitle?: string;
  series: ChartSeries[];
  height?: number;
  loading?: boolean;
  emptyMessage?: string;
  syncId?: string;
  showLegend?: boolean;
  yTickFormatter?: (n: number) => string;
  className?: string;
  error?: string | null;
}

function mergeSeries(series: ChartSeries[]) {
  const byDate = new Map<string, Record<string, string | number>>();
  for (const s of series) {
    for (const p of s.data) {
      const row = byDate.get(p.date) ?? { date: p.date };
      row[s.id] = p.value;
      byDate.set(p.date, row);
    }
  }
  return Array.from(byDate.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
}

function defaultColor(s: ChartSeries, variant: "equity" | "drawdown"): string {
  if (s.color) return s.color;
  if (variant === "drawdown" || s.role === "drawdown") return "var(--pnl-neg)";
  if (s.role === "benchmark") return "var(--chart-benchmark)";
  return "var(--chart-portfolio)";
}

export function PerformanceChart({
  variant,
  title,
  subtitle,
  series,
  height,
  loading = false,
  emptyMessage = "No data for selected range",
  syncId,
  showLegend = true,
  yTickFormatter,
  className = "",
  error,
}: PerformanceChartProps) {
  const h = height ?? (variant === "equity" ? 360 : 260);
  const data = mergeSeries(series);
  const empty = !loading && !error && data.length === 0;

  const yFmt =
    yTickFormatter ??
    (variant === "drawdown"
      ? (n: number) => formatPercent(n, 0)
      : (n: number) => formatNav(n, 0));

  return (
    <div
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 ${className}`}
    >
      {(title || showLegend) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            {title ? (
              <h3 className="text-base font-medium text-[var(--text-primary)]">
                {title}
              </h3>
            ) : null}
            {subtitle ? (
              <p className="text-xs text-[var(--text-muted)]">{subtitle}</p>
            ) : null}
          </div>
        </div>
      )}

      {loading ? (
        <div
          className="animate-pulse rounded-lg bg-[var(--bg-muted)]"
          style={{ height: h }}
        />
      ) : error ? (
        <div
          className="flex items-center justify-center text-sm text-[var(--text-secondary)]"
          style={{ height: h }}
        >
          {error}
        </div>
      ) : empty ? (
        <div
          className="flex items-center justify-center text-sm text-[var(--text-muted)]"
          style={{ height: h }}
        >
          {emptyMessage}
        </div>
      ) : variant === "drawdown" ? (
        <ResponsiveContainer width="100%" height={h}>
          <AreaChart data={data} syncId={syncId} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid
              stroke="var(--border-subtle)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => formatShortDate(String(v))}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={{ stroke: "var(--border-subtle)" }}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              tickFormatter={yFmt}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={52}
              domain={["dataMin", 0]}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-surface-raised)",
                border: "1px solid var(--border-default)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ fontWeight: 600, marginBottom: 4 }}
              labelFormatter={(l) => formatShortDate(String(l))}
              formatter={(value) => [
                formatPercent(typeof value === "number" ? value : Number(value)),
                "Drawdown",
              ]}
            />
            {showLegend ? (
              <Legend
                wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }}
              />
            ) : null}
            {series.map((s) => (
              <Area
                key={s.id}
                type="monotone"
                dataKey={s.id}
                name={s.name}
                stroke={defaultColor(s, variant)}
                fill={defaultColor(s, variant)}
                fillOpacity={0.25}
                strokeWidth={2}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={h}>
          <LineChart data={data} syncId={syncId} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid
              stroke="var(--border-subtle)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => formatShortDate(String(v))}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={{ stroke: "var(--border-subtle)" }}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              tickFormatter={yFmt}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={52}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-surface-raised)",
                border: "1px solid var(--border-default)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ fontWeight: 600, marginBottom: 4 }}
              labelFormatter={(l) => formatShortDate(String(l))}
              formatter={(value, name) => [
                formatNav(typeof value === "number" ? value : Number(value)),
                String(name),
              ]}
            />
            {showLegend ? (
              <Legend
                wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }}
              />
            ) : null}
            {series.map((s) => (
              <Line
                key={s.id}
                type="monotone"
                dataKey={s.id}
                name={s.name}
                stroke={defaultColor(s, variant)}
                strokeWidth={2}
                strokeDasharray={
                  s.strokeDasharray ??
                  (s.role === "benchmark" ? "6 4" : undefined)
                }
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
