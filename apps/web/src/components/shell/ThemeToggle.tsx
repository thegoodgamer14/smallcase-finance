"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { useApp } from "@/lib/context";

/**
 * Theme icon can differ after mount when localStorage overrides default dark.
 * Suppress hydration mismatch on the control; server always renders dark icon.
 * Note: browser extensions injecting attributes (bis_register, etc.) can also
 * trigger Next hydration warnings — those are not app bugs.
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useApp();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = !mounted || theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
      suppressHydrationWarning
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
