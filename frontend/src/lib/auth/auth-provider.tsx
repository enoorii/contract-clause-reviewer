// src/features/auth/auth-provider.tsx
import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  type PropsWithChildren,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { AuthContext, type AuthStatus } from "./auth-context";
import { tokenStorage } from "@/lib/auth/storage";
import { setAuthHandler } from "@/lib/api/client";
import * as authApi from "@/features/auth/api";
import * as usersApi from "@/features/users/api";
import type { UserDetailed } from "@/types";

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<UserDetailed | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const queryClient = useQueryClient();

  // Session restoration on mount
  useEffect(() => {
    async function restoreSession() {
      if (!tokenStorage.hasTokens()) {
        setStatus("unauthenticated");
        return;
      }

      try {
        const userData = await usersApi.getProfile();
        setUser(userData);
        setStatus("authenticated");
      } catch {
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
          tokenStorage.clearTokens();
          setStatus("unauthenticated");
          return;
        }

        try {
          const tokens = await authApi.refresh(refreshToken);
          tokenStorage.setAccessToken(tokens.access_token);
          tokenStorage.setRefreshToken(tokens.refresh_token);

          const userData = await usersApi.getProfile();
          setUser(userData);
          setStatus("authenticated");
        } catch {
          tokenStorage.clearTokens();
          setStatus("unauthenticated");
        }
      }
    }

    restoreSession();
  }, []);

  // Wire up the AuthHandler for the API client
  useEffect(() => {
    setAuthHandler({
      getToken: () => tokenStorage.getAccessToken(),
      refreshToken: async () => {
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) return null;

        try {
          const tokens = await authApi.refresh(refreshToken);
          tokenStorage.setAccessToken(tokens.access_token);
          tokenStorage.setRefreshToken(tokens.refresh_token);
          return tokens.access_token;
        } catch {
          return null;
        }
      },
      logout: () => {
        tokenStorage.clearTokens();
        setUser(null);
        setStatus("unauthenticated");
        queryClient.clear();
      },
    });
  }, [queryClient]);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const tokens = await authApi.login({ username, password });
      tokenStorage.setAccessToken(tokens.access_token);
      tokenStorage.setRefreshToken(tokens.refresh_token);

      const userData = await usersApi.getProfile();
      setUser(userData);
      setStatus("authenticated");
    } catch (error) {
      setStatus("unauthenticated");
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken();

    try {
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } catch {
      // Ignore logout errors - we're clearing local state anyway
    } finally {
      tokenStorage.clearTokens();
      setUser(null);
      setStatus("unauthenticated");
      queryClient.clear();
    }
  }, [queryClient]);

  /**
   * Merge partial updates into the current user object.
   * Used by mutations that change user fields (e.g., username) so the
   * header and other `useAuth().user` consumers stay in sync with the
   * server's response without a full cache refetch.
   */
  const updateUser = useCallback((updates: Partial<UserDetailed>) => {
    setUser((prev) => (prev ? { ...prev, ...updates } : prev));
  }, []);

  const value = useMemo(
    () => ({
      user,
      status,
      isLoading: status === "initializing",
      login,
      logout,
      updateUser,
    }),
    [user, status, login, logout, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
