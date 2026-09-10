import {
  Boxes,
  CalendarDays,
  LayoutDashboard,
  Package,
  Settings,
  Users,
  Wallet,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/packages", label: "Packages", icon: Package },
  { href: "/subscriptions", label: "Subscriptions", icon: Boxes },
  { href: "/deliveries", label: "Deliveries", icon: CalendarDays },
  { href: "/payments", label: "Payments", icon: Wallet },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;
