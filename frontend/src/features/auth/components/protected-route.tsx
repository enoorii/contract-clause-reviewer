import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "@/lib/auth/hooks";
import { Loader2 } from "lucide-react";

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "initializing") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    // Redirect to login, but save the page they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If authenticated, render the child routes (e.g., AppShell)
  return <Outlet />;
}
