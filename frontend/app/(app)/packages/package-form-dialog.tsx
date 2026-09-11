"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useCreatePackage, useUpdatePackage, type Package } from "@/lib/api/hooks/packages";

const schema = z.object({
  name: z.string().min(1, "Required"),
  description: z.string().optional(),
  number_of_meals: z.coerce.number().int().min(1).max(500),
  validity_days: z.coerce.number().int().min(1).max(730),
  base_price: z.coerce.number().min(0),
  tax_amount: z.coerce.number().min(0),
});
type FormInput = z.input<typeof schema>;
type FormOutput = z.output<typeof schema>;

export function PackageFormDialog({
  trigger,
  editing,
}: {
  trigger: React.ReactNode;
  editing?: Package;
}) {
  const [open, setOpen] = React.useState(false);
  const toast = useToast();
  const create = useCreatePackage();
  const update = useUpdatePackage();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(schema),
    defaultValues: editing
      ? {
          name: editing.name,
          description: editing.description ?? "",
          number_of_meals: editing.number_of_meals,
          validity_days: editing.validity_days,
          base_price: Number(editing.base_price),
          tax_amount: Number(editing.tax_amount),
        }
      : { tax_amount: 0 },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, body: values });
        toast({ title: "Package updated", variant: "success" });
      } else {
        await create.mutateAsync(values);
        toast({ title: "Package created", variant: "success" });
        reset({ tax_amount: 0 });
      }
      setOpen(false);
    } catch (e) {
      toast({ title: "Save failed", description: (e as Error).message, variant: "error" });
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        title={editing ? `Edit ${editing.package_code}` : "New package"}
        description="Meals, validity and price are snapshotted onto any subscription created from it."
      >
        <form onSubmit={onSubmit} noValidate className="space-y-3">
          <Field label="Name" htmlFor="name" error={errors.name?.message}>
            <Input id="name" {...register("name")} autoFocus />
          </Field>
          <Field label="Description (optional)" htmlFor="description">
            <Textarea id="description" {...register("description")} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Number of meals"
              htmlFor="number_of_meals"
              error={errors.number_of_meals?.message}
            >
              <Input id="number_of_meals" type="number" {...register("number_of_meals")} />
            </Field>
            <Field
              label="Validity (days)"
              htmlFor="validity_days"
              error={errors.validity_days?.message}
            >
              <Input id="validity_days" type="number" {...register("validity_days")} />
            </Field>
            <Field label="Base price (₹)" htmlFor="base_price" error={errors.base_price?.message}>
              <Input id="base_price" type="number" step="0.01" {...register("base_price")} />
            </Field>
            <Field label="Tax (₹)" htmlFor="tax_amount" error={errors.tax_amount?.message}>
              <Input id="tax_amount" type="number" step="0.01" {...register("tax_amount")} />
            </Field>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : editing ? "Save changes" : "Create package"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
