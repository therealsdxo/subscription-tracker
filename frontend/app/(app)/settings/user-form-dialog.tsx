"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useCreateUser, useUpdateUser, type User } from "@/lib/api/hooks/users";

const ROLES = ["STAFF", "ADMIN"] as const;

export function UserFormDialog({ trigger, editing }: { trigger: React.ReactNode; editing?: User }) {
  const [open, setOpen] = React.useState(false);
  const [email, setEmail] = React.useState(editing?.email ?? "");
  const [fullName, setFullName] = React.useState(editing?.full_name ?? "");
  const [role, setRole] = React.useState<(typeof ROLES)[number]>(editing?.role ?? "STAFF");
  const [password, setPassword] = React.useState("");
  const toast = useToast();
  const create = useCreateUser();
  const update = useUpdateUser();

  const submit = async () => {
    if (!editing && (!email || !fullName || !password)) return;
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          body: { full_name: fullName, role, password: password || undefined },
        });
        toast({ title: "User updated", variant: "success" });
      } else {
        await create.mutateAsync({ email, full_name: fullName, role, password });
        toast({ title: "User created", variant: "success" });
      }
      setOpen(false);
      setPassword("");
    } catch (e) {
      toast({ title: "Save failed", description: (e as Error).message, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent title={editing ? "Edit user" : "New user"}>
        {!editing ? (
          <Field label="Email" htmlFor="email">
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </Field>
        ) : null}
        <Field label="Full name" htmlFor="full_name" className="mt-3">
          <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </Field>
        <Field label="Role" htmlFor="role" className="mt-3">
          <Select id="role" className="w-full" value={role} onChange={(e) => setRole(e.target.value as never)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={editing ? "New password (optional)" : "Password"} htmlFor="password" className="mt-3">
          <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit}>
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
