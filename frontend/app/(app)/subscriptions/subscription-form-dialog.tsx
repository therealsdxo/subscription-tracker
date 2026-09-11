"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useCustomer, useCustomerSearch } from "@/lib/api/hooks/customers";
import { useActivePackages } from "@/lib/api/hooks/packages";
import { useCreateSubscription, useRenewSubscription } from "@/lib/api/hooks/subscriptions";
import { formatMoney, todayISO } from "@/lib/format";

const WEEKDAYS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 7, label: "Sun" },
];

type Frequency = "DAILY" | "SPECIFIC_WEEKDAYS";
type Slot = "MORNING" | "LUNCH" | "EVENING" | "CUSTOM";

function CustomerPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number, label: string) => void;
}) {
  const [q, setQ] = React.useState("");
  const [label, setLabel] = React.useState("");
  const search = useCustomerSearch(q);

  if (value != null) {
    return (
      <div className="flex items-center justify-between rounded-[var(--radius-sm)] border border-border-strong bg-surface-2 px-2.5 py-2 text-sm">
        <span>{label}</span>
        <button
          type="button"
          className="text-text-muted hover:text-text text-[13px] underline"
          onClick={() => onChange(0, "")}
        >
          change
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <Input
        placeholder="Search customer by name…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {q.trim() && search.data && search.data.length > 0 ? (
        <div className="max-h-40 overflow-y-auto rounded-[var(--radius-sm)] border border-border bg-surface">
          {search.data.map((c) => (
            <button
              key={c.id}
              type="button"
              className="hover:bg-surface-2 block w-full px-2.5 py-1.5 text-left text-sm"
              onClick={() => {
                onChange(c.id, `${c.name} (${c.customer_code})`);
                setLabel(`${c.name} (${c.customer_code})`);
              }}
            >
              {c.name} <span className="text-text-muted">· {c.customer_code}</span>
            </button>
          ))}
        </div>
      ) : q.trim() && search.data?.length === 0 ? (
        <p className="text-text-muted text-[13px]">No match.</p>
      ) : null}
      {label ? null : null}
    </div>
  );
}

