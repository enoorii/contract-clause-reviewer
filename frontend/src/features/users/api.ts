import { api } from "@/lib/api/client";
import type {
  User,
  UserDetailed,
  UserCreate,
  UserUpdate,
  PasswordChange,
  UserListParams,
  PaginatedResponse,
} from "@/types";

// ─── Current user (self-service) ─────────────────────────────────────
/**
 * Fetches the current user's profile data.
 * Requires a valid access token (skipAuth is false by default).
 */

export async function getProfile(): Promise<UserDetailed> {
  return api.get<UserDetailed>("/api/v1/users/me");
}

/**
 * Updates the current user's profile.
 * NOTE: The backend expects `new_username` as a query parameter, not a JSON body.
 */
export async function updateProfile(
  newUsername: string,
): Promise<UserDetailed> {
  return api.patch<UserDetailed>("/api/v1/users/me", undefined, {
    params: { new_username: newUsername },
  });
}

export async function changeOwnPassword(
  payload: PasswordChange,
): Promise<User> {
  return api.patch<User>("/api/v1/users/me/password", payload);
}

// ─── Admin: user management ──────────────────────────────────────────

export async function getUsers(
  params?: UserListParams,
): Promise<PaginatedResponse<User>> {
  return api.get<PaginatedResponse<User>>("/api/v1/users", { params });
}

export async function getUser(userId: string): Promise<UserDetailed> {
  return api.get<UserDetailed>(`/api/v1/users/${userId}`);
}

export async function createUser(payload: UserCreate): Promise<User> {
  return api.post<User>("/api/v1/users", payload);
}

export async function updateUser(
  userId: string,
  payload: UserUpdate,
): Promise<UserDetailed> {
  return api.patch<UserDetailed>(`/api/v1/users/${userId}`, payload);
}

/**
 * Deletes a user. Returns 204 No Content (no response body).
 */
export async function deleteUser(userId: string): Promise<void> {
  return api.delete<void>(`/api/v1/users/${userId}`);
}

export async function changeUserPassword(
  userId: string,
  payload: PasswordChange,
): Promise<User> {
  return api.post<User>(`/api/v1/users/${userId}/password`, payload);
}

/**
 * Expires all active sessions for a specific user (Admin only).
 */
export async function expireUserSessions(userId: string): Promise<void> {
  return api.post<void>(`/api/v1/auth/sessions/expire/${userId}`);
}
