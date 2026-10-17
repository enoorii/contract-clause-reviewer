// src/features/users/hooks.ts
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getUsers } from "./api";
import type { PaginatedResponse, User, UserListParams } from "@/types";

/**
 * Fetches a paginated list of users. Refetches whenever any filter,
 * pagination, or size changes.
 *
 * `placeholderData: keepPreviousData` keeps the previous page visible
 * while the next one loads — no table flash when the user clicks Next.
 */
export function useUsersList(params: UserListParams) {
  return useQuery<PaginatedResponse<User>>({
    queryKey: ["users-list", params],
    queryFn: () => getUsers(params),
    placeholderData: keepPreviousData,
  });
}