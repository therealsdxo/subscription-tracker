"use client";

import { RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { Pagination } from "@/components/ui/pagination";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { Select } from "@/components/ui/select";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import {
  useDeliveries,
  useGenerateDeliveries,
  useReverseDelivery,
  useUpdateDelivery,
  type DeliveryStatus,
} from "@/lib/api/hooks/deliveries";
import { PAGE_SIZE } from "@/lib/constants";
import { todayISO } from "@/lib/format";

const STATUSES: (DeliveryStatus | "ALL")[] = [
  "ALL",
  "SCHEDULED",
  "PREPARING",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "SKIPPED",
  "CANCELLED",
  "FAILED",
  "RESCHEDULED",
];

const SLOTS = ["ALL", "MORNING", "LUNCH", "EVENING", "CUSTOM"] as const;

function DeliveriesList() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();

  const date = params.get("date") ?? todayISO();
  const status = (params.get("status") as DeliveryStatus | "ALL") ?? "ALL";
  const timeSlot = (params.get("slot") as (typeof SLOTS)[number]) ?? "ALL";
  const page = Number(params.get("page") ?? "1");
  const [area, setArea] = useState(params.get("area") ?? "");

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (value === null || value === "") next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.delete("page");
    router.push(`/deliveries?${next.toString()}`);
  };

  const query = useDeliveries({
    date,
    status: status === "ALL" ? undefined : status,
    area: area || undefined,
    time_slot: timeSlot === "ALL" ? undefined : timeSlot,
    page,
    page_size: PAGE_SIZE,
  });
  const generate = useGenerateDeliveries();
  const update = useUpdateDelivery();
  const reverse = useReverseDelivery();

  return (
    <>
      <PageHeader
        title="Deliveries"
        description="Daily delivery schedule and fulfillment"
        actions={
          <Button
            size="sm"
            onClick={async () => {
              try {
                const res = await generate.mutateAsync(date);
                toast({
                  title: "Deliveries generated",
                  description: res.open_day
                    ? `${res.created} created`
                    : `${res.created} created — not a service day`,
                  variant: "success",
                });
              } catch (e) {
                toast({ title: "Generate failed", description: (e as Error).message, variant: "error" });
              }
            }}
          >
            <RefreshCw className="h-3.5 w-3.5" /> Generate for date
          </Button>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input type="date" value={date} onChange={(e) => setParam("date", e.target.value)} className="w-40" />
        <Select value={status} onChange={(e) => setParam("status", e.target.value === "ALL" ? null : e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Select value={timeSlot} onChange={(e) => setParam("slot", e.target.value === "ALL" ? null : e.target.value)}>
          {SLOTS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All slots" : s}
            </option>
          ))}
        </Select>
        <Input
          placeholder="Filter by area…"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          onBlur={() => setParam("area", area)}
          onKeyDown={(e) => e.key === "Enter" && setParam("area", area)}
          className="w-48"
        />
        {query.isFetching ? <Spinner /> : null}
      </div>

      {query.isError ? (
        <ErrorState message={(query.error as Error).message} />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState message="No deliveries for this date/filter. Try generating them." />
      ) : query.data ? (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Subscription</Th>
                <Th>Customer</Th>
                <Th>Slot</Th>
                <Th>Status</Th>
                <Th className="text-right">Qty</Th>
                <Th className="w-64">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((d) => (
                <Tr key={d.id}>
                  <Td>
                    <Link href={`/subscriptions/${d.subscription_id}`} className="font-mono text-[13px] text-accent hover:underline">
                      {d.subscription_code}
                    </Link>
                  </Td>
                  <Td>{d.customer_name}</Td>
                  <Td>{d.time_slot}</Td>
                  <Td>
                    <StatusPill value={d.status} />
                  </Td>
                  <Td className="text-right tabular-nums">{d.meal_quantity}</Td>
                  <Td>
                    <div className="flex items-center gap-1.5">
                      <Select
                        value={d.status}
                        disabled={update.isPending}
                        onChange={async (e) => {
                          try {
                            await update.mutateAsync({ id: d.id, body: { status: e.target.value as DeliveryStatus } });
                            toast({ title: "Delivery updated", variant: "success" });
                          } catch (err) {
                            toast({ title: "Update failed", description: (err as Error).message, variant: "error" });
                          }
                        }}
                      >
                        {STATUSES.filter((s) => s !== "ALL").map((s) => (
                          <option key={s} value={s}>
                            {s.replace(/_/g, " ")}
                          </option>
                        ))}
                      </Select>
                      {!d.reversed && d.status === "DELIVERED" ? (
                        <ReasonDialog
                          trigger={
                            <Button variant="danger" size="sm">
                              Reverse
                            </Button>
                          }
                          title="Reverse delivery"
                          description="Restores the meal(s) deducted for this delivery."
                          confirmLabel="Reverse"
                          danger
                          onConfirm={async (reason) => {
                            await reverse.mutateAsync({ id: d.id, reason });
                            toast({ title: "Delivery reversed", variant: "success" });
                          }}
                        />
                      ) : null}
                    </div>
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

export default function DeliveriesPage() {
  return (
    <Suspense>
      <DeliveriesList />
    </Suspense>
  );
}
