import { Loader2 } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/cn";

export function Spinner({ className }: { className?: string }) {
  return (
    <Loader2
      className={cn("text-text-muted h-4 w-4 animate-spin", className)}
      aria-hidden
    />
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="border-border mb-5 flex items-start justify-between gap-4 border-b pb-4">
      <div>
        <h1 className="text-text text-lg font-semibold tracking-tight">{title}</h1>
        {description ? (
          <p className="text-text-muted mt-0.5 text-sm">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="border-border-strong bg-surface text-text-muted rounded-[var(--radius)] border border-dashed px-6 py-12 text-center text-sm">
      {message}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="border-border-strong bg-danger-bg text-danger rounded-[var(--radius)] border px-4 py-3 text-sm">
      {message}
    </div>
  );
}

const statusStyles: Record<string, string> = {
  ACTIVE: "text-success",
  PENDING: "text-warning",
  PAUSED: "text-warning",
  COMPLETED: "text-text-muted",
  EXPIRED: "text-danger",
  CANCELLED: "text-danger",
  PAID: "text-success",
  PARTIALLY_PAID: "text-warning",
  UNPAID: "text-text-muted",
  REFUNDED: "text-text-muted",
};

export function StatusPill({ value }: { value: string }) {
  return (
    <span
      className={cn(
        "border-border bg-surface-2 inline-flex items-center rounded-[var(--radius-sm)] border px-1.5 py-0.5 text-[11px] font-medium tracking-wide uppercase",
        statusStyles[value] ?? "text-text-muted",
      )}
    >
      {value.replace(/_/g, " ")}
    </span>
  );
}
