import { Label } from "@radix-ui/react-label";
import * as React from "react";

import { cn } from "@/lib/cn";

export function Field({
  label,
  htmlFor,
  error,
  children,
  className,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={htmlFor} className="text-text block text-[13px] font-medium">
        {label}
      </Label>
      {children}
      {error ? <p className="text-danger text-[13px]">{error}</p> : null}
    </div>
  );
}
