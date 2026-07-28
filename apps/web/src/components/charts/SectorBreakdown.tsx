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

export interface SectorWeight {
  label: string;
  weight: number;
}

const SECTOR_COLORS = [
  "#60A5FA",
  "#34D399",
  "#FBBF24",
  "#F472B6",
  "#A78BFA",
  "#22D3EE",
  "#FB923C",
  "#94A3B8",
];

interface SectorBreakdownProps {
  data: SectorWeight[];
  title?: string;
  height?: number;
  loading?: boolean;
  className?: string;
}

export function SectorBreakdown({
  data,
  title = "Sector mix",
  height = 280,
  loading = false,
  className = "",
}: SectorBreakdownProps) {
  const sorted = [...data].sort((a, b) => b.weight - a.weight);
  const top = sorted.slice(0, 8);
  const rest = sorted.slice(8);
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
          No sector data
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
              width={100}
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
              fill={SECTOR_COLORS[0]}
              radius={[0, 4, 4, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

/** Aggregate holdings by sector. */
export function aggregateSectors(
  holdings: { sector?: string | null; weight: number }[],
): SectorWeight[] {
  const map = new Map<string, number>();
  for (const h of holdings) {
    const key = h.sector?.trim() || "Unclassified";
    map.set(key, (map.get(key) ?? 0) + h.weight);
  }
  return Array.from(map.entries()).map(([label, weight]) => ({
    label,
    weight,
  }));
}
