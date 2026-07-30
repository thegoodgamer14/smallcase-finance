"use client";

import { Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorBanner } from "@/components/feedback/ErrorBanner";
import { MetricCard } from "@/components/kpis/MetricCard";
import {
  ApiError,
  getPortfolioHoldingsLatest,
  getPortfolioStatus,
  refreshPortfolio,
} from "@/lib/api";
import {
  formatDate,
  formatInr,
  formatInrCompact,
  formatWeight,
} from "@/lib/format";
import type { PortfolioResponse, PortfolioStatusResponse } from "@/lib/types";

export default function PortfolioPage() {
  const [status, setStatus] = useState<PortfolioStatusResponse | null>(null);
  const [book, setBook] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const st = await getPortfolioStatus();
      setStatus(st);
      if (st.has_snapshot) {
        try {
          const h = await getPortfolioHoldingsLatest();
          setBook(h);
        } catch (e) {
          if (e instanceof ApiError && e.status === 404) {
            setBook(null);
          } else {
            throw e;
          }
        }
      } else {
        setBook(null);
      }
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to load portfolio",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const h = await refreshPortfolio();
      setBook(h);
      const st = await getPortfolioStatus();
      setStatus(st);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Refresh failed",
      );
    } finally {
      setRefreshing(false);
    }
  };

  const selectedForDecide =
    book?.holdings
      .slice(0, 8)
      .map((h) => h.symbol)
      .join(",") ?? "";

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Portfolio</h1>
          <p className="mt-1 max-w-xl text-sm text-[var(--text-secondary)]">
            Your live equity book from Kite (read-only). Prices for backtests still
            come from Upstox. This is not theme demo holdings.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void onRefresh()}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {refreshing ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <RefreshCw size={16} />
          )}
          Refresh holdings
        </button>
      </div>

      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}

      <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 text-sm">
        <p className="font-medium text-[var(--text-primary)]">Kite connection</p>
        {status ? (
          <ul className="mt-2 space-y-1 text-[var(--text-secondary)]">
            <li>
              App credentials:{" "}
              {status.kite_app_configured ? "configured" : "missing"}
            </li>
            <li>
              Session token:{" "}
              {status.kite_session_configured ? "present" : "needs login"}
            </li>
            <li>{status.message}</li>
            {status.latest_synced_at ? (
              <li>
                Last snapshot: {formatDate(status.latest_synced_at.slice(0, 10))}{" "}
                <span className="text-[var(--text-muted)]">
                  ({status.latest_synced_at})
                </span>
              </li>
            ) : null}
            {status.login_url ? (
              <li>
                <a
                  href={status.login_url}
                  className="text-[var(--accent)] underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open Kite login
                </a>
              </li>
            ) : null}
          </ul>
        ) : loading ? (
          <p className="mt-2 text-[var(--text-muted)]">Loading status…</p>
        ) : null}
      </div>

      {book ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard
              label="Equity value"
              value={
                book.total_value != null
                  ? formatInrCompact(book.total_value)
                  : "—"
              }
            />
            <MetricCard label="Positions" value={String(book.position_count)} />
            <MetricCard label="Source" value={book.source.toUpperCase()} />
            <MetricCard
              label="Snapshot"
              value={book.snapshot_id.slice(0, 14)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <Link
              href={
                selectedForDecide
                  ? `/decide?symbols=${encodeURIComponent(selectedForDecide)}`
                  : "/decide"
              }
              className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-medium hover:bg-[var(--bg-hover)]"
            >
              Use top holdings in Decision Lab
            </Link>
            <Link
              href="/decide"
              className="rounded-md border border-[var(--border-default)] px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
            >
              Open Decision Lab
            </Link>
          </div>

          <div className="overflow-x-auto rounded-lg border border-[var(--border-default)]">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[var(--bg-surface)] text-[11px] uppercase tracking-wide text-[var(--text-muted)]">
                <tr>
                  <th className="px-3 py-2">Symbol</th>
                  <th className="px-3 py-2">Exch</th>
                  <th className="px-3 py-2 text-right">Qty</th>
                  <th className="px-3 py-2 text-right">Avg</th>
                  <th className="px-3 py-2 text-right">LTP</th>
                  <th className="px-3 py-2 text-right">Value</th>
                  <th className="px-3 py-2 text-right">Weight</th>
                  <th className="px-3 py-2">Product</th>
                </tr>
              </thead>
              <tbody>
                {book.holdings.map((h) => (
                  <tr
                    key={`${h.symbol}-${h.exchange}-${h.product}`}
                    className="border-t border-[var(--border-subtle)]"
                  >
                    <td className="px-3 py-2 font-medium">{h.symbol}</td>
                    <td className="px-3 py-2 text-[var(--text-secondary)]">
                      {h.exchange || "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {h.quantity}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {h.average_price != null ? formatInr(h.average_price) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {h.last_price != null ? formatInr(h.last_price) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {h.value != null ? formatInr(h.value) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatWeight(h.weight)}
                    </td>
                    <td className="px-3 py-2 text-[var(--text-secondary)]">
                      {h.product || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : !loading ? (
        <EmptyState
          title="No portfolio snapshot yet"
          description="Connect Kite (API key + daily login), set KITE_ACCESS_TOKEN, then click Refresh holdings. Theme demo pages are separate."
        />
      ) : (
        <p className="text-sm text-[var(--text-muted)]">Loading holdings…</p>
      )}
    </div>
  );
}
