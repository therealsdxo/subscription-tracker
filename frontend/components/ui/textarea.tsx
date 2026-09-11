import * as React from "react";

import { cn } from "@/lib/cn";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    rows={3}
    className={cn(
      "w-full rounded-[var(--radius-sm)] border border-border-strong bg-surface px-2.5 py-2 text-sm",
      "placeholder:text-text-subtle focus-visible:border-accent focus-visible:outline-none",
      "disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
