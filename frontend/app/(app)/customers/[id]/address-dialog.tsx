"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAddAddress, useUpdateAddress, type Address } from "@/lib/api/hooks/customers";

export function AddressDialog({
  trigger,
  customerId,
  editing,
}: {
  trigger: React.ReactNode;
  customerId: number;
  editing?: Address;
}) {
  const [open, setOpen] = React.useState(false);
  const toast = useToast();
  const add = useAddAddress();
  const update = useUpdateAddress();
  const [form, setForm] = React.useState({
    address_line: editing?.address_line ?? "",
    area: editing?.area ?? "",
    city: editing?.city ?? "",
    pincode: editing?.pincode ?? "",
    landmark: editing?.landmark ?? "",
    is_primary: editing?.is_primary ?? false,
  });
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    if (!form.address_line || !form.area || !form.city || !form.pincode) return;
    setBusy(true);
    try {
      if (editing) {
        await update.mutateAsync({ customerId, addressId: editing.id, body: form });
      } else {
        await add.mutateAsync({ customerId, body: form });
      }
      toast({ title: editing ? "Address updated" : "Address added", variant: "success" });
      setOpen(false);
    } catch (e) {
      toast({ title: "Save failed", description: (e as Error).message, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title={editing ? "Edit address" : "Add address"}>
        <div className="space-y-3">
          <Field label="Address line" htmlFor="al">
            <Input
              id="al"
              value={form.address_line}
              onChange={(e) => setForm((f) => ({ ...f, address_line: e.target.value }))}
              autoFocus
            />
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Area" htmlFor="area">
              <Input
                id="area"
                value={form.area}
                onChange={(e) => setForm((f) => ({ ...f, area: e.target.value }))}
              />
            </Field>
            <Field label="City" htmlFor="city">
              <Input
                id="city"
                value={form.city}
                onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
              />
            </Field>
            <Field label="Pincode" htmlFor="pin">
              <Input
                id="pin"
                value={form.pincode}
                onChange={(e) => setForm((f) => ({ ...f, pincode: e.target.value }))}
              />
            </Field>
          </div>
          <Field label="Landmark (optional)" htmlFor="lm">
            <Input
              id="lm"
              value={form.landmark ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, landmark: e.target.value }))}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_primary}
              onChange={(e) => setForm((f) => ({ ...f, is_primary: e.target.checked }))}
            />
            Primary address
          </label>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={busy} onClick={submit}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
