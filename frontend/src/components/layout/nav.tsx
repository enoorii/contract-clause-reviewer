import { FilePlus, LayoutDashboard, User, Users, LogOut } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/hooks";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "New Analysis", href: "/analysis/new", icon: FilePlus },
  { label: "Profile", href: "/profile", icon: User },
  {
    label: "User Management",
    href: "/admin/users",
    icon: Users,
    adminOnly: true, // <-- Hidden from non-admins
  },
];

interface NavProps {
  onNavigate?: () => void;
}

export function Nav({ onNavigate }: NavProps) {
  const { user, logout } = useAuth();

  // Filter navigation items based on user role
  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item.adminOnly) {
      return user?.role === "admin";
    }
    return true;
  });

  const handleLogout = async () => {
    if (onNavigate) onNavigate(); // Close mobile nav first
    await logout();
    // RequireAuth wrapper will automatically redirect to /login
  };

  return (
    <nav className="flex flex-col gap-1 p-2">
      {visibleItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.href}
            to={item.href}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={cn(
                    "h-4 w-4",
                    isActive
                      ? "text-primary-foreground"
                      : "text-muted-foreground",
                  )}
                />
                {item.label}
              </>
            )}
          </NavLink>
        );
      })}

      {/* Mobile Logout Button (Hidden on desktop) */}
      <button
        type="button"
        onClick={handleLogout}
        className="mt-2 flex w-full items-center gap-3 rounded-md border-t border-border pt-3 px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-accent hover:text-destructive lg:hidden"
      >
        <LogOut className="h-4 w-4" />
        Logout
      </button>
    </nav>
  );
}
