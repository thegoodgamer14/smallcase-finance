import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-6 py-12 text-center ${className}`}
      role="status"
    >
      <p className="text-base font-medium text-[var(--text-primary)]">{title}</p>
      {description ? (
        <p className="mt-2 max-w-md text-sm text-[var(--text-secondary)]">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
