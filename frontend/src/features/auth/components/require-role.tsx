import { Navigate, Outlet } from "react-router";
import { useAuth } from "@/lib/auth/hooks";
import type { Role } from "@/types";

export function RequireRole({ allowedRoles }: { allowedRoles: Role[] }) {
  const { user, status } = useAuth();

  // Let RequireAuth handle the main loading/unauthenticated states
  if (status !== "authenticated" || !user) {
    return null;
  }

  if (!allowedRoles.includes(user.role)) {
    // Redirect to dashboard if they lack permissions
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
