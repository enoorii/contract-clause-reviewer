import { HttpError, type AuthHandler } from "./types";

let isRefreshing = false;
let refreshSubscribers: ((token: string | null) => void)[] = [];

function onTokenRefreshed(token: string | null) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback: (token: string | null) => void) {
  refreshSubscribers.push(callback);
}

/**
 * Handles 401 errors by attempting token refresh and retrying the original request.
 * Implements a queue to prevent multiple simultaneous refresh attempts.
 */
export async function handleAuthError(
  error: HttpError,
  originalRequest: () => Promise<unknown>,
  authHandler: AuthHandler,
): Promise<unknown> {
  // If it's not a 401, or it's already a refresh request, don't retry
  if (error.status !== 401) {
    throw error;
  }

  // If we're already refreshing, queue this request
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      addRefreshSubscriber((token) => {
        if (token) {
          // Retry with new token
          originalRequest().then(resolve).catch(reject);
        } else {
          reject(error);
        }
      });
    });
  }

  // Start refresh process
  isRefreshing = true;

  try {
    const newToken = await authHandler.refreshToken();

    if (!newToken) {
      // Refresh failed - logout
      authHandler.logout();
      throw error;
    }

    // Notify all queued subscribers
    onTokenRefreshed(newToken);

    // Retry the original request
    return await originalRequest();
  } catch (refreshError) {
    // Refresh failed - logout
    authHandler.logout();
    onTokenRefreshed(null);
    throw refreshError;
  } finally {
    isRefreshing = false;
  }
}
