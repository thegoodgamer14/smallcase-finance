import type { MetricWindowApi, WindowKey } from "./types";

export const WINDOW_OPTIONS: WindowKey[] = [
  "1M",
  "3M",
  "6M",
  "1Y",
  "YTD",
  "SI",
];

/** UI SI → API ITD (inception-to-date). */
export function toApiWindow(window: WindowKey): MetricWindowApi {
  return window === "SI" ? "ITD" : window;
}

export function fromApiWindow(window: MetricWindowApi | string): WindowKey {
  if (window === "ITD" || window === "custom") return "SI";
  if (
    window === "1M" ||
    window === "3M" ||
    window === "6M" ||
    window === "1Y" ||
    window === "YTD"
  ) {
    return window;
  }
  return "SI";
}

export function isWindowKey(value: string | null | undefined): value is WindowKey {
  return (
    value === "1M" ||
    value === "3M" ||
    value === "6M" ||
    value === "1Y" ||
    value === "YTD" ||
    value === "SI"
  );
}
