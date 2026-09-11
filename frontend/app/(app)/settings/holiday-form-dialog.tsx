"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAddHoliday } from "@/lib/api/hooks/holidays";
import { todayISO } from "@/lib/format";

export function HolidayFormDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  const [date, setDate] = React.useState(todayISO());
  const [name, setName] = React.useState("");
  const toast = useToast();
  const add = useAddHoliday();

  const submit = async () => {
    if (!name.trim()) return;
    try {
      await add.mutateAsync({ holiday_date: date, name: name.trim() });
      toast({ title: "Holiday added", variant: "success" });
      setOpen(false);
      setName("");
    } catch (e) {
      toast({ title: "Failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title="Add holiday" description="No deliveries are generated on this date.">
        <Field label="Date" htmlFor="date">
          <Input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <Field label="Name" htmlFor="name" className="mt-3">
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!name.trim()} onClick={submit}>
            Add
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
