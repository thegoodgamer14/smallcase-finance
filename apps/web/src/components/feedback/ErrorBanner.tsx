interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBanner({
  message,
  onRetry,
  className = "",
}: ErrorBannerProps) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--risk-warning)]/40 bg-[var(--risk-warning)]/10 px-4 py-3 text-sm text-[var(--text-primary)] ${className}`}
      role="alert"
    >
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
