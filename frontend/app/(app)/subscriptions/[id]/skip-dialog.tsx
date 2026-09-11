"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAddSkip } from "@/lib/api/hooks/subscriptions";
import { todayISO } from "@/lib/format";

export function SkipDialog({ trigger, subscriptionId }: { trigger: React.ReactNode; subscriptionId: number }) {
  const [open, setOpen] = React.useState(false);
  const [from, setFrom] = React.useState(todayISO());
  const [to, setTo] = React.useState(todayISO());
  const [reason, setReason] = React.useState("");
  const toast = useToast();
  const add = useAddSkip(subscriptionId);

  const submit = async () => {
    try {
      await add.mutateAsync({ skip_date_from: from, skip_date_to: to, reason: reason || undefined });
      toast({ title: "Planned skip added", variant: "success" });
      setOpen(false);
    } catch (e) {
      toast({ title: "Failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title="Add a planned skip" description="No delivery will be generated for these dates.">
        <div className="grid grid-cols-2 gap-3">
          <Field label="From" htmlFor="from">
            <Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </Field>
          <Field label="To" htmlFor="to">
            <Input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </Field>
        </div>
        <Field label="Reason (optional)" htmlFor="reason" className="mt-3">
          <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={to < from} onClick={submit}>
            Add
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
