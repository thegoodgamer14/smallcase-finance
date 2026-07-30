"use client";

import {
  Activity,
  FlaskConical,
  LayoutDashboard,
  PieChart,
  Scale,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { CustomRangePicker } from "@/components/filters/CustomRangePicker";
import { RangeChips } from "@/components/filters/RangeChips";
import { DataSourceBanner } from "@/components/shell/DataSourceBanner";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import {
  SmallcaseSelect,
  toOptions,
} from "@/components/smallcase/SmallcaseSelect";
import { useApp } from "@/lib/context";
import { formatDate } from "@/lib/format";

const NAV = [
  { href: "/portfolio", label: "Portfolio", icon: Wallet },
  { href: "/decide", label: "Decision Lab", icon: Scale },
  { href: "/sip-lab", label: "SIP Lab", icon: FlaskConical },
  { href: "/", label: "Theme demo", icon: LayoutDashboard },
  { href: "/holdings", label: "Theme holdings", icon: PieChart },
  { href: "/performance", label: "Theme perf", icon: Activity },
] as const;

function navActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const {
    smallcases,
    smallcasesLoading,
    smallcaseId,
    setSmallcaseId,
    activeSmallcase,
    window,
    setWindow,
    customRange,
    setCustomRange,
  } = useApp();

  const asOf = activeSmallcase?.as_of;
  const isSipLab = pathname.startsWith("/sip-lab");
  const isPortfolioDecision =
    pathname.startsWith("/portfolio") ||
    pathname.startsWith("/decide") ||
    isSipLab;
  const showThemeControls = !isPortfolioDecision;

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg-app)] text-[var(--text-primary)]">
      <DataSourceBanner />
      {/* Top bar */}
      <header className="sticky top-0 z-40 flex h-topbar items-center gap-4 border-b border-[var(--border-default)] bg-[var(--bg-app)]/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-[var(--bg-app)]/80">
        <Link
          href="/portfolio"
          className="shrink-0 text-sm font-semibold tracking-tight text-[var(--text-primary)]"
        >
          Backtest Hero
        </Link>

        <div className="hidden flex-1 md:block" />

        {showThemeControls ? (
          <SmallcaseSelect
            items={toOptions(smallcases)}
            value={smallcaseId}
            onChange={setSmallcaseId}
            loading={smallcasesLoading}
          />
        ) : null}

        {asOf && showThemeControls ? (
          <span className="hidden text-xs text-[var(--text-muted)] sm:inline">
            As-of {formatDate(asOf)}
          </span>
        ) : null}

        <ThemeToggle />
      </header>

      <div className="flex flex-1">
        {/* Left nav */}
        <aside className="sticky top-topbar hidden h-[calc(100vh-var(--topbar-height))] w-nav shrink-0 flex-col border-r border-[var(--border-default)] bg-[var(--bg-app)] p-3 md:flex">
          <nav className="flex flex-col gap-1" aria-label="Primary">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = navActive(pathname, href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${
                    active
                      ? "bg-[var(--accent-subtle)] text-[var(--accent)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {showThemeControls ? (
            <div className="mt-auto space-y-3 border-t border-[var(--border-subtle)] pt-4">
              <p className="px-1 text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                Range
              </p>
              <RangeChips
                value={customRange ? null : window}
                onChange={setWindow}
                className="px-0.5"
              />
              <p className="px-1 text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                Custom timeline
              </p>
              <CustomRangePicker
                value={customRange}
                onChange={setCustomRange}
                className="px-0.5"
              />
              {customRange ? (
                <p className="px-1 text-[11px] text-[var(--accent)]">
                  Evaluating {customRange.start} → {customRange.end}
                </p>
              ) : null}
              {activeSmallcase ? (
                <p className="px-1 text-[11px] text-[var(--text-muted)]">
                  {activeSmallcase.name}
                  {activeSmallcase.theme ? ` · ${activeSmallcase.theme}` : ""}
                </p>
              ) : null}
              <p className="px-1 text-[11px] text-[var(--text-muted)]">
                Theme demo only — not your Kite book.
              </p>
            </div>
          ) : (
            <div className="mt-auto border-t border-[var(--border-subtle)] pt-4">
              <p className="px-1 text-[11px] text-[var(--text-muted)]">
                {pathname.startsWith("/portfolio")
                  ? "Refresh holdings when your Kite token is valid."
                  : "SIP / decision window is set in the form."}
              </p>
            </div>
          )}
        </aside>

        {/* Main */}
        <main className="min-w-0 flex-1">{children}</main>
      </div>

      {/* Mobile bottom nav */}
      <nav
        className="sticky bottom-0 z-40 flex border-t border-[var(--border-default)] bg-[var(--bg-surface)] md:hidden"
        aria-label="Mobile"
      >
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = navActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] ${
                active
                  ? "text-[var(--accent)]"
                  : "text-[var(--text-secondary)]"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
