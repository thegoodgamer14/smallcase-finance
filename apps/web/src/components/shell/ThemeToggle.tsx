"use client";

import { Moon, Sun } from "lucide-react";

import { useApp } from "@/lib/context";

export function ThemeToggle() {
  const { theme, toggleTheme } = useApp();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
