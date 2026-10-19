// src/pages/auth/login-page.test.tsx
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/lib/auth/hooks", () => ({
  useAuth: () => mockAuthState,
}));

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";

import { renderWithProviders } from "@/tests/test-utils";
import { mockAuthState, mockUnauthenticated } from "@/tests/auth-mocks";
import { HttpError } from "@/lib/api/types";
import { LoginPage } from "./login-page";

function renderTree(initialEntries: string[] = ["/login"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<div>Dashboard content</div>} />
    </Routes>,
    { initialEntries },
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    mockUnauthenticated();
    mockAuthState.login.mockReset();
  });

  it("renders the username, password, and submit button", () => {
    renderTree();
    expect(
      screen.getByLabelText("Username", { exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Password", { exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("disables submit when fields are empty", () => {
    renderTree();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeDisabled();
  });

  it("calls login with the entered credentials and navigates on success", async () => {
    const user = userEvent.setup();
    mockAuthState.login.mockResolvedValue(undefined);

    renderTree();

    await user.type(
      screen.getByLabelText("Username", { exact: true }),
      "alice",
    );
    await user.type(
      screen.getByLabelText("Password", { exact: true }),
      "secret123",
    );
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(mockAuthState.login).toHaveBeenCalledWith("alice", "secret123"),
    );
    expect(await screen.findByText(/dashboard content/i)).toBeInTheDocument();
  });

  it("shows a form-level error on invalid credentials", async () => {
    const user = userEvent.setup();
    mockAuthState.login.mockRejectedValue(
      new HttpError(401, "Invalid credentials"),
    );

    renderTree();

    await user.type(
      screen.getByLabelText("Username", { exact: true }),
      "alice",
    );
    await user.type(
      screen.getByLabelText("Password", { exact: true }),
      "wrong",
    );
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText(/invalid username or password/i),
    ).toBeInTheDocument();
  });

  it("toggles password visibility", async () => {
    const user = userEvent.setup();
    renderTree();

    const passwordInput = screen.getByLabelText("Password", {
      exact: true,
    }) as HTMLInputElement;
    expect(passwordInput.type).toBe("password");

    await user.click(screen.getByRole("button", { name: /show password/i }));
    expect(passwordInput.type).toBe("text");

    await user.click(screen.getByRole("button", { name: /hide password/i }));
    expect(passwordInput.type).toBe("password");
  });
});
