// Domain-neutral shared types used across multiple features.
// These have no single feature owner.

// Pydantic: Role
export type Role = "admin" | "user" | "viewer";

// Pydantic: Sort
export type SortOrder = "asc" | "desc";

// Shared Celery task status for analysis + reports.
// Matches backend TaskStatus(StrEnum).
export type TaskStatus =
  "pending" | "processing" | "completed" | "failed" | "unknown";

// Pydantic: PaginatedResponse[T] — the generic pagination contract
export interface PaginatedResponse<T> {
  items: T[];
  size: number;
  total: number;
  page: number;
  pages: number;
}

// Pydantic: ValidationError (nested inside HTTPValidationError.detail)
export interface ValidationErrorItem {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

// Pydantic: HTTPValidationError — returned as 422 by all endpoints
export interface ApiValidationError {
  detail?: ValidationErrorItem[];
}
