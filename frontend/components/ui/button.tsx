import { Slot } from "@radix-ui/react-slot";
import * as React from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg border-accent hover:opacity-90 disabled:opacity-50",
  secondary:
    "bg-surface text-text border-border-strong hover:bg-surface-2 disabled:opacity-50",
  ghost: "bg-transparent text-text border-transparent hover:bg-surface-2",
  danger: "bg-transparent text-danger border-border-strong hover:bg-danger-bg",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-2.5 text-[13px]",
  md: "h-9 px-3.5 text-sm",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", asChild, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-sm)] border font-medium transition-colors",
          "focus-visible:outline-2 disabled:cursor-not-allowed",
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
