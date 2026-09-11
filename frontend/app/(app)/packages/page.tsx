"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PackageFormDialog } from "@/app/(app)/packages/package-form-dialog";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { EmptyState, ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { Pagination } from "@/components/ui/pagination";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import {
  useDeletePackage,
  usePackages,
  useSetPackageStatus,
  type PackageStatus,
} from "@/lib/api/hooks/packages";
import { PAGE_SIZE } from "@/lib/constants";
import { formatMoney } from "@/lib/format";

export default function PackagesPage() {
  const toast = useToast();
  const [status, setStatus] = useState<PackageStatus | "ALL">("ALL");
  const [page, setPage] = useState(1);

  const query = usePackages({
    status: status === "ALL" ? undefined : status,
    page,
    page_size: PAGE_SIZE,
  });
  const setActive = useSetPackageStatus();
  const remove = useDeletePackage();

  const toggle = async (id: number, activate: boolean) => {
    try {
      await setActive.mutateAsync({ id, activate });
      toast({ title: activate ? "Package activated" : "Package deactivated", variant: "success" });
    } catch (e) {
      toast({ title: "Action failed", description: (e as Error).message, variant: "error" });
    }
  };

  const del = async (id: number, code: string) => {
    if (!window.confirm(`Delete ${code}? This only works if it has never been used.`)) return;
    try {
      await remove.mutateAsync(id);
      toast({ title: "Package deleted", variant: "success" });
    } catch (e) {
      toast({ title: "Delete failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <>
      <PageHeader
        title="Packages"
        description="Meal packages available for new subscriptions"
        actions={
          <PackageFormDialog
            trigger={
              <Button size="sm">
                <Plus className="h-3.5 w-3.5" /> New package
              </Button>
            }
          />
        }
      />

      <div className="mb-3 flex items-center gap-2">
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as PackageStatus | "ALL");
            setPage(1);
          }}
        >
          <option value="ALL">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </Select>
        {query.isFetching ? <Spinner /> : null}
      </div>

      {query.isError ? (
        <ErrorState message={(query.error as Error).message} />
      ) : query.data && query.data.items.length === 0 ? (
        <EmptyState message="No packages yet." />
      ) : query.data ? (
        <>
          <Table>
            <thead>
              <tr>
                <Th className="w-28">Code</Th>
                <Th>Name</Th>
                <Th className="w-24 text-right">Meals</Th>
                <Th className="w-28 text-right">Validity</Th>
                <Th className="w-28 text-right">Price</Th>
                <Th className="w-24">Status</Th>
                <Th className="w-56" />
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((p) => (
                <Tr key={p.id}>
                  <Td className="font-mono text-[13px] text-text-muted">{p.package_code}</Td>
                  <Td className="font-medium">{p.name}</Td>
                  <Td className="text-right tabular-nums">{p.number_of_meals}</Td>
                  <Td className="text-right tabular-nums">{p.validity_days}d</Td>
                  <Td className="text-right tabular-nums">{formatMoney(p.final_price)}</Td>
                  <Td>
                    <StatusPill value={p.status} />
                  </Td>
                  <Td>
                    <div className="flex justify-end gap-1.5">
                      <PackageFormDialog
                        editing={p}
                        trigger={
                          <Button variant="secondary" size="sm">
                            Edit
                          </Button>
                        }
                      />
                      {p.status === "ACTIVE" ? (
                        <Button variant="secondary" size="sm" onClick={() => toggle(p.id, false)}>
                          Deactivate
                        </Button>
                      ) : (
                        <Button variant="secondary" size="sm" onClick={() => toggle(p.id, true)}>
                          Activate
                        </Button>
                      )}
                      <Button variant="danger" size="sm" onClick={() => del(p.id, p.package_code)}>
                        Delete
                      </Button>
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
            onPageChange={setPage}
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
