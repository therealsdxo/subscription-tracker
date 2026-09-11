"use client";

import { Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { AddressDialog } from "@/app/(app)/customers/[id]/address-dialog";
import { CustomerEditDialog } from "@/app/(app)/customers/[id]/customer-edit-dialog";
import { SubscriptionFormDialog } from "@/app/(app)/subscriptions/subscription-form-dialog";
import { Button } from "@/components/ui/button";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { EmptyState, ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { useCustomer, useRemoveAddress, useSetCustomerActive } from "@/lib/api/hooks/customers";
import { useSubscriptions } from "@/lib/api/hooks/subscriptions";
import { formatDate } from "@/lib/format";

export default function CustomerDetailPage() {
  const id = Number(useParams<{ id: string }>().id);
  const router = useRouter();
  const toast = useToast();
  const customer = useCustomer(id);
  const subs = useSubscriptions({ customer_id: id, page: 1, page_size: 50 });
  const setActive = useSetCustomerActive();
  const removeAddress = useRemoveAddress();

  if (customer.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading…
      </div>
    );
  }
  if (customer.isError || !customer.data) {
    return <ErrorState message={(customer.error as Error)?.message ?? "Not found"} />;
  }
  const c = customer.data;

  return (
    <>
      <PageHeader
        title={c.name}
        description={c.customer_code}
        actions={
          <>
            <CustomerEditDialog
              customer={c}
              trigger={<Button variant="secondary" size="sm">Edit</Button>}
            />
            {c.is_active ? (
              <ReasonDialog
                trigger={
                  <Button variant="danger" size="sm">
                    Deactivate
                  </Button>
                }
                title="Deactivate customer"
                description="Hides them from active operations; history is kept."
                confirmLabel="Deactivate"
                danger
                onConfirm={async (reason) => {
                  await setActive.mutateAsync({ id, activate: false, reason });
                  toast({ title: "Customer deactivated", variant: "success" });
                }}
              />
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  await setActive.mutateAsync({ id, activate: true });
                  toast({ title: "Customer reactivated", variant: "success" });
                }}
              >
                Reactivate
              </Button>
            )}
          </>
        }
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <section className="rounded-[var(--radius)] border border-border bg-surface p-4 lg:col-span-1">
          <h2 className="mb-3 text-[13px] font-semibold uppercase tracking-wide text-text-muted">
            Contact
          </h2>
          <dl className="space-y-2 text-sm">
            <Row label="Status"><StatusPill value={c.is_active ? "ACTIVE" : "INACTIVE"} /></Row>
            <Row label="Phone">{c.phone}</Row>
            <Row label="Email">{c.email ?? "—"}</Row>
            <Row label="Dietary">{c.default_dietary_preference?.replace(/_/g, " ") ?? "—"}</Row>
            <Row label="Allergies">{c.allergies ?? "—"}</Row>
            <Row label="Notes">{c.notes ?? "—"}</Row>
          </dl>

          {c.subscriptions ? (
            <div className="mt-4 border-t border-border pt-3 text-sm">
              <div className="text-text-muted mb-1 text-[13px] font-semibold uppercase tracking-wide">
                Subscriptions
              </div>
              {c.subscriptions.current ? (
                <div className="flex items-center justify-between">
                  <span>Current</span>
                  <StatusPill value={c.subscriptions.current.status} />
                </div>
              ) : (
                <p className="text-text-muted">No current subscription.</p>
              )}
              <p className="text-text-muted mt-1">Past: {c.subscriptions.past_count}</p>
            </div>
          ) : null}
        </section>

        <section className="rounded-[var(--radius)] border border-border bg-surface p-4 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold uppercase tracking-wide text-text-muted">
              Addresses
            </h2>
            <AddressDialog
              customerId={id}
              trigger={
                <Button variant="secondary" size="sm">
                  <Plus className="h-3.5 w-3.5" /> Add
                </Button>
              }
            />
          </div>
          <div className="space-y-2">
            {(c.addresses ?? [])
              .filter((a) => a.is_active)
              .map((a) => (
                <div
                  key={a.id}
                  className="flex items-start justify-between rounded-[var(--radius-sm)] border border-border px-3 py-2 text-sm"
                >
                  <div>
                    <div>
                      {a.address_line}, {a.area}, {a.city} — {a.pincode}
                      {a.is_primary ? (
                        <span className="ml-2 text-[11px] font-medium uppercase text-text-muted">
                          primary
                        </span>
                      ) : null}
                    </div>
                    {a.landmark ? (
                      <div className="text-text-muted text-[13px]">Near {a.landmark}</div>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    <AddressDialog
                      customerId={id}
                      editing={a}
                      trigger={
                        <Button variant="secondary" size="sm">
                          Edit
                        </Button>
                      }
                    />
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={async () => {
                        try {
                          await removeAddress.mutateAsync({ customerId: id, addressId: a.id });
                          toast({ title: "Address removed", variant: "success" });
                        } catch (e) {
                          toast({
                            title: "Could not remove",
                            description: (e as Error).message,
                            variant: "error",
                          });
                        }
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            {(c.addresses ?? []).filter((a) => a.is_active).length === 0 ? (
              <EmptyState message="No addresses." />
            ) : null}
          </div>
        </section>
      </div>

      <div className="mt-6 mb-3 flex items-center justify-between">
        <h2 className="text-[13px] font-semibold uppercase tracking-wide text-text-muted">
          Subscription history
        </h2>
        <SubscriptionFormDialog
          customerId={id}
          customerLabel={`${c.name} (${c.customer_code})`}
          trigger={
            <Button size="sm">
              <Plus className="h-3.5 w-3.5" /> New subscription
            </Button>
          }
        />
      </div>
      {subs.data && subs.data.items.length > 0 ? (
        <Table>
          <thead>
            <tr>
              <Th className="w-32">Code</Th>
              <Th>Package</Th>
              <Th className="w-24">Status</Th>
              <Th className="w-28 text-right">Meals left</Th>
              <Th className="w-28">Ends</Th>
              <Th className="w-24">Payment</Th>
            </tr>
          </thead>
          <tbody>
            {subs.data.items.map((s) => (
              <Tr key={s.id} onClick={() => router.push(`/subscriptions/${s.id}`)}>
                <Td className="font-mono text-[13px] text-text-muted">{s.subscription_code}</Td>
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
      ) : (
        <EmptyState message="No subscriptions yet." />
      )}
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-text-muted">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}
