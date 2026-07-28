"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError, listSmallcases } from "./api";
import {
  getStoredSmallcase,
  setStoredSmallcase,
  type Theme,
  getStoredTheme,
  setStoredTheme,
  applyTheme,
} from "./theme";
import type { SmallcaseListItem, WindowKey } from "./types";
import { isWindowKey } from "./windows";

/** Custom inclusive evaluation range (ISO YYYY-MM-DD), optional. */
export interface CustomRange {
  start: string;
  end: string;
}

interface AppContextValue {
  smallcases: SmallcaseListItem[];
  smallcasesLoading: boolean;
  smallcasesError: string | null;
  refreshSmallcases: () => Promise<void>;
  smallcaseId: string | null;
  setSmallcaseId: (id: string) => void;
  activeSmallcase: SmallcaseListItem | null;
  window: WindowKey;
  setWindow: (w: WindowKey) => void;
  /** When set, metrics/performance use this range instead of preset window chips. */
  customRange: CustomRange | null;
  setCustomRange: (range: CustomRange | null) => void;
  theme: Theme;
  toggleTheme: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [smallcases, setSmallcases] = useState<SmallcaseListItem[]>([]);
  const [smallcasesLoading, setSmallcasesLoading] = useState(true);
  const [smallcasesError, setSmallcasesError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>("dark");

  const urlSmallcase = searchParams.get("smallcase");
  const urlWindow = searchParams.get("window");
  const urlFrom = searchParams.get("from");
  const urlTo = searchParams.get("to");

  const window: WindowKey = isWindowKey(urlWindow) ? urlWindow : "SI";

  const customRange: CustomRange | null =
    urlFrom && urlTo && urlFrom <= urlTo
      ? { start: urlFrom, end: urlTo }
      : null;

  const [resolvedId, setResolvedId] = useState<string | null>(urlSmallcase);

  const replaceQuery = useCallback(
    (next: {
      smallcase?: string | null;
      window?: WindowKey;
      from?: string | null;
      to?: string | null;
      clearCustom?: boolean;
    }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next.smallcase !== undefined) {
        if (next.smallcase) params.set("smallcase", next.smallcase);
        else params.delete("smallcase");
      }
      if (next.window !== undefined) {
        if (next.window === "SI") params.delete("window");
        else params.set("window", next.window);
      }
      if (next.clearCustom) {
        params.delete("from");
        params.delete("to");
      } else {
        if (next.from !== undefined) {
          if (next.from) params.set("from", next.from);
          else params.delete("from");
        }
        if (next.to !== undefined) {
          if (next.to) params.set("to", next.to);
          else params.delete("to");
        }
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const refreshSmallcases = useCallback(async () => {
    setSmallcasesLoading(true);
    setSmallcasesError(null);
    try {
      const res = await listSmallcases();
      setSmallcases(res.items);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to load smallcases";
      setSmallcasesError(msg);
      setSmallcases([]);
    } finally {
      setSmallcasesLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = getStoredTheme();
    setTheme(t);
    applyTheme(t);
    void refreshSmallcases();
  }, [refreshSmallcases]);

  // Resolve active smallcase: URL → localStorage → first item
  useEffect(() => {
    if (smallcasesLoading) return;
    if (smallcases.length === 0) {
      setResolvedId(null);
      return;
    }
    const stored = getStoredSmallcase();
    const candidate =
      (urlSmallcase && smallcases.some((s) => s.id === urlSmallcase)
        ? urlSmallcase
        : null) ||
      (stored && smallcases.some((s) => s.id === stored) ? stored : null) ||
      smallcases[0].id;

    setResolvedId(candidate);
    if (candidate !== urlSmallcase) {
      replaceQuery({ smallcase: candidate });
    }
    if (candidate) setStoredSmallcase(candidate);
  }, [smallcases, smallcasesLoading, urlSmallcase, replaceQuery]);

  const setSmallcaseId = useCallback(
    (id: string) => {
      setResolvedId(id);
      setStoredSmallcase(id);
      replaceQuery({ smallcase: id });
    },
    [replaceQuery],
  );

  const setWindow = useCallback(
    (w: WindowKey) => {
      // Preset chip clears custom range so the two modes don't fight
      replaceQuery({ window: w, clearCustom: true });
    },
    [replaceQuery],
  );

  const setCustomRange = useCallback(
    (range: CustomRange | null) => {
      if (!range) {
        replaceQuery({ clearCustom: true });
        return;
      }
      replaceQuery({ from: range.start, to: range.end });
    },
    [replaceQuery],
  );

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      setStoredTheme(next);
      return next;
    });
  }, []);

  const activeSmallcase = useMemo(
    () => smallcases.find((s) => s.id === resolvedId) ?? null,
    [smallcases, resolvedId],
  );

  const value = useMemo<AppContextValue>(
    () => ({
      smallcases,
      smallcasesLoading,
      smallcasesError,
      refreshSmallcases,
      smallcaseId: resolvedId,
      setSmallcaseId,
      activeSmallcase,
      window,
      setWindow,
      customRange,
      setCustomRange,
      theme,
      toggleTheme,
    }),
    [
      smallcases,
      smallcasesLoading,
      smallcasesError,
      refreshSmallcases,
      resolvedId,
      setSmallcaseId,
      activeSmallcase,
      window,
      setWindow,
      customRange,
      setCustomRange,
      theme,
      toggleTheme,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
