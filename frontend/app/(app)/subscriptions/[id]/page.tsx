"use client";

import { useParams } from "next/navigation";
import * as React from "react";

import { ExtendDialog } from "@/app/(app)/subscriptions/[id]/extend-dialog";
import { MealAdjustmentDialog } from "@/app/(app)/subscriptions/[id]/meal-adjustment-dialog";
import { IssueRefundDialog, RecordPaymentDialog } from "@/app/(app)/subscriptions/[id]/payment-dialogs";
import { SkipDialog } from "@/app/(app)/subscriptions/[id]/skip-dialog";
import { SubscriptionFormDialog } from "@/app/(app)/subscriptions/subscription-form-dialog";
import { Button } from "@/components/ui/button";
import { ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { ReasonDialog } from "@/components/ui/reason-dialog";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { useCurrentUser } from "@/lib/api/hooks/auth";
import { useCustomer } from "@/lib/api/hooks/customers";
import {
  useCancelSubscription,
  usePauseSubscription,
  useRemoveSkip,
  useResumeSubscription,
  useSubscription,
  useSubscriptionDeliveries,
  useSubscriptionEvents,
  useSubscriptionPayments,
  useSubscriptionSkips,
} from "@/lib/api/hooks/subscriptions";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="text-text text-right font-medium">{children}</span>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-border bg-surface rounded-[var(--radius)] border p-4">
      <h2 className="text-text mb-2 text-sm font-semibold">{title}</h2>
      {children}
    </div>
  );
}

