"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { NAV_ITEMS } from "@/components/app-shell/nav";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { useCurrentUser, useLogout } from "@/lib/api/hooks/auth";
import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/cn";

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-0.5 p-2">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2.5 rounded-[var(--radius-sm)] px-2.5 py-2 text-sm",
              active
                ? "bg-surface-2 text-text font-medium"
                : "text-text-muted hover:bg-surface-2 hover:text-text",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const { data: user, isLoading } = useCurrentUser();
  const logout = useLogout();

  return (
    <div className="bg-bg flex min-h-dvh">
      {/* desktop sidebar */}
      <aside className="border-border bg-surface hidden w-56 shrink-0 border-r md:block">
        <div className="border-border flex h-14 items-center border-b px-4 text-sm font-semibold tracking-tight">
          {APP_NAME}
        </div>
        <NavList />
      </aside>

      {/* mobile drawer */}
      {open ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            aria-label="Close menu"
            className="absolute inset-0 bg-black/20"
            onClick={() => setOpen(false)}
          />
          <div className="border-border bg-surface absolute top-0 left-0 h-full w-60 border-r">
            <div className="border-border flex h-14 items-center justify-between border-b px-4 text-sm font-semibold">
              {APP_NAME}
              <button aria-label="Close menu" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <NavList onNavigate={() => setOpen(false)} />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border bg-surface flex h-14 items-center justify-between border-b px-4">
          <button
            className="md:hidden"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="ml-auto flex items-center gap-3 text-sm">
            {isLoading ? (
              <Spinner />
            ) : (
              <span className="text-text-muted">
                {user?.full_name} · {user?.role}
              </span>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              Log out
            </Button>
          </div>
        </header>
        <main className="min-w-0 flex-1 p-5 md:p-7">{children}</main>
      </div>
    </div>
  );
}
