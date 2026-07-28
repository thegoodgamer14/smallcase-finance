export type Theme = "dark" | "light";

export const THEME_KEY = "sf-theme";
export const SMALLCASE_KEY = "sf-smallcase";

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const v = localStorage.getItem(THEME_KEY);
  return v === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", theme);
}

export function setStoredTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
}

export function getStoredSmallcase(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SMALLCASE_KEY);
}

export function setStoredSmallcase(id: string): void {
  localStorage.setItem(SMALLCASE_KEY, id);
}
