/**
 * Authentication Storage
 * Framework-agnostic localStorage wrappers for token management.
 */

const STORAGE_KEYS = {
  ACCESS_TOKEN: "auth_access_token",
  REFRESH_TOKEN: "auth_refresh_token",
} as const; // this object and its properties are read-only

export const tokenStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  },

  setAccessToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  },

  setRefreshToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, token);
  },

  clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  },

  hasTokens(): boolean {
    return Boolean(
      localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) &&
      localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN),
    );
  },
};
