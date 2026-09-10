import * as React from "react";

import { cn } from "@/lib/cn";

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-border bg-surface overflow-x-auto rounded-[var(--radius)] border">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  );
}

export function Th({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "border-border bg-surface-2 text-text-muted border-b px-3 py-2 text-left text-[12px] font-semibold tracking-wide uppercase",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <td className={cn("border-border text-text border-b px-3 py-2", className)}>
      {children}
    </td>
  );
}

export function Tr({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "last:[&>td]:border-b-0",
        onClick && "hover:bg-surface-2 cursor-pointer",
      )}
    >
      {children}
    </tr>
  );
}
