import { useState } from "react";
import { Menu, X, LogOut } from "lucide-react";

import { Nav } from "@/components/layout/nav";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { useAuth } from "@/lib/auth/hooks";

export function Header() {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { user, logout } = useAuth();

  const closeMobileNav = () => setIsMobileNavOpen(false);

  const handleLogout = async () => {
    await logout();
    // RequireAuth wrapper will automatically redirect to /login
  };

  // Safety fallback while auth is initializing or if somehow unmounted
  if (!user) return null;

  return (
    <>
      <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background px-4 md:px-6">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="lg:hidden"
            onClick={() => setIsMobileNavOpen((prev) => !prev)}
            aria-expanded={isMobileNavOpen}
            aria-controls="mobile-navigation"
          >
            {isMobileNavOpen ? (
              <X className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
            <span className="sr-only">Toggle navigation</span>
          </Button>

          <h1 className="text-lg font-semibold tracking-tight md:text-xl">
            Contract Clause Reviewer
          </h1>
        </div>

        <div className="flex items-center gap-3 md:gap-4">
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.username}
          </span>

          <Badge variant="secondary" className="capitalize">
            {user.role}
          </Badge>

          <ThemeToggle />

          {/* Desktop Logout Button (Hidden on mobile) */}
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="ghost"
                  size="sm"
                  className="hidden lg:flex items-center gap-2 text-muted-foreground hover:text-destructive"
                  onClick={handleLogout}
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden xl:inline">Logout</span>
                </Button>
              }
            ></TooltipTrigger>
            <TooltipContent side="bottom">Logout</TooltipContent>
          </Tooltip>
        </div>
      </header>

      {isMobileNavOpen && (
        <div
          id="mobile-navigation"
          className="border-b bg-background lg:hidden"
        >
          <Nav onNavigate={closeMobileNav} />
        </div>
      )}
    </>
  );
}
