import { api } from "@/lib/api/client";
import type {
  UserLogin,
  RefreshTokenRequest,
  AuthTokenResponse,
} from "@/types"; // Adjust import path if your barrel export is named differently

/**
 * Authenticates a user and returns access/refresh tokens.
 * skipAuth is true because we do not have a valid access token yet.
 */
export async function login(
  credentials: UserLogin,
): Promise<AuthTokenResponse> {
  return api.post<AuthTokenResponse>("/api/v1/auth/login", credentials, {
    skipAuth: true,
  });
}

/**
 * Exchanges a valid refresh token for a new access/refresh token pair.
 * skipAuth is true because the refresh token is passed in the request body,
 * not as a Bearer token in the header.
 */
export async function refresh(
  refreshToken: string,
): Promise<AuthTokenResponse> {
  const payload: RefreshTokenRequest = {
    refresh_token: refreshToken,
  };
  return api.post<AuthTokenResponse>("/api/v1/auth/refresh", payload, {
    skipAuth: true,
  });
}

/**
 * Revokes the refresh token on the backend.
 * Returns void (handled as 204 No Content by the API client).
 */
export async function logout(refreshToken: string): Promise<void> {
  const payload: RefreshTokenRequest = {
    refresh_token: refreshToken,
  };
  return api.post<void>("/api/v1/auth/logout", payload, { skipAuth: true });
}

/**
 * Expires all active sessions for a specific user (Admin only).
 */
export async function expireUserSessions(userId: string): Promise<void> {
  return api.post<void>(`/api/v1/auth/sessions/expire/${userId}`);
}
