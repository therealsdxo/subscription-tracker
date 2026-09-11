"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, PageHeader, Spinner } from "@/components/ui/misc";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { usePayments, type PaymentMethod } from "@/lib/api/hooks/payments";
import { PAGE_SIZE } from "@/lib/constants";
import { formatDate, formatMoney } from "@/lib/format";

const METHODS: (PaymentMethod | "ALL")[] = ["ALL", "CASH", "UPI", "CARD", "BANK_TRANSFER", "OTHER"];

function PaymentsList() {
  const params = useSearchParams();
  const router = useRouter();

  const method = (params.get("method") as PaymentMethod | "ALL") ?? "ALL";
  const dateFrom = params.get("from") ?? "";
  const dateTo = params.get("to") ?? "";
  const page = Number(params.get("page") ?? "1");

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (value === null || value === "") next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.delete("page");
    router.push(`/payments?${next.toString()}`);
  };

  const query = usePayments({
    method: method === "ALL" ? undefined : method,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  return (
    <>
      <PageHeader title="Payments" description="All payments recorded across subscriptions" />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Select value={method} onChange={(e) => setParam("method", e.target.value === "ALL" ? null : e.target.value)}>
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {m === "ALL" ? "All methods" : m.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Input type="date" value={dateFrom} onChange={(e) => setParam("from", e.target.value)} className="w-40" />
        <span className="text-text-muted text-[13px]">to</span>
        <Input type="date" value={dateTo} onChange={(e) => setParam("to", e.target.value)} className="w-40" />
        {query.isFetching ? <Spinner /> : null}
      </div>

      {query.isError ? (
        <ErrorState message={(query.error as Error).message} />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState message="No payments match." />
      ) : query.data ? (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Subscription</Th>
                <Th>Method</Th>
                <Th>Reference</Th>
                <Th className="text-right">Amount</Th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((p) => (
                <Tr key={p.id}>
                  <Td>{formatDate(p.payment_date)}</Td>
                  <Td>
                    <Link href={`/subscriptions/${p.subscription_id}`} className="text-accent hover:underline">
                      #{p.subscription_id}
                    </Link>
                  </Td>
                  <Td>{p.payment_method.replace(/_/g, " ")}</Td>
                  <Td>{p.reference_number ?? "—"}</Td>
                  <Td className="text-right tabular-nums">{formatMoney(p.amount)}</Td>
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

export default function PaymentsPage() {
  return (
    <Suspense>
      <PaymentsList />
    </Suspense>
  );
}
