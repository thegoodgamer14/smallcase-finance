/** API DTOs aligned with FastAPI schemas (src/smallcase_finance/schemas/). */

export type MetricWindowApi =
  | "1M"
  | "3M"
  | "6M"
  | "1Y"
  | "YTD"
  | "ITD"
  | "custom";

/** UI window keys; SI maps to API ITD. */
export type WindowKey = "1M" | "3M" | "6M" | "1Y" | "YTD" | "SI";

export interface SmallcaseListItem {
  id: string;
  name: string;
  description?: string | null;
  theme?: string | null;
  currency: string;
  methodology: string;
  rebalance_rule: string;
  inception_date?: string | null;
  as_of?: string | null;
  constituent_count?: number | null;
}

export interface SmallcaseListResponse {
  items: SmallcaseListItem[];
}

export interface SmallcaseDetail {
  id: string;
  name: string;
  description?: string | null;
  theme?: string | null;
  currency: string;
  methodology: string;
  rebalance_rule: string;
  base_nav: number;
  inception_date?: string | null;
  benchmark_id?: string | null;
  notes?: string | null;
}

export interface HoldingItem {
  symbol: string;
  name?: string | null;
  weight: number;
  sector?: string | null;
}

export interface HoldingsResponse {
  smallcase_id: string;
  as_of: string;
  effective_from?: string | null;
  methodology?: string | null;
  holdings: HoldingItem[];
  weight_sum: number;
}

export interface PerformancePoint {
  date: string;
  nav: number;
  daily_return?: number | null;
}

export interface PerformanceResponse {
  smallcase_id: string;
  currency: string;
  start?: string | null;
  end?: string | null;
  series: PerformancePoint[];
  benchmark_series?: PerformancePoint[] | null;
}

export interface MetricValues {
  cagr?: number | null;
  volatility?: number | null;
  max_drawdown?: number | null;
  sharpe?: number | null;
  total_return?: number | null;
  n_observations?: number | null;
}

export interface MetricsAssumptions {
  periods_per_year: number;
  risk_free_rate: number;
  return_type: string;
  price_field: string;
}

export interface MetricsResponse {
  smallcase_id: string;
  start?: string | null;
  end?: string | null;
  window: MetricWindowApi;
  currency: string;
  metrics: MetricValues;
  assumptions: MetricsAssumptions;
}

export interface HealthResponse {
  status: string;
  version: string;
  data_curated_root: string;
  data_reachable: boolean;
}

export type Sentiment = "pos" | "neg" | "flat" | "none";

export interface HoldingRow {
  symbol: string;
  name?: string | null;
  weight: number;
  sector?: string | null;
  price?: number | null;
  periodReturn?: number | null;
  contribution?: number | null;
}

export interface ChartPoint {
  date: string;
  value: number;
}

export interface ChartSeries {
  id: string;
  name: string;
  data: ChartPoint[];
  color?: string;
  role?: "portfolio" | "benchmark" | "drawdown" | "other";
  strokeDasharray?: string;
  type?: "line" | "area";
}