export function SubscriptionFormDialog({
  trigger,
  customerId,
  customerLabel,
  renewFrom,
}: {
  trigger: React.ReactNode;
  customerId?: number;
  customerLabel?: string;
  /** When set, this dialog renews that subscription instead of creating a fresh one. */
  renewFrom?: number;
}) {
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<{ id: number; label: string } | null>(
    customerId ? { id: customerId, label: customerLabel ?? "" } : null,
  );
  const [packageId, setPackageId] = React.useState<number | "">("");
  const [startDate, setStartDate] = React.useState(todayISO());
  const [frequency, setFrequency] = React.useState<Frequency>("DAILY");
  const [weekdays, setWeekdays] = React.useState<number[]>([]);
  const [mealsPerDelivery, setMealsPerDelivery] = React.useState(1);
  const [slot, setSlot] = React.useState<Slot>("MORNING");
  const [slotNote, setSlotNote] = React.useState("");
  const [addressId, setAddressId] = React.useState<number | "">("");
  const [notes, setNotes] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const toast = useToast();
  const customer = useCustomer(selected?.id);
  const packages = useActivePackages();
  const create = useCreateSubscription();
  const renew = useRenewSubscription(renewFrom ?? 0);

  const activeAddresses = customer.data?.addresses?.filter((a) => a.is_active) ?? [];

  React.useEffect(() => {
    const primary = activeAddresses.find((a) => a.is_primary);
    if (primary && addressId === "") setAddressId(primary.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customer.data]);

  const reset = () => {
    setPackageId("");
    setStartDate(todayISO());
    setFrequency("DAILY");
    setWeekdays([]);
    setMealsPerDelivery(1);
    setSlot("MORNING");
    setSlotNote("");
    setAddressId("");
    setNotes("");
    if (!customerId) setSelected(null);
  };

  const submit = async () => {
    if (!selected || !packageId || !addressId) return;
    if (frequency === "SPECIFIC_WEEKDAYS" && weekdays.length === 0) {
      toast({ title: "Pick at least one weekday", variant: "error" });
      return;
    }
    setBusy(true);
    try {
      const body = {
        package_id: Number(packageId),
        start_date: startDate,
        delivery_frequency: frequency,
        delivery_weekdays: frequency === "SPECIFIC_WEEKDAYS" ? weekdays : undefined,
        meals_per_delivery: mealsPerDelivery,
        delivery_time_slot: slot,
        delivery_time_slot_note: slot === "CUSTOM" ? slotNote : undefined,
        delivery_address_id: Number(addressId),
        subscription_notes: notes || undefined,
      };
      if (renewFrom) {
        await renew.mutateAsync(body);
        toast({ title: "Renewal created", variant: "success" });
      } else {
        await create.mutateAsync({ ...body, customer_id: selected.id });
        toast({ title: "Subscription created", variant: "success" });
      }
      reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "Save failed", description: (e as Error).message, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        title={renewFrom ? "Renew subscription" : "New subscription"}
        className="max-w-lg"
      >
        <div className="space-y-3">
          <Field label="Customer" htmlFor="customer">
            <CustomerPicker
              value={selected?.id ?? null}
              onChange={(id, label) => setSelected(id ? { id, label } : null)}
            />
          </Field>

          <Field label="Package" htmlFor="package">
            <Select
              id="package"
              className="w-full"
              value={packageId}
              onChange={(e) => setPackageId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Select…</option>
              {packages.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {p.number_of_meals} meals / {p.validity_days}d —{" "}
                  {formatMoney(p.final_price)}
                </option>
              ))}
            </Select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date" htmlFor="start_date">
              <Input
                id="start_date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </Field>
            <Field label="Meals per delivery" htmlFor="mpd">
              <Input
                id="mpd"
                type="number"
                min={1}
                max={10}
                value={mealsPerDelivery}
                onChange={(e) => setMealsPerDelivery(Number(e.target.value))}
              />
            </Field>
          </div>

          <Field label="Delivery address" htmlFor="address">
            <Select
              id="address"
              className="w-full"
              value={addressId}
              onChange={(e) => setAddressId(e.target.value ? Number(e.target.value) : "")}
              disabled={!selected}
            >
              <option value="">Select…</option>
              {activeAddresses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.address_line}, {a.area} {a.is_primary ? "(primary)" : ""}
                </option>
              ))}
            </Select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Frequency" htmlFor="freq">
              <Select
                id="freq"
                className="w-full"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as Frequency)}
              >
                <option value="DAILY">Daily</option>
                <option value="SPECIFIC_WEEKDAYS">Specific weekdays</option>
              </Select>
            </Field>
            <Field label="Time slot" htmlFor="slot">
              <Select id="slot" className="w-full" value={slot} onChange={(e) => setSlot(e.target.value as Slot)}>
                <option value="MORNING">Morning</option>
                <option value="LUNCH">Lunch</option>
                <option value="EVENING">Evening</option>
                <option value="CUSTOM">Custom</option>
              </Select>
            </Field>
          </div>

          {frequency === "SPECIFIC_WEEKDAYS" ? (
            <div className="flex flex-wrap gap-1.5">
              {WEEKDAYS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() =>
                    setWeekdays((prev) =>
                      prev.includes(d.value) ? prev.filter((x) => x !== d.value) : [...prev, d.value],
                    )
                  }
                  className={
                    "rounded-[var(--radius-sm)] border px-2 py-1 text-[13px] " +
                    (weekdays.includes(d.value)
                      ? "border-accent bg-accent text-accent-fg"
                      : "border-border-strong bg-surface text-text-muted")
                  }
                >
                  {d.label}
                </button>
              ))}
            </div>
          ) : null}

          {slot === "CUSTOM" ? (
            <Field label="Slot note" htmlFor="slot_note">
              <Input id="slot_note" value={slotNote} onChange={(e) => setSlotNote(e.target.value)} />
            </Field>
          ) : null}

          <Field label="Notes (optional)" htmlFor="notes">
            <Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={busy || !selected || !packageId || !addressId}
            onClick={submit}
          >
            {busy ? "Saving…" : renewFrom ? "Renew" : "Create subscription"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
