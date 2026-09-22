import { FilePlus, LayoutDashboard, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router";

import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "New Analysis", href: "/analysis/new", icon: FilePlus },
  { label: "Profile", href: "/profile", icon: User },
];

interface NavProps {
  onNavigate?: () => void;
}

export function Nav({ onNavigate }: NavProps) {
  return (
    <nav className="flex flex-col gap-1 p-2">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.href}
            to={item.href}
            onClick={onNavigate} // <-- Triggered when the link is clicked
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
