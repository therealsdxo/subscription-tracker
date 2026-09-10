"use client";

import { PageHeader, ErrorState, Spinner } from "@/components/ui/misc";
import { useDashboardSummary } from "@/lib/api/hooks/dashboard";

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border-border bg-surface rounded-[var(--radius)] border p-4">
      <div className="text-text-muted text-[12px] font-medium tracking-wide uppercase">
        {label}
      </div>
      <div className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums">
        {value}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useDashboardSummary();

  return (
    <>
      <PageHeader title="Dashboard" description="Today at a glance" />

      {isLoading ? (
        <div className="text-text-muted flex items-center gap-2 text-sm">
          <Spinner /> Loading…
        </div>
      ) : isError ? (
        <ErrorState message={(error as Error).message} />
      ) : data ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Tile label="Active subscriptions" value={data.active_subscriptions} />
          <Tile label="Today's meals" value={data.todays_meals_planned} />
          <Tile label="Delivered today" value={data.delivered_today} />
          <Tile label="Expiring soon" value={data.expiring_soon} />
          <Tile label="Outstanding dues" value={`₹${data.outstanding_dues_total}`} />
        </div>
      ) : null}
    </>
  );
}
