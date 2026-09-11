"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useExtendSubscription } from "@/lib/api/hooks/subscriptions";

export function ExtendDialog({ trigger, subscriptionId }: { trigger: React.ReactNode; subscriptionId: number }) {
  const [open, setOpen] = React.useState(false);
  const [mode, setMode] = React.useState<"days" | "date">("days");
  const [days, setDays] = React.useState(7);
  const [newEndDate, setNewEndDate] = React.useState("");
  const [reason, setReason] = React.useState("");
  const toast = useToast();
  const extend = useExtendSubscription(subscriptionId);

  const submit = async () => {
    if (!reason.trim()) return;
    try {
      await extend.mutateAsync(
        mode === "days"
          ? { days, reason: reason.trim() }
          : { new_end_date: newEndDate, reason: reason.trim() },
      );
      toast({ title: "Subscription extended", variant: "success" });
      setOpen(false);
      setReason("");
    } catch (e) {
      toast({ title: "Extend failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title="Extend subscription" description="Pushes the expiry date out.">
        <div className="mb-3 flex gap-1.5">
          <Button variant={mode === "days" ? "primary" : "secondary"} size="sm" onClick={() => setMode("days")}>
            By days
          </Button>
          <Button variant={mode === "date" ? "primary" : "secondary"} size="sm" onClick={() => setMode("date")}>
            To a date
          </Button>
        </div>
        {mode === "days" ? (
          <Field label="Days to add" htmlFor="days">
            <Input id="days" type="number" min={1} value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </Field>
        ) : (
          <Field label="New expiry date" htmlFor="new_end_date">
            <Input
              id="new_end_date"
              type="date"
              value={newEndDate}
              onChange={(e) => setNewEndDate(e.target.value)}
            />
          </Field>
        )}
        <Field label="Reason" htmlFor="reason" className="mt-3">
          <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!reason.trim() || (mode === "date" && !newEndDate)} onClick={submit}>
            Extend
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
