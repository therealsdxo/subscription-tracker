"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useAdjustMeals } from "@/lib/api/hooks/subscriptions";

export function MealAdjustmentDialog({
  trigger,
  subscriptionId,
}: {
  trigger: React.ReactNode;
  subscriptionId: number;
}) {
  const [open, setOpen] = React.useState(false);
  const [quantity, setQuantity] = React.useState(1);
  const [reason, setReason] = React.useState("");
  const toast = useToast();
  const adjust = useAdjustMeals(subscriptionId);

  const submit = async () => {
    if (!reason.trim() || quantity === 0) return;
    try {
      await adjust.mutateAsync({ quantity, reason: reason.trim() });
      toast({ title: "Meal balance adjusted", variant: "success" });
      setOpen(false);
      setReason("");
    } catch (e) {
      toast({ title: "Adjustment failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        title="Adjust meal balance"
        description="Positive for a goodwill credit, negative to correct a mistake."
      >
        <Field label="Quantity (+/-)" htmlFor="qty">
          <Input id="qty" type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} />
        </Field>
        <Field label="Reason" htmlFor="reason" className="mt-3">
          <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!reason.trim() || quantity === 0} onClick={submit}>
            Apply
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
