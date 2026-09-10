"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  StatusPill,
} from "@/components/ui/misc";
import { Pagination } from "@/components/ui/pagination";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useCustomers } from "@/lib/api/hooks/customers";
import { PAGE_SIZE } from "@/lib/constants";

type ActiveFilter = "all" | "active" | "inactive";

export default function CustomersPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState<ActiveFilter>("all");
  const [page, setPage] = useState(1);

  const query = useCustomers({
    q: q.trim() || undefined,
    is_active: active === "all" ? undefined : active === "active",
    page,
    page_size: PAGE_SIZE,
  });

  const onSearch = (value: string) => {
    setQ(value);
    setPage(1);
  };

  return (
    <>
      <PageHeader title="Customers" description="Search and open a customer record" />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search by name…"
          value={q}
          onChange={(e) => onSearch(e.target.value)}
          className="max-w-xs"
        />
        <select
          value={active}
          onChange={(e) => {
            setActive(e.target.value as ActiveFilter);
            setPage(1);
          }}
          className="border-border-strong bg-surface h-9 rounded-[var(--radius-sm)] border px-2 text-sm"
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        {query.isFetching ? <Spinner /> : null}
      </div>

      {query.isError ? (
        <ErrorState message={(query.error as Error).message} />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState message="No customers match." />
      ) : query.data ? (
        <>
          <Table>
            <thead>
              <tr>
                <Th className="w-32">Code</Th>
                <Th>Name</Th>
                <Th>Phone</Th>
                <Th className="w-24">Status</Th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((c) => (
                <Tr key={c.id} onClick={() => router.push(`/customers/${c.id}`)}>
                  <Td className="text-text-muted font-mono text-[13px]">
                    {c.customer_code}
                  </Td>
                  <Td className="font-medium">{c.name}</Td>
                  <Td className="tabular-nums">{c.phone}</Td>
                  <Td>
                    <StatusPill value={c.is_active ? "ACTIVE" : "INACTIVE"} />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            onPageChange={setPage}
          />
        </>
      ) : (
        <div className="text-text-muted flex items-center gap-2 text-sm">
          <Spinner /> Loading…
        </div>
      )}
    </>
  );
}
