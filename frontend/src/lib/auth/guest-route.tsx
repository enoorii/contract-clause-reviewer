import { Navigate, useLocation } from "react-router";
import { useAuth } from "./hooks";
import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";

interface GuestRouteProps {
  children: ReactNode;
}

export function GuestRoute({ children }: GuestRouteProps) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "initializing") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (status === "authenticated") {
    // If they came from a specific page, send them back there, otherwise dashboard
    const from =
      (location.state as { from?: Location })?.from?.pathname || "/dashboard";
    return <Navigate to={from} replace />;
  }

  // If unauthenticated, render the login page
  return <>{children}</>;
}
