"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useCreateCustomer } from "@/lib/api/hooks/customers";

const DIETARY = ["", "VEGETARIAN", "NON_VEGETARIAN", "EGGETARIAN", "VEGAN", "JAIN", "OTHER"] as const;

const schema = z.object({
  name: z.string().min(1, "Required"),
  phone: z.string().min(4, "Required"),
  email: z.union([z.email("Enter a valid email"), z.literal("")]).optional(),
  default_dietary_preference: z.string().optional(),
  allergies: z.string().optional(),
  notes: z.string().optional(),
  address_line: z.string().min(1, "Required"),
  area: z.string().min(1, "Required"),
  city: z.string().min(1, "Required"),
  pincode: z.string().min(3, "Required"),
  landmark: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function CustomerFormDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  const toast = useToast();
  const create = useCreateCustomer();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    try {
      const result = await create.mutateAsync({
        name: values.name,
        phone: values.phone,
        email: values.email || null,
        default_dietary_preference: (values.default_dietary_preference || null) as never,
        allergies: values.allergies || null,
        notes: values.notes || null,
        addresses: [
          {
            address_line: values.address_line,
            area: values.area,
            city: values.city,
            pincode: values.pincode,
            landmark: values.landmark || null,
            is_primary: true,
          },
        ],
      });
      const warnings = result.warnings ?? [];
      toast({
        title: "Customer created",
        description: warnings[0]?.message,
        variant: warnings.length ? "default" : "success",
      });
      reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "Save failed", description: (e as Error).message, variant: "error" });
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title="New customer" description="Name, phone and one address are required.">
        <form onSubmit={onSubmit} noValidate className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Name" htmlFor="name" error={errors.name?.message}>
              <Input id="name" {...register("name")} autoFocus />
            </Field>
            <Field label="Phone" htmlFor="phone" error={errors.phone?.message}>
              <Input id="phone" {...register("phone")} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Email (optional)" htmlFor="email" error={errors.email?.message}>
              <Input id="email" type="email" {...register("email")} />
            </Field>
            <Field label="Dietary preference" htmlFor="diet">
              <Select id="diet" {...register("default_dietary_preference")} className="w-full">
                {DIETARY.map((d) => (
                  <option key={d} value={d}>
                    {d ? d.replace(/_/g, " ") : "—"}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Allergies (optional)" htmlFor="allergies">
            <Input id="allergies" {...register("allergies")} />
          </Field>

          <div className="border-t border-border pt-3 text-[13px] font-medium text-text-muted">
            Delivery address
          </div>
          <Field label="Address line" htmlFor="address_line" error={errors.address_line?.message}>
            <Input id="address_line" {...register("address_line")} />
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Area" htmlFor="area" error={errors.area?.message}>
              <Input id="area" {...register("area")} />
            </Field>
            <Field label="City" htmlFor="city" error={errors.city?.message}>
              <Input id="city" {...register("city")} />
            </Field>
            <Field label="Pincode" htmlFor="pincode" error={errors.pincode?.message}>
              <Input id="pincode" {...register("pincode")} />
            </Field>
          </div>
          <Field label="Landmark (optional)" htmlFor="landmark">
            <Input id="landmark" {...register("landmark")} />
          </Field>
          <Field label="Notes (optional)" htmlFor="notes">
            <Textarea id="notes" {...register("notes")} />
          </Field>

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Create customer"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
