"use client";

import { Plus } from "lucide-react";

import { HolidayFormDialog } from "@/app/(app)/settings/holiday-form-dialog";
import { UserFormDialog } from "@/app/(app)/settings/user-form-dialog";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, PageHeader, Spinner, StatusPill } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { useCurrentUser } from "@/lib/api/hooks/auth";
import { useHolidays, useRemoveHoliday } from "@/lib/api/hooks/holidays";
import { useDeactivateUser, useUsers } from "@/lib/api/hooks/users";
import { PAGE_SIZE } from "@/lib/constants";
import { formatDate } from "@/lib/format";

function UsersSection({ isAdmin }: { isAdmin: boolean }) {
  const toast = useToast();
  const users = useUsers({ page: 1, page_size: PAGE_SIZE });
  const deactivate = useDeactivateUser();

  return (
    <div className="border-border bg-surface rounded-[var(--radius)] border p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-text text-sm font-semibold">Users</h2>
        {isAdmin ? (
          <UserFormDialog
            trigger={
              <Button size="sm">
                <Plus className="h-3.5 w-3.5" /> New user
              </Button>
            }
          />
        ) : null}
      </div>

      {users.isError ? (
        <ErrorState message={(users.error as Error).message} />
      ) : users.data && users.data.items.length === 0 ? (
        <EmptyState message="No users." />
      ) : users.data ? (
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Role</Th>
              <Th>Status</Th>
              <Th>Last login</Th>
              {isAdmin ? <Th className="w-40">Actions</Th> : null}
            </tr>
          </thead>
          <tbody>
            {users.data.items.map((u) => (
              <Tr key={u.id}>
                <Td>{u.full_name}</Td>
                <Td className="text-text-muted">{u.email}</Td>
                <Td>{u.role}</Td>
                <Td>
                  <StatusPill value={u.is_active ? "ACTIVE" : "CANCELLED"} />
                </Td>
                <Td>{formatDate(u.last_login_at)}</Td>
                {isAdmin ? (
                  <Td>
                    <div className="flex items-center gap-1.5">
                      <UserFormDialog
                        trigger={
                          <Button variant="secondary" size="sm">
                            Edit
                          </Button>
                        }
                        editing={u}
                      />
                      {u.is_active ? (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={async () => {
                            try {
                              await deactivate.mutateAsync(u.id);
                              toast({ title: "User deactivated", variant: "success" });
                            } catch (e) {
                              toast({ title: "Failed", description: (e as Error).message, variant: "error" });
                            }
                          }}
                        >
                          Deactivate
                        </Button>
                      ) : null}
                    </div>
                  </Td>
                ) : null}
              </Tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <Spinner />
      )}
    </div>
  );
}

function HolidaysSection({ isAdmin }: { isAdmin: boolean }) {
  const toast = useToast();
  const holidays = useHolidays();
  const remove = useRemoveHoliday();

  return (
    <div className="border-border bg-surface rounded-[var(--radius)] border p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-text text-sm font-semibold">Holiday calendar</h2>
        {isAdmin ? (
          <HolidayFormDialog
            trigger={
              <Button size="sm">
                <Plus className="h-3.5 w-3.5" /> Add holiday
              </Button>
            }
          />
        ) : null}
      </div>

      {holidays.isError ? (
        <ErrorState message={(holidays.error as Error).message} />
      ) : holidays.data && holidays.data.length === 0 ? (
        <EmptyState message="No holidays configured." />
      ) : holidays.data ? (
        <div className="space-y-1.5 text-sm">
          {holidays.data.map((h) => (
            <div key={h.id} className="flex items-center justify-between">
              <span>
                {formatDate(h.holiday_date)} — {h.name}
              </span>
              {isAdmin ? (
                <button
                  className="text-danger text-[13px] hover:underline"
                  onClick={async () => {
                    try {
                      await remove.mutateAsync(h.id);
                      toast({ title: "Holiday removed", variant: "success" });
                    } catch (e) {
                      toast({ title: "Failed", description: (e as Error).message, variant: "error" });
                    }
                  }}
                >
                  Remove
                </button>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <Spinner />
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { data: me } = useCurrentUser();
  const isAdmin = me?.role === "ADMIN";

  return (
    <>
      <PageHeader title="Settings" description="Users and holiday calendar" />
      <div className="space-y-4">
        <UsersSection isAdmin={isAdmin} />
        <HolidaysSection isAdmin={isAdmin} />
      </div>
    </>
  );
}
