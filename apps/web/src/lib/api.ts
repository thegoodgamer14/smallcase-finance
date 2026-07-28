import type {
  HealthResponse,
  HoldingsResponse,
  MetricsResponse,
  PerformanceResponse,
  SipBacktestRequest,
  SipBacktestResponse,
  SmallcaseDetail,
  SmallcaseListResponse,
  StrategyDetail,
  StrategyListResponse,
  WindowKey,
} from "./types";
import { toApiWindow } from "./windows";

const DEFAULT_BASE = "http://127.0.0.1:8000";

export function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || DEFAULT_BASE
  );
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBase()}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Cannot reach API at ${apiBase()}. Is the backend running?`,
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail || `HTTP ${res.status}`, res.status);
  }

  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export function listSmallcases(params?: {
  q?: string;
  tag?: string;
}): Promise<SmallcaseListResponse> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.tag) sp.set("tag", params.tag);
  const qs = sp.toString();
  return apiFetch<SmallcaseListResponse>(`/smallcases${qs ? `?${qs}` : ""}`);
}

export function getSmallcase(id: string): Promise<SmallcaseDetail> {
  return apiFetch<SmallcaseDetail>(`/smallcases/${encodeURIComponent(id)}`);
}

export function getHoldings(
  id: string,
  asOf?: string,
): Promise<HoldingsResponse> {
  const sp = new URLSearchParams();
  if (asOf) sp.set("as_of", asOf);
  const qs = sp.toString();
  return apiFetch<HoldingsResponse>(
    `/smallcases/${encodeURIComponent(id)}/holdings${qs ? `?${qs}` : ""}`,
  );
}

export function getPerformance(
  id: string,
  opts?: { start?: string; end?: string; benchmark?: boolean },
): Promise<PerformanceResponse> {
  const sp = new URLSearchParams();
  if (opts?.start) sp.set("start", opts.start);
  if (opts?.end) sp.set("end", opts.end);
  if (opts?.benchmark) sp.set("benchmark", "true");
  const qs = sp.toString();
  return apiFetch<PerformanceResponse>(
    `/smallcases/${encodeURIComponent(id)}/performance${qs ? `?${qs}` : ""}`,
  );
}

export function getMetrics(
  id: string,
  window: WindowKey = "SI",
  opts?: { start?: string; end?: string },
): Promise<MetricsResponse> {
  const sp = new URLSearchParams();
  if (opts?.start && opts?.end) {
    sp.set("start", opts.start);
    sp.set("end", opts.end);
  } else {
    sp.set("window", toApiWindow(window));
  }
  return apiFetch<MetricsResponse>(
    `/smallcases/${encodeURIComponent(id)}/metrics?${sp.toString()}`,
  );
}

export interface UpstoxStatusResponse {
  provider: string;
  configured: boolean;
  sync_http_enabled: boolean;
  default_years: number;
  hint: string;
}

export function getUpstoxStatus(): Promise<UpstoxStatusResponse> {
  return apiFetch<UpstoxStatusResponse>("/integrations/upstox/status");
}

/** Fetch metrics for several windows (period returns grid). */
export async function getMetricsMulti(
  id: string,
  windows: WindowKey[],
): Promise<Partial<Record<WindowKey, MetricsResponse>>> {
  const results = await Promise.allSettled(
    windows.map((w) => getMetrics(id, w)),
  );
  const out: Partial<Record<WindowKey, MetricsResponse>> = {};
  results.forEach((r, i) => {
    if (r.status === "fulfilled") out[windows[i]] = r.value;
  });
  return out;
}

// ── SIP Lab ──────────────────────────────────────────────────────────────────

/** File-backed SIP strategies under config/strategies/. */
export function listStrategies(): Promise<StrategyListResponse> {
  return apiFetch<StrategyListResponse>("/strategies");
}

export function getStrategy(id: string): Promise<StrategyDetail> {
  return apiFetch<StrategyDetail>(
    `/strategies/${encodeURIComponent(id)}`,
  );
}

/**
 * Run monthly SIP cashflow backtest (primary metric XIRR).
 * Uses POST /backtests/sip — never the v0 rebalance POST /backtest.
 */
export function postSipBacktest(
  body: SipBacktestRequest,
): Promise<SipBacktestResponse> {
  return apiFetch<SipBacktestResponse>("/backtests/sip", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
