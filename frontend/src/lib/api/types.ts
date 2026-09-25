/**
 * API Client Types
 * Framework-agnostic contracts for the centralized HTTP client.
 */

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  /**
   * Query parameters to be serialized into the URL.
   *
   * We use `Record<string, any>` intentionally. TypeScript interfaces
   * do not have implicit index signatures, so strictly typed interfaces
   * (like UserListParams) will fail to assign to `Record<string, unknown>`.
   * Since we only read these values in buildUrl() to serialize them to strings,
   * `any` is safe here and is the industry standard (used by Axios, Ky, etc.).
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params?: Record<string, any>;

  /** Skip attaching the Authorization header (e.g., for login/refresh endpoints) */
  skipAuth?: boolean;

  /** Request body - will be automatically JSON stringified if it's an object */
  body?: unknown;
}

/** Matches FastAPI's ValidationError schema exactly */
export interface ApiErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

/** Normalized error thrown by the API client for non-2xx responses */
export class HttpError extends Error {
  public status: number;
  public details?: ApiErrorDetail[] | string;

  constructor(
    status: number,
    message: string,
    details?: ApiErrorDetail[] | string,
  ) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.details = details;
  }
}

/** Thrown when the network request fails entirely (no response received) */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

/**
 * Interface for the authentication module (Phase 7).
 * The API client depends on this abstraction, not the React Context itself.
 * This keeps `lib/` decoupled from React.
 */
export interface AuthHandler {
  getToken: () => string | null;
  refreshToken: () => Promise<string | null>;
  logout: () => void;
}
