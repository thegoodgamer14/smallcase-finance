import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { AppProvider } from "@/lib/context";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Backtest Hero",
  description:
    "Personal portfolio view (Kite) + Decision Lab SIP backtests — local-first.",
};

function ShellFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)] text-sm text-[var(--text-secondary)]">
      Loading…
    </div>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <Suspense fallback={<ShellFallback />}>
          <AppProvider>
            <AppShell>{children}</AppShell>
          </AppProvider>
        </Suspense>
      </body>
    </html>
  );
}
