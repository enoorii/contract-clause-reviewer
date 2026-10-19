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

import { RequireAuth } from "./protected-route";

function TestTree() {
  return (
    <Routes>
      <Route path="/login" element={<div>Login page</div>} />
      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<div>Dashboard content</div>} />
      </Route>
    </Routes>
  );
}

describe("RequireAuth", () => {
  it("shows a spinner while auth is initializing", () => {
    mockAuthState.status = "initializing";
    mockAuthState.user = null;

    renderWithProviders(<TestTree />, { initialEntries: ["/dashboard"] });

    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated", () => {
    mockUnauthenticated();
    renderWithProviders(<TestTree />, { initialEntries: ["/dashboard"] });

    expect(screen.getByText(/login page/i)).toBeInTheDocument();
    expect(screen.queryByText(/dashboard content/i)).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    mockAuthenticated();
    renderWithProviders(<TestTree />, { initialEntries: ["/dashboard"] });

    expect(screen.getByText(/dashboard content/i)).toBeInTheDocument();
  });
});
