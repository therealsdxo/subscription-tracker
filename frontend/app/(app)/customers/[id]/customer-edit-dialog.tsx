"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useUpdateCustomer, type CustomerDetail } from "@/lib/api/hooks/customers";

const DIETARY = ["", "VEGETARIAN", "NON_VEGETARIAN", "EGGETARIAN", "VEGAN", "JAIN", "OTHER"] as const;

export function CustomerEditDialog({
  trigger,
  customer,
}: {
  trigger: React.ReactNode;
  customer: CustomerDetail;
}) {
  const [open, setOpen] = React.useState(false);
  const toast = useToast();
  const update = useUpdateCustomer();
  const [form, setForm] = React.useState({
    name: customer.name,
    phone: customer.phone,
    email: customer.email ?? "",
    default_dietary_preference: customer.default_dietary_preference ?? "",
    allergies: customer.allergies ?? "",
    dietary_notes: customer.dietary_notes ?? "",
    notes: customer.notes ?? "",
  });
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await update.mutateAsync({
        id: customer.id,
        body: {
          name: form.name,
          phone: form.phone,
          email: form.email || null,
          default_dietary_preference: (form.default_dietary_preference || null) as never,
          allergies: form.allergies || null,
          dietary_notes: form.dietary_notes || null,
          notes: form.notes || null,
        },
      });
      toast({ title: "Customer updated", variant: "success" });
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
      <DialogContent title={`Edit ${customer.customer_code}`}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Name" htmlFor="name">
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                autoFocus
              />
            </Field>
            <Field label="Phone" htmlFor="phone">
              <Input
                id="phone"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </Field>
            <Field label="Dietary preference" htmlFor="diet">
              <Select
                id="diet"
                className="w-full"
                value={form.default_dietary_preference}
                onChange={(e) => setForm((f) => ({ ...f, default_dietary_preference: e.target.value }))}
              >
                {DIETARY.map((d) => (
                  <option key={d} value={d}>
                    {d ? d.replace(/_/g, " ") : "—"}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Allergies" htmlFor="allergies">
            <Input
              id="allergies"
              value={form.allergies}
              onChange={(e) => setForm((f) => ({ ...f, allergies: e.target.value }))}
            />
          </Field>
          <Field label="Notes" htmlFor="notes">
            <Textarea
              id="notes"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </Field>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={busy} onClick={submit}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
