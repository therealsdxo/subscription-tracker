"use client";

import { Plus } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { SubscriptionFormDialog } from "@/app/(app)/subscriptions/subscription-form-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useCustomersByIds } from "@/lib/api/hooks/customers";
import { useSubscriptions, type SubscriptionStatus } from "@/lib/api/hooks/subscriptions";
import { PAGE_SIZE } from "@/lib/constants";
import { formatDate } from "@/lib/format";

const STATUSES: (SubscriptionStatus | "ALL")[] = [
  "ALL",
  "PENDING",
  "ACTIVE",
  "PAUSED",
  "COMPLETED",
  "EXPIRED",
  "CANCELLED",
];

function SubscriptionsList() {
  const router = useRouter();
  const params = useSearchParams();
  const status = (params.get("status") as SubscriptionStatus | "ALL") ?? "ALL";
  const quick = params.get("quick"); // "expiring" | "dues"
  const page = Number(params.get("page") ?? "1");

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (value === null) next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.delete("page");
    router.push(`/subscriptions?${next.toString()}`);
  };

  const query = useSubscriptions({
    status: status === "ALL" ? undefined : status,
    expiring: quick === "expiring" ? true : undefined,
    dues: quick === "dues" ? true : undefined,
    page,
    page_size: PAGE_SIZE,
  });
  const customers = useCustomersByIds(query.data?.items.map((s) => s.customer_id) ?? []);

  return (
    <>
      <PageHeader
        title="Subscriptions"
        description="Every customer subscription, past and present"
        actions={
          <SubscriptionFormDialog
            trigger={
              <Button size="sm">
                <Plus className="h-3.5 w-3.5" /> New subscription
              </Button>
            }
          />
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Select value={status} onChange={(e) => setParam("status", e.target.value === "ALL" ? null : e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : s}
            </option>
          ))}
        </Select>
        <Button
          variant={quick === "expiring" ? "primary" : "secondary"}
          size="sm"
          onClick={() => setParam("quick", quick === "expiring" ? null : "expiring")}
        >
          Expiring soon
        </Button>
        <Button
          variant={quick === "dues" ? "primary" : "secondary"}
          size="sm"
          onClick={() => setParam("quick", quick === "dues" ? null : "dues")}
        >
          Dues
        </Button>
        {query.isFetching ? <Spinner /> : null}
      </div>

      {query.isError ? (
        <ErrorState message={(query.error as Error).message} />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState message="No subscriptions match." />
      ) : query.data ? (
        <>
          <Table>
            <thead>
              <tr>
                <Th className="w-32">Code</Th>
                <Th>Customer</Th>
                <Th>Package</Th>
                <Th className="w-24">Status</Th>
                <Th className="w-28 text-right">Meals left</Th>
                <Th className="w-28">Ends</Th>
                <Th className="w-28">Payment</Th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((s) => (
                <Tr key={s.id} onClick={() => router.push(`/subscriptions/${s.id}`)}>
                  <Td className="font-mono text-[13px] text-text-muted">{s.subscription_code}</Td>
                  <Td>{customers.get(s.customer_id)?.name ?? `#${s.customer_id}`}</Td>
                  <Td>{s.snapshot_package_name}</Td>
                  <Td>
                    <StatusPill value={s.status} />
                  </Td>
                  <Td className="text-right tabular-nums">
                    {s.meals_remaining}/{s.meals_allocated}
                  </Td>
                  <Td>{formatDate(s.expected_end_date)}</Td>
                  <Td>
                    <StatusPill value={s.payment_status} />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            onPageChange={(p) => setParam("page", String(p))}
          />
        </>
      ) : (
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Spinner /> Loading…
        </div>
      )}
    </>
  );
}

export default function SubscriptionsPage() {
  return (
    <Suspense>
      <SubscriptionsList />
    </Suspense>
  );
}
