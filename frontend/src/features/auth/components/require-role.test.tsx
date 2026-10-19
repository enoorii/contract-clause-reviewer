import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";

import { renderWithProviders } from "@/tests/test-utils";
import {
  mockAuthState,
  mockAuthenticated,
  mockUnauthenticated,
} from "@/tests/auth-mocks";

vi.mock("@/lib/auth/hooks", () => ({
  useAuth: () => mockAuthState,
}));

import { RequireRole } from "./require-role";

function TestTree() {
  return (
    <Routes>
      <Route path="/dashboard" element={<div>Dashboard content</div>} />
      <Route element={<RequireRole allowedRoles={["admin"]} />}>
        <Route path="/admin/users" element={<div>Admin users page</div>} />
      </Route>
    </Routes>
  );
}

describe("RequireRole", () => {
  it("renders children for allowed roles", () => {
    mockAuthenticated({ role: "admin" });
    renderWithProviders(<TestTree />, { initialEntries: ["/admin/users"] });
    expect(screen.getByText(/admin users page/i)).toBeInTheDocument();
  });

  it("redirects to /dashboard for disallowed roles", () => {
    mockAuthenticated({ role: "user" });
    renderWithProviders(<TestTree />, { initialEntries: ["/admin/users"] });
    expect(screen.getByText(/dashboard content/i)).toBeInTheDocument();
    expect(screen.queryByText(/admin users page/i)).not.toBeInTheDocument();
  });

  it("renders nothing when not authenticated", () => {
    mockUnauthenticated();
    renderWithProviders(<TestTree />, { initialEntries: ["/admin/users"] });
    expect(screen.queryByText(/admin users page/i)).not.toBeInTheDocument();
  });
});
