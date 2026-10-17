// src/features/analysis/hooks.ts
import { useQuery } from "@tanstack/react-query";

import { getAnalysisStatus } from "./api";
import type { AnalysisStatusResponse } from "@/types/analysis";

const POLL_INTERVAL_MS = 5000;
const MAX_CONSECUTIVE_ERRORS = 3;

/**
 * Polls the status of a Celery analysis task every 5s until it reaches a
 * terminal state (completed | failed), or until too many consecutive
 * errors occur.
 *
 * Backed by TanStack Query. The polling logic lives in `refetchInterval`:
 * a number schedules the next poll; `false` stops it. Cancellation,
 * caching, and deduplication are handled by the library.
 *
 * Unlike the previous hand-rolled version, this hook does NOT treat
 * "unknown" as a terminal state — it's treated as transient, matching
 * the behavior of `useReportStatus`.
 */
export function useAnalysisStatus(taskId: string | undefined) {
  return useQuery<AnalysisStatusResponse>({
    queryKey: ["analysis-status", taskId],
    queryFn: () => getAnalysisStatus(taskId!),
    enabled: Boolean(taskId),
    retry: false,
    refetchInterval: (query) => {
      const taskStatus = query.state.data?.status;

      if (taskStatus === "completed" || taskStatus === "failed") {
        return false;
      }

      if ((query.state.fetchFailureCount ?? 0) >= MAX_CONSECUTIVE_ERRORS) {
        return false;
      }

      return POLL_INTERVAL_MS;
    },
  });
}
