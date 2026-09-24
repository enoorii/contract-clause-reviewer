import {
  useState,
  useEffect,
  useCallback,
  type PropsWithChildren,
} from "react";
import { AuthContext, type AuthStatus } from "./auth-context";
import { tokenStorage } from "@/lib/auth/storage";
import { setAuthHandler } from "@/lib/api/client";
import * as authApi from "@/features/auth/api";
import type { UserDetailed } from "@/types";

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<UserDetailed | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");

  // Session restoration on mount
  useEffect(() => {
    async function restoreSession() {
      if (!tokenStorage.hasTokens()) {
        setStatus("unauthenticated");
        return;
      }

      try {
        // Try to fetch current user with existing access token
        const userData = await authApi.getCurrentUser();
        setUser(userData);
        setStatus("authenticated");
      } catch {
        // Access token expired or invalid
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
          tokenStorage.clearTokens();
          setStatus("unauthenticated");
          return;
        }

        try {
          // Attempt refresh
          const tokens = await authApi.refresh(refreshToken);
          tokenStorage.setAccessToken(tokens.access_token);
          tokenStorage.setRefreshToken(tokens.refresh_token);

          // Retry fetching user
          const userData = await authApi.getCurrentUser();
          setUser(userData);
          setStatus("authenticated");
        } catch {
          // Refresh failed - clear everything
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
          // Refresh failed - will trigger logout in the interceptor
          return null;
        }
      },
      logout: () => {
        tokenStorage.clearTokens();
        setUser(null);
        setStatus("unauthenticated");
      },
    });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setStatus("initializing");

    try {
      const tokens = await authApi.login({ username, password });
      tokenStorage.setAccessToken(tokens.access_token);
      tokenStorage.setRefreshToken(tokens.refresh_token);

      const userData = await authApi.getCurrentUser();
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
    }
  }, []);

  const value = {
    user,
    status,
    isLoading: status === "initializing",
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
