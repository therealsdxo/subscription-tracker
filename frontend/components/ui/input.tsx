import * as React from "react";

import { cn } from "@/lib/cn";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "border-border-strong bg-surface h-9 w-full rounded-[var(--radius-sm)] border px-2.5 text-sm",
      "placeholder:text-text-subtle focus-visible:border-accent focus-visible:outline-none",
      "disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
