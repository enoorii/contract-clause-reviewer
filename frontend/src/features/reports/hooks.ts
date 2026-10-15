// src/features/reports/hooks.ts
import { useQuery } from "@tanstack/react-query";

import { getReportStatus } from "./api";
import type { ReportTaskStatusResponse } from "@/types";

const POLL_INTERVAL_MS = 2000;
const MAX_CONSECUTIVE_ERRORS = 3;

/**
 * Polls the status of a Celery report-generation task every 2s until it
 * reaches a terminal state (completed | failed), or until too many
 * consecutive errors occur.
 *
 * Backed by TanStack Query. The polling logic lives in `refetchInterval`:
 * returning a number schedules the next poll; returning `false` stops it.
 * Cancellation, deduplication, and caching are handled by the library.
 *
 * The caller must pass a `taskId`. When it's `undefined`, the query is
 * disabled and no fetch runs — this is why the hook accepts `undefined`
 * rather than requiring the caller to conditionally call it.
 */
export function useReportStatus(taskId: string | undefined) {
  return useQuery<ReportTaskStatusResponse>({
    queryKey: ["report-status", taskId],
    queryFn: () => getReportStatus(taskId!),
    enabled: Boolean(taskId),
    // Each poll is a single attempt; refetchInterval handles the retries.
    // Without this, TanStack Query would retry a failed poll up to the
    // global `retry` config before incrementing fetchFailureCount.
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;

      // Stop polling on terminal states.
      if (status === "completed" || status === "failed") {
        return false;
      }

      // Stop after too many consecutive failures so we don't hammer a
      // broken backend indefinitely.
      if ((query.state.fetchFailureCount ?? 0) >= MAX_CONSECUTIVE_ERRORS) {
        return false;
      }

      return POLL_INTERVAL_MS;
    },
  });
}
