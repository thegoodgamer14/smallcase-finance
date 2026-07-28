"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatWeight } from "@/lib/format";

export interface WeightBarItem {
  label: string;
  weight: number;
}

interface WeightBarsProps {
  data: WeightBarItem[];
  title?: string;
  topN?: number;
  height?: number;
  loading?: boolean;
  className?: string;
}

export function WeightBars({
  data,
  title = "Weight distribution",
  topN = 12,
  height = 280,
  loading = false,
  className = "",
}: WeightBarsProps) {
  const sorted = [...data].sort((a, b) => b.weight - a.weight);
  const top = sorted.slice(0, topN);
  const rest = sorted.slice(topN);
  const chartData =
    rest.length > 0
      ? [
          ...top,
          {
            label: "Other",
            weight: rest.reduce((s, r) => s + r.weight, 0),
          },
        ]
      : top;

  return (
    <div
      className={`rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 ${className}`}
    >
      <h3 className="mb-3 text-base font-medium text-[var(--text-primary)]">
        {title}
      </h3>
      {loading ? (
        <div
          className="animate-pulse rounded-lg bg-[var(--bg-muted)]"
          style={{ height }}
        />
      ) : chartData.length === 0 ? (
        <div
          className="flex items-center justify-center text-sm text-[var(--text-muted)]"
          style={{ height }}
        >
          No holdings
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid
              stroke="var(--border-subtle)"
              strokeDasharray="3 3"
              horizontal={false}
            />
            <XAxis
              type="number"
              tickFormatter={(v) => formatWeight(Number(v))}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={72}
              tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-surface-raised)",
                border: "1px solid var(--border-default)",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value) => [
                formatWeight(typeof value === "number" ? value : Number(value)),
                "Weight",
              ]}
            />
            <Bar
              dataKey="weight"
              fill="var(--chart-portfolio)"
              radius={[0, 4, 4, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
