// src/features/users/hooks.ts
import { useEffect, useState } from "react";

import { getUsers } from "./api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { PaginatedResponse, User, UserListParams } from "@/types";

interface UseUsersListResult {
  data: PaginatedResponse<User> | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Fetches a paginated list of users. Refetches whenever any filter,
 * pagination, or size changes.
 *
 * `refreshKey` is an explicit escape hatch for triggering a refetch after
 * a mutation (create/edit/delete). Increment it and the effect re-runs.
 */
export function useUsersList(
  params: UserListParams,
  refreshKey: number = 0,
): UseUsersListResult {
  const [data, setData] = useState<PaginatedResponse<User> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Destructure so the effect depends on primitives, not the params object.
  // Without this, a new `params` object every render would loop the effect.
  const { page, size, search, sort, sort_by, role, is_active } = params;

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const result = await getUsers(params);
        if (cancelled) return;
        setData(result);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof HttpError || err instanceof NetworkError
            ? err.message
            : "Failed to load users.",
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, size, search, sort, sort_by, role, is_active, refreshKey]);

  return { data, isLoading, error };
}
