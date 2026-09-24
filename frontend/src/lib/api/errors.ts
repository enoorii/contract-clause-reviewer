import { HttpError, NetworkError, type ApiErrorDetail } from "./types";

/**
 * Parses the response and throws a normalized HttpError if the request failed.
 * Handles FastAPI's specific error shapes (422 validation vs business logic errors).
 */
export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let details: ApiErrorDetail[] | string | undefined;
    let message = response.statusText || "An error occurred";

    try {
      const errorData = await response.json();

      // FastAPI returns { detail: [...] } for 422, or { detail: "string" } for 401/403/404
      if (errorData && typeof errorData.detail !== "undefined") {
        details = errorData.detail;

        if (Array.isArray(details)) {
          // Format validation errors into a readable string (e.g., "body.username: Field required")
          message = details
            .map((d) => `${d.loc.join(".")}: ${d.msg}`)
            .join(", ");
        } else if (typeof details === "string") {
          message = details;
        }
      }
    } catch {
      // If parsing JSON fails, fall back to default statusText
    }

    throw new HttpError(response.status, message, details);
  }

  // Handle 204 No Content (e.g., logout, delete)
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  // For other successful responses, parse and return JSON
  const text = await response.text();
  if (!text) {
    return undefined as unknown as T;
  }

  return JSON.parse(text) as T;
}

/**
 * Converts unknown catch errors into a normalized NetworkError.
 */
export function createNetworkError(error: unknown): NetworkError {
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    return new NetworkError(
      "Network connection failed. Please check your internet or backend server.",
    );
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return new NetworkError("Request was cancelled.");
  }
  return new NetworkError("An unexpected network error occurred.");
}
