// User domain types. UserDetailed is consumed by both the users
// feature and the profile feature, so it lives in the shared layer.

import type { AnalysisSummary } from "./analysis";
import type { Role, SortOrder } from "./common";

// Pydantic: UserResponse
export interface User {
  id: string; // UUID
  username: string;
  role: Role; // NOTE: backend spec currently says plain `string` — see notes below
  must_change_password: boolean;
  is_active: boolean;
}

// Pydantic: UserDetailedResponse
export interface UserDetailed {
  id: string;
  username: string;
  role: Role;
  must_change_password: boolean;
  is_active: boolean;
  // Not in `required` AND nullable: may be omitted or explicitly null
  analyses?: AnalysisSummary[] | null;
}

// Pydantic: UserCreate
export interface UserCreate {
  username: string; // minLength: 3
  password: string;
  role?: Role; // backend default: "user"
}

// Pydantic: UserUpdate
export interface UserUpdate {
  username: string; // minLength: 3
  role?: Role | null;
  is_active?: boolean | null;
}

// Pydantic: PasswordChange
// Used for both self-service (PATCH /users/me/password)
// and admin reset (POST /users/{user_id}/password)
export interface PasswordChange {
  old_password: string;
  new_password: string;
}

// Pydantic: SortBy (users list only supports created_at)
export type UserSortByField = "created_at";

// Query params for GET /api/v1/users
// (no single Pydantic model — derived from endpoint parameters)
export interface UserListParams {
  page?: number; // min 1, default 1
  size?: number; // 1–100, default 10
  search?: string | null;
  sort?: SortOrder | null; // default "desc"
  sort_by?: UserSortByField | null;
  role?: Role | null;
  is_active?: boolean | null;
  from_date?: string | null; // ISO datetime
  to_date?: string | null;
}
