import { HttpError, type ApiRequestOptions, type AuthHandler } from "./types";
import { handleResponse, createNetworkError } from "./errors";
import { handleAuthError } from "./auth-interceptor";
import { tokenStorage } from "@/lib/auth/storage";

let authHandler: AuthHandler | null = null;

export function setAuthHandler(handler: AuthHandler) {
  authHandler = handler;
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildUrl(endpoint: string, params?: Record<string, unknown>): string {
  const urlString = endpoint.startsWith("http")
    ? endpoint
    : `${BASE_URL}${endpoint}`;
  const url = new URL(urlString, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      // Skip null and undefined values
      if (value === null || value === undefined) return;

      if (Array.isArray(value)) {
        // FastAPI expects arrays as repeated keys: ?role=admin&role=user
        value.forEach((item) => {
          if (item !== null && item !== undefined) {
            url.searchParams.append(key, String(item));
          }
        });
      } else {
        // Standard primitive serialization
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

async function apiClient<T>(
  endpoint: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const url = buildUrl(endpoint, options.params);

  // CRITICAL FIX: Headers are now built INSIDE makeRequest.
  // This ensures that when the interceptor retries, it fetches the NEW token from storage.
  const makeRequest = async (): Promise<T> => {
    const requestHeaders = new Headers(options.headers);

    if (options.body && !(options.body instanceof FormData)) {
      requestHeaders.set("Content-Type", "application/json");
    }
    requestHeaders.set("Accept", "application/json");

    if (!options.skipAuth) {
      const token = authHandler?.getToken() || tokenStorage.getAccessToken();
      if (token) {
        requestHeaders.set("Authorization", `Bearer ${token}`);
      }
    }

    const response = await fetch(url, {
      ...options,
      headers: requestHeaders,
      body:
        options.body instanceof FormData
          ? options.body
          : options.body
            ? JSON.stringify(options.body)
            : undefined,
    });

    return await handleResponse<T>(response);
  };

  try {
    return await makeRequest();
  } catch (error) {
    if (error instanceof HttpError) {
      // Prevent refresh loops: If the refresh endpoint itself fails, force logout
      if (error.status === 401 && endpoint.includes("/auth/refresh")) {
        authHandler?.logout();
        tokenStorage.clearTokens();
        throw error;
      }

      if (error.status === 401 && authHandler && !options.skipAuth) {
        return (await handleAuthError(error, makeRequest, authHandler)) as T;
      }
      throw error;
    }
    throw createNetworkError(error);
  }
}

export const api = {
  get: <T>(
    endpoint: string,
    options?: Omit<ApiRequestOptions, "body" | "method">,
  ) => apiClient<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(
    endpoint: string,
    body?: unknown,
    options?: Omit<ApiRequestOptions, "body" | "method">,
  ) => apiClient<T>(endpoint, { ...options, method: "POST", body }),

  patch: <T>(
    endpoint: string,
    body?: unknown,
    options?: Omit<ApiRequestOptions, "body" | "method">,
  ) => apiClient<T>(endpoint, { ...options, method: "PATCH", body }),

  delete: <T>(
    endpoint: string,
    options?: Omit<ApiRequestOptions, "body" | "method">,
  ) => apiClient<T>(endpoint, { ...options, method: "DELETE" }),
};
