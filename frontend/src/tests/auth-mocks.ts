// src/tests/auth-mocks.ts
import { vi, type Mock } from "vitest";
import type { AuthContextValue } from "@/lib/auth/auth-context";
import type { UserDetailed } from "@/types";

/**
 * Auth context value with its function fields typed as vi mocks so that
 * test files can call `.mockResolvedValue`, `.mockReset`, etc. without casts.
 */
export interface MockAuthContext extends Omit<
  AuthContextValue,
  "login" | "logout" | "updateUser"
> {
  login: Mock<AuthContextValue["login"]>;
  logout: Mock<AuthContextValue["logout"]>;
  updateUser: Mock<AuthContextValue["updateUser"]>;
}

export const mockAuthState: MockAuthContext = {
  user: null,
  status: "unauthenticated",
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  updateUser: vi.fn(),
};

export function mockAuthenticated(overrides: Partial<UserDetailed> = {}): void {
  mockAuthState.user = {
    id: "user-1",
    username: "test-user",
    role: "user",
    must_change_password: false,
    is_active: true,
    ...overrides,
  };
  mockAuthState.status = "authenticated";
  mockAuthState.isLoading = false;
}

export function mockUnauthenticated(): void {
  mockAuthState.user = null;
  mockAuthState.status = "unauthenticated";
  mockAuthState.isLoading = false;
}