export default function SubscriptionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const toast = useToast();

  const { data: me } = useCurrentUser();
  const isAdmin = me?.role === "ADMIN";

  const sub = useSubscription(id);
  const events = useSubscriptionEvents(id);
  const deliveries = useSubscriptionDeliveries(id);
  const skips = useSubscriptionSkips(id);
  const payments = useSubscriptionPayments(id);
  const customer = useCustomer(sub.data?.customer_id);

  const pause = usePauseSubscription(id);
  const resume = useResumeSubscription(id);
  const cancel = useCancelSubscription(id);
  const removeSkip = useRemoveSkip(id);

  if (sub.isError) return <ErrorState message={(sub.error as Error).message} />;
  if (!sub.data) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading…
      </div>
    );
  }

  const s = sub.data;
  const canPause = s.status === "ACTIVE";
  const canResume = s.status === "PAUSED";
  const canCancel = !["COMPLETED", "CANCELLED", "EXPIRED"].includes(s.status);

  return (
    <>
      <PageHeader
        title={s.subscription_code}
        description={`${s.snapshot_package_name} · ${customer.data?.name ?? `Customer #${s.customer_id}`}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusPill value={s.status} />
            {canPause && isAdmin ? (
              <ReasonDialog
                trigger={
                  <Button variant="secondary" size="sm">
                    Pause
                  </Button>
                }
                title="Pause subscription"
                confirmLabel="Pause"
                onConfirm={async (reason) => {
                  await pause.mutateAsync(reason);
                  toast({ title: "Subscription paused", variant: "success" });
                }}
              />
            ) : null}
            {canResume ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  try {
                    await resume.mutateAsync();
                    toast({ title: "Subscription resumed", variant: "success" });
                  } catch (e) {
                    toast({ title: "Resume failed", description: (e as Error).message, variant: "error" });
                  }
                }}
              >
                Resume
              </Button>
            ) : null}
            {isAdmin ? <ExtendDialog trigger={<Button variant="secondary" size="sm">Extend</Button>} subscriptionId={id} /> : null}
            {isAdmin ? (
              <MealAdjustmentDialog
                trigger={
                  <Button variant="secondary" size="sm">
                    Adjust meals
                  </Button>
                }
                subscriptionId={id}
              />
            ) : null}
            <SubscriptionFormDialog
              trigger={
                <Button variant="secondary" size="sm">
                  Renew
                </Button>
              }
              customerId={s.customer_id}
              customerLabel={customer.data?.name}
              renewFrom={id}
            />
            {canCancel && isAdmin ? (
              <ReasonDialog
                trigger={
                  <Button variant="danger" size="sm">
                    Cancel
                  </Button>
                }
                title="Cancel subscription"
                confirmLabel="Cancel subscription"
                danger
                onConfirm={async (reason) => {
                  await cancel.mutateAsync(reason);
                  toast({ title: "Subscription cancelled", variant: "success" });
                }}
              />
            ) : null}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Snapshot & balance">
          <Row label="Package">{s.snapshot_package_name}</Row>
          <Row label="Start date">{formatDate(s.start_date)}</Row>
          <Row label="Expected end">{formatDate(s.expected_end_date)}</Row>
          <Row label="Original end">{formatDate(s.original_end_date)}</Row>
          <Row label="Actual end">{formatDate(s.actual_end_date)}</Row>
          <Row label="Meals allocated">{s.meals_allocated}</Row>
          <Row label="Meals consumed">{s.meals_consumed}</Row>
          <Row label="Adjustment">{s.meals_adjustment}</Row>
          <Row label="Meals remaining">{s.meals_remaining}</Row>
          <Row label="Price">{formatMoney(s.snapshot_final_price)}</Row>
        </Card>

        <Card title="Delivery settings">
          <Row label="Frequency">{s.delivery_frequency}</Row>
          <Row label="Weekdays">{s.delivery_weekdays?.join(", ") ?? "—"}</Row>
          <Row label="Meals per delivery">{s.meals_per_delivery}</Row>
          <Row label="Time slot">{s.delivery_time_slot}</Row>
          <Row label="Time slot note">{s.delivery_time_slot_note ?? "—"}</Row>
          <Row label="Dietary preference">{s.snapshot_dietary_preference ?? "—"}</Row>
          <Row label="Notes">{s.subscription_notes ?? "—"}</Row>
        </Card>

        <Card title="Payments">
          {payments.data ? (
            <>
              <Row label="Status">
                <StatusPill value={payments.data.summary.payment_status} />
              </Row>
              <Row label="Total paid">{formatMoney(payments.data.summary.total_paid)}</Row>
              <Row label="Total refunded">{formatMoney(payments.data.summary.total_refunded)}</Row>
              <Row label="Net paid">{formatMoney(payments.data.summary.net_paid)}</Row>
              <Row label="Outstanding">{formatMoney(payments.data.summary.outstanding_amount)}</Row>
              <div className="mt-3 flex gap-2">
                <RecordPaymentDialog
                  trigger={
                    <Button size="sm" variant="secondary">
                      Record payment
                    </Button>
                  }
                  subscriptionId={id}
                />
                {isAdmin ? (
                  <IssueRefundDialog
                    trigger={
                      <Button size="sm" variant="danger">
                        Issue refund
                      </Button>
                    }
                    subscriptionId={id}
                    suggested={payments.data.summary.suggested_refund}
                  />
                ) : null}
              </div>
              {payments.data.payments.length > 0 || payments.data.refunds.length > 0 ? (
                <div className="mt-3 space-y-1 text-[13px]">
                  {payments.data.payments.map((p) => (
                    <div key={`p-${p.id}`} className="flex justify-between text-text-muted">
                      <span>
                        {formatDate(p.payment_date)} · {p.payment_method}
                      </span>
                      <span className="text-text">{formatMoney(p.amount)}</span>
                    </div>
                  ))}
                  {payments.data.refunds.map((r) => (
                    <div key={`r-${r.id}`} className="flex justify-between text-text-muted">
                      <span>
                        {formatDate(r.refund_date)} · refund · {r.reason}
                      </span>
                      <span className="text-danger">-{formatMoney(r.amount)}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          ) : (
            <Spinner />
          )}
        </Card>

        <Card title="Planned skips">
          <div className="mb-2">
            <SkipDialog
              trigger={
                <Button size="sm" variant="secondary">
                  Add skip
                </Button>
              }
              subscriptionId={id}
            />
          </div>
          {skips.data && skips.data.length > 0 ? (
            <div className="space-y-1 text-[13px]">
              {skips.data.map((sk) => (
                <div key={sk.id} className="flex items-center justify-between text-text-muted">
                  <span>
                    {formatDate(sk.skip_date_from)} → {formatDate(sk.skip_date_to)}
                    {sk.reason ? ` · ${sk.reason}` : ""}
                  </span>
                  <button
                    className="text-danger hover:underline"
                    onClick={async () => {
                      try {
                        await removeSkip.mutateAsync(sk.id);
                        toast({ title: "Skip removed", variant: "success" });
                      } catch (e) {
                        toast({ title: "Failed", description: (e as Error).message, variant: "error" });
                      }
                    }}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-muted text-[13px]">No planned skips.</p>
          )}
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Recent deliveries">
          {deliveries.data && deliveries.data.length > 0 ? (
            <Table>
              <thead>
                <tr>
                  <Th>Date</Th>
                  <Th>Slot</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Qty</Th>
                </tr>
              </thead>
              <tbody>
                {deliveries.data.slice(0, 10).map((d) => (
                  <Tr key={d.id}>
                    <Td>{formatDate(d.delivery_date)}</Td>
                    <Td>{d.time_slot}</Td>
                    <Td>
                      <StatusPill value={d.status} />
                    </Td>
                    <Td className="text-right tabular-nums">{d.meal_quantity}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <p className="text-text-muted text-[13px]">No deliveries yet.</p>
          )}
        </Card>

        <Card title="Event history">
          {events.data && events.data.length > 0 ? (
            <div className="space-y-1.5 text-[13px]">
              {events.data.map((e) => (
                <div key={e.id} className="flex items-center justify-between text-text-muted">
                  <span>
                    <span className="text-text font-medium">{e.event_type}</span>
                    {e.reason ? ` · ${e.reason}` : ""}
                  </span>
                  <span>{formatDateTime(e.performed_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-muted text-[13px]">No events yet.</p>
          )}
        </Card>
      </div>
    </>
  );
}
