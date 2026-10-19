// src/features/users/components/password-form.test.tsx
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../api", () => ({
  changeOwnPassword: vi.fn(),
}));

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/tests/test-utils";
import * as usersApi from "../api";
import { PasswordForm } from "./password-form";

const currentPassword = () =>
  screen.getByLabelText("Current Password", {
    exact: true,
  }) as HTMLInputElement;
const newPassword = () =>
  screen.getByLabelText("New Password", { exact: true }) as HTMLInputElement;
const confirmPassword = () =>
  screen.getByLabelText("Confirm New Password", {
    exact: true,
  }) as HTMLInputElement;
const submitButton = () =>
  screen.getByRole("button", { name: "Update Password" });

describe("PasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects a password shorter than 8 characters", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PasswordForm />);

    await user.type(currentPassword(), "OldPass1!");
    await user.type(newPassword(), "Short1!");
    await user.type(confirmPassword(), "Short1!");
    await user.click(submitButton());

    expect(
      await screen.findByText(/password must be at least 8 characters/i),
    ).toBeInTheDocument();
    expect(usersApi.changeOwnPassword).not.toHaveBeenCalled();
  });

  it("rejects a new password missing an uppercase letter", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PasswordForm />);

    await user.type(currentPassword(), "OldPass1!");
    await user.type(newPassword(), "lowercase1!");
    await user.type(confirmPassword(), "lowercase1!");
    await user.click(submitButton());

    expect(
      await screen.findByText(/at least one uppercase letter/i),
    ).toBeInTheDocument();
    expect(usersApi.changeOwnPassword).not.toHaveBeenCalled();
  });

  it("rejects when confirmation does not match", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PasswordForm />);

    await user.type(currentPassword(), "OldPass1!");
    await user.type(newPassword(), "NewPass1!");
    await user.type(confirmPassword(), "DifferentPass1!");
    await user.click(submitButton());

    expect(
      await screen.findByText(/passwords do not match/i),
    ).toBeInTheDocument();
    expect(usersApi.changeOwnPassword).not.toHaveBeenCalled();
  });

  it("submits a valid payload and shows success", async () => {
    const user = userEvent.setup();
    vi.mocked(usersApi.changeOwnPassword).mockResolvedValue({
      id: "u1",
      username: "alice",
      role: "user",
      must_change_password: false,
      is_active: true,
    });

    renderWithProviders(<PasswordForm />);

    await user.type(currentPassword(), "OldPass1!");
    await user.type(newPassword(), "NewPass1!");
    await user.type(confirmPassword(), "NewPass1!");
    await user.click(submitButton());

    await waitFor(() =>
      expect(usersApi.changeOwnPassword).toHaveBeenCalledWith({
        old_password: "OldPass1!",
        new_password: "NewPass1!",
      }),
    );
    expect(await screen.findByText(/password updated/i)).toBeInTheDocument();
  });
});
