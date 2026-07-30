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

// ── SIP Lab ──────────────────────────────────────────────────────────────────

/** Result-scoped price provenance for demo vs Upstox banners. */
export type SipDataSource =
  | "upstox"
  | "sample"
  | "fixture"
  | "mixed"
  | "unknown";

export interface StrategySummary {
  id: string;
  name: string;
  summary?: string | null;
  currency: string;
  sip_amount: number;
  day_of_month: number;
  start_date: string;
  end_date?: string | null;
  allocation_mode: string;
  n_constituents?: number | null;
  version: string;
}

export interface StrategyListResponse {
  items: StrategySummary[];
}

export interface StrategyDetail {
  id: string;
  name: string;
  currency: string;
  version: string;
  notes?: string | null;
  allocation_mode: string;
  price_field: string;
  rebalance_mode: string;
  fractional_units: boolean;
  basket: Record<string, unknown>;
  sip: Record<string, unknown>;
  costs: Record<string, unknown>;
  source_path?: string | null;
}

export interface SipBacktestRequest {
  strategy_id?: string;
  strategy?: Record<string, unknown>;
  amount?: number;
  day_of_month?: number;
  start?: string;
  end?: string;
  as_of?: string;
}

export interface SipCashflow {
  date: string;
  amount: number;
  kind: string;
}

export interface SipSeriesPoint {
  date: string;
  market_value: number;
  total_invested_to_date: number;
  has_sip: boolean;
}

export interface SipSymbolContribution {
  symbol: string;
  cash_in: number;
  units_end: number;
  price_end?: number | null;
  market_value_end: number;
  contribution: number;
  weight_end?: number | null;
}

export interface SipAssumptions {
  primary_metric: string;
  sip_day_rule: string;
  costs: string;
  costs_zero: boolean;
  price_field: string;
  xirr_day_count: string;
  fractional_units: boolean;
  currency: string;
  rebalance_mode: string;
  not_v0_rebalance: boolean;
}

export interface SipMetrics {
  total_invested: number;
  final_value: number;
  absolute_gain: number;
  n_sips: number;
  first_sip?: string | null;
  last_sip?: string | null;
  as_of?: string | null;
  max_drawdown?: number | null;
  volatility?: number | null;
  cagr_mv?: number | null;
  xirr_status: string;
  xirr_message?: string | null;
  xirr_day_count: string;
}

export interface SipBacktestResponse {
  strategy_id: string;
  name?: string | null;
  xirr: number | null;
  total_invested: number;
  final_value: number;
  max_drawdown?: number | null;
  absolute_gain?: number | null;
  n_sips: number;
  series: SipSeriesPoint[];
  cashflows: SipCashflow[];
  data_source: SipDataSource | string;
  assumptions: SipAssumptions;
  warnings: string[];
  invest_dates: string[];
  units_end: Record<string, number>;
  contribution: SipSymbolContribution[];
  metrics?: SipMetrics | null;
  notes?: string;
}

// ── Portfolio Decision v1 ────────────────────────────────────────────────────

export interface PortfolioHoldingItem {
  symbol: string;
  exchange: string;
  quantity: number;
  average_price?: number | null;
  last_price?: number | null;
  value?: number | null;
  weight?: number | null;
  pnl?: number | null;
  product?: string | null;
  isin?: string | null;
  sector?: string | null;
}

export interface PortfolioResponse {
  snapshot_id: string;
  synced_at: string;
  source: string;
  currency: string;
  total_value?: number | null;
  position_count: number;
  holdings: PortfolioHoldingItem[];
  warnings: string[];
}

export interface PortfolioStatusResponse {
  kite_app_configured: boolean;
  kite_session_configured: boolean;
  login_url?: string | null;
  has_snapshot: boolean;
  latest_synced_at?: string | null;
  position_count: number;
  total_value?: number | null;
  currency: string;
  message: string;
}

export interface PortfolioSymbolsResponse {
  symbols: string[];
  synced_at?: string | null;
}

export interface DecisionConstituent {
  symbol: string;
  target_weight?: number | null;
}

export interface DecisionRunRequest {
  basket: {
    mode: "custom_weights" | "equal_weight";
    constituents: DecisionConstituent[];
  };
  sip: {
    amount: number;
    day_of_month: number;
    start_date: string;
    end_date?: string | null;
  };
  benchmark_symbol?: string | null;
  include_benchmark?: boolean;
  include_weight_gap?: boolean;
  strict_market_data?: boolean | null;
}

export interface SymbolCoverage {
  symbol: string;
  has_prices: boolean;
  start?: string | null;
  end?: string | null;
}

export interface PriceCoverageResponse {
  data_source: string;
  symbols: SymbolCoverage[];
}

export interface DecisionSeriesPoint {
  date: string;
  market_value: number;
  invested_cum: number;
}

export interface DecisionLegResult {
  symbol?: string | null;
  xirr?: number | null;
  total_invested: number;
  final_value: number;
  max_drawdown?: number | null;
  series: DecisionSeriesPoint[];
  cashflows_summary: Record<string, unknown>;
  data_source: string;
  warnings: string[];
}

export interface WeightGapRow {
  symbol: string;
  portfolio_weight: number;
  target_weight: number;
  delta_weight: number;
  approx_value_delta?: number | null;
}

export interface DecisionRunResponse {
  run_id: string;
  data_source: string;
  coverage: {
    basket_symbols: number;
    basket_with_prices: number;
    benchmark_ok: boolean;
    missing_symbols: string[];
    price_start?: string | null;
    price_end?: string | null;
  };
  warnings: string[];
  candidate: DecisionLegResult;
  benchmark?: DecisionLegResult | null;
  delta_xirr?: number | null;
  weight_gap: WeightGapRow[];
  disclaimer: string;
}
