"use client";

import { useEffect, useState } from "react";

import { getUpstoxStatus, type UpstoxStatusResponse } from "@/lib/api";

/**
 * Shows whether live Upstox credentials are configured vs sample prices.
 * Never displays secrets.
 */
export function DataSourceBanner() {
  const [status, setStatus] = useState<UpstoxStatusResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getUpstoxStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error || !status) {
    return null;
  }

  const live = status.configured;

  return (
    <div
      className={`border-b px-4 py-1.5 text-xs ${
        live
          ? "border-[var(--border-default)] bg-[var(--accent-subtle)]/40 text-[var(--text-secondary)]"
          : "border-[var(--border-default)] bg-[var(--bg-elevated)] text-[var(--text-muted)]"
      }`}
      role="status"
    >
      <span className="font-medium text-[var(--text-secondary)]">
        Price source:{" "}
      </span>
      {live ? (
        <>
          Upstox token configured (live sync via CLI). Default lookback{" "}
          {status.default_years}y — use{" "}
          <code className="rounded bg-[var(--bg-app)] px-1">make sync-upstox</code>{" "}
          or custom <code className="rounded bg-[var(--bg-app)] px-1">FROM=… TO=…</code>.
        </>
      ) : (
        <>
          Sample / synthetic prices (demo). Set{" "}
          <code className="rounded bg-[var(--bg-app)] px-1">UPSTOX_ACCESS_TOKEN</code>{" "}
          in <code className="rounded bg-[var(--bg-app)] px-1">.env</code> then{" "}
          <code className="rounded bg-[var(--bg-app)] px-1">make sync-upstox YEARS=3</code>.
          See docs/integrations/upstox.md.
        </>
      )}
    </div>
  );
}
