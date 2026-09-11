"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useIssueRefund, useRecordPayment } from "@/lib/api/hooks/subscriptions";

const METHODS = ["CASH", "UPI", "CARD", "BANK_TRANSFER", "OTHER"] as const;

export function RecordPaymentDialog({
  trigger,
  subscriptionId,
}: {
  trigger: React.ReactNode;
  subscriptionId: number;
}) {
  const [open, setOpen] = React.useState(false);
  const [amount, setAmount] = React.useState("");
  const [method, setMethod] = React.useState<(typeof METHODS)[number]>("UPI");
  const [reference, setReference] = React.useState("");
  const toast = useToast();
  const record = useRecordPayment(subscriptionId);

  const submit = async () => {
    if (!amount) return;
    try {
      await record.mutateAsync({
        amount,
        payment_method: method,
        reference_number: reference || undefined,
      });
      toast({ title: "Payment recorded", variant: "success" });
      setOpen(false);
      setAmount("");
      setReference("");
    } catch (e) {
      toast({ title: "Failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title="Record payment">
        <Field label="Amount (₹)" htmlFor="amount">
          <Input
            id="amount"
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label="Method" htmlFor="method" className="mt-3">
          <Select id="method" className="w-full" value={method} onChange={(e) => setMethod(e.target.value as never)}>
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reference (optional)" htmlFor="ref" className="mt-3">
          <Input id="ref" value={reference} onChange={(e) => setReference(e.target.value)} />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!amount} onClick={submit}>
            Record
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function IssueRefundDialog({
  trigger,
  subscriptionId,
  suggested,
}: {
  trigger: React.ReactNode;
  subscriptionId: number;
  suggested?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [amount, setAmount] = React.useState("");
  const [method, setMethod] = React.useState<(typeof METHODS)[number]>("UPI");
  const [reason, setReason] = React.useState("");
  const toast = useToast();
  const refund = useIssueRefund(subscriptionId);

  const submit = async () => {
    if (!amount || !reason.trim()) return;
    try {
      await refund.mutateAsync({ amount, payment_method: method, reason: reason.trim() });
      toast({ title: "Refund recorded", variant: "success" });
      setOpen(false);
      setAmount("");
      setReason("");
    } catch (e) {
      toast({ title: "Failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        title="Issue refund"
        description={suggested ? `Suggested prorated amount: ₹${suggested} (guidance only).` : undefined}
      >
        <Field label="Amount (₹)" htmlFor="amount">
          <Input
            id="amount"
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label="Method" htmlFor="method" className="mt-3">
          <Select id="method" className="w-full" value={method} onChange={(e) => setMethod(e.target.value as never)}>
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reason" htmlFor="reason" className="mt-3">
          <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" size="sm" disabled={!amount || !reason.trim()} onClick={submit}>
            Issue refund
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
