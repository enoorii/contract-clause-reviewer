import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { HttpError } from "@/lib/api/types";
import { tokenStorage } from "@/lib/auth/storage";
import { AuthProvider } from "@/lib/auth/auth-provider";
import { useAuth } from "@/lib/auth/hooks";

vi.mock("@/features/auth/api", () => ({
  login: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
  expireUserSessions: vi.fn(),
}));

vi.mock("@/features/users/api", () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
  changeOwnPassword: vi.fn(),
  getUsers: vi.fn(),
  getUser: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  changeUserPassword: vi.fn(),
  expireUserSessions: vi.fn(),
}));

import * as authApi from "@/features/auth/api";
import * as usersApi from "@/features/users/api";

const MOCK_USER = {
  id: "u1",
  username: "alice",
  role: "user" as const,
  must_change_password: false,
  is_active: true,
};

function renderAuthFlow() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  function Probe() {
    const { user, status, logout } = useAuth();
    return (
      <>
        <div data-testid="status">{status}</div>
        <div data-testid="username">{user?.username ?? "none"}</div>
        <button onClick={() => logout()}>Logout</button>
      </>
    );
  }

  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  );

  return { queryClient };
}

// ─── Session restoration ──────────────────────────────────────────────

describe("Session restoration", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("becomes unauthenticated immediately when no tokens exist", async () => {
    renderAuthFlow();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"),
    );
    expect(usersApi.getProfile).not.toHaveBeenCalled();
    expect(authApi.refresh).not.toHaveBeenCalled();
  });

  it("restores an authenticated session when access token is valid", async () => {
    tokenStorage.setAccessToken("valid-access");
    tokenStorage.setRefreshToken("refresh");
    vi.mocked(usersApi.getProfile).mockResolvedValue(MOCK_USER);

    renderAuthFlow();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );
    expect(screen.getByTestId("username")).toHaveTextContent("alice");
    expect(usersApi.getProfile).toHaveBeenCalledTimes(1);
    expect(authApi.refresh).not.toHaveBeenCalled();
  });

  it("refreshes the token when access token is expired, then retries", async () => {
    tokenStorage.setAccessToken("expired");
    tokenStorage.setRefreshToken("refresh");

    vi.mocked(usersApi.getProfile)
      .mockRejectedValueOnce(new HttpError(401, "Unauthorized"))
      .mockResolvedValueOnce(MOCK_USER);

    vi.mocked(authApi.refresh).mockResolvedValue({
      access_token: "new-access",
      refresh_token: "new-refresh",
      token_type: "bearer",
      expires_in: 1800,
    });

    renderAuthFlow();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );
    expect(authApi.refresh).toHaveBeenCalledWith("refresh");
    expect(usersApi.getProfile).toHaveBeenCalledTimes(2);
    expect(tokenStorage.getAccessToken()).toBe("new-access");
    expect(tokenStorage.getRefreshToken()).toBe("new-refresh");
  });

  it("becomes unauthenticated when refresh fails", async () => {
    tokenStorage.setAccessToken("expired");
    tokenStorage.setRefreshToken("refresh");

    vi.mocked(usersApi.getProfile).mockRejectedValue(
      new HttpError(401, "Unauthorized"),
    );
    vi.mocked(authApi.refresh).mockRejectedValue(
      new HttpError(401, "Refresh failed"),
    );

    renderAuthFlow();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"),
    );
    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });
});

// ─── Logout ────────────────────────────────────────────────────────────

describe("Logout", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("clears tokens, user, status, and the query cache", async () => {
    tokenStorage.setAccessToken("access");
    tokenStorage.setRefreshToken("refresh");
    vi.mocked(usersApi.getProfile).mockResolvedValue(MOCK_USER);
    vi.mocked(authApi.logout).mockResolvedValue(undefined);

    const user = userEvent.setup();
    const { queryClient } = renderAuthFlow();

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated"),
    );

    // Seed cache with data the next user must not see.
    queryClient.setQueryData(["current-user"], MOCK_USER);
    queryClient.setQueryData(["users-list", { page: 1 }], { items: [] });

    await user.click(screen.getByRole("button", { name: /logout/i }));

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"),
    );

    expect(screen.getByTestId("username")).toHaveTextContent("none");
    expect(authApi.logout).toHaveBeenCalledWith("refresh");
    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
    expect(queryClient.getQueryData(["current-user"])).toBeUndefined();
    expect(
      queryClient.getQueryData(["users-list", { page: 1 }]),
    ).toBeUndefined();
  });
});
