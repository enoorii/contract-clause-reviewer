// src/app/router.tsx
import { Navigate, Route, Routes } from "react-router";

import AppShell from "@/components/layout/app-shell";
import { PublicLayout } from "@/components/layout/public-layout";
import { AnalysisDetailPage } from "@/pages/analysis/analysis-detail-page";
import { NewAnalysisPage } from "@/pages/analysis/new-analysis-page";
import { LoginPage } from "@/pages/auth/login-page";
import { DashboardPage } from "@/pages/dashboard/dashboard-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { ProfilePage } from "@/pages/profile/profile-page";
import { ReportPage } from "@/pages/reports/report-page";
import { UsersPage } from "@/pages/admin/users-page";
import { RequireAuth } from "@/features/auth/components/protected-route";
import { RequireRole } from "@/features/auth/components/require-role";
import { GuestRoute } from "./lib/auth/guest-route";

export function AppRoutes() {
  return (
    <Routes>
      {/* Redirect root to dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Public routes */}
      <Route element={<PublicLayout />}>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <LoginPage />
            </GuestRoute>
          }
        />
      </Route>

      {/* Protected routes - RequireAuth wraps everything inside */}
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/analysis/new" element={<NewAnalysisPage />} />
          <Route
            path="/analysis/:analysisId"
            element={<AnalysisDetailPage />}
          />
          <Route path="/reports/:analysisId" element={<ReportPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          {/* Admin-only routes */}
          <Route element={<RequireRole allowedRoles={["admin"]} />}>
            <Route path="/admin/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>

      {/* Catch-all 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
