// src/features/reports/hooks.ts
import { useEffect, useRef, useState } from "react";

import { getReportStatus } from "./api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { ReportTaskStatusResponse } from "@/types";

const POLL_INTERVAL_MS = 2000;
const MAX_CONSECUTIVE_ERRORS = 3;

interface UseReportStatusResult {
  status: ReportTaskStatusResponse | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Polls the status of a Celery report-generation task every 2s until it
 * reaches a terminal state (completed | failed | unknown), or until too
 * many consecutive errors occur.
 *
 * Unlike useAnalysisStatus, this hook does NOT navigate on completion —
 * the report widget stays on the page and renders a download button.
 *
 * IMPORTANT: consumers should key the component that uses this hook on
 * taskId, so a new task resets internal state without synchronous setState
 * in the effect.
 *
 *   <ReportWidget key={taskId} taskId={taskId} analysisId={id} />
 */
export function useReportStatus(
  taskId: string | undefined,
): UseReportStatusResult {
  const [status, setStatus] = useState<ReportTaskStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(taskId));
  const consecutiveErrorsRef = useRef(0);

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const data = await getReportStatus(taskId);
        if (cancelled) return;

        consecutiveErrorsRef.current = 0;
        setStatus(data);
        setError(null);
        setIsLoading(false);

        if (
          data.status === "completed" ||
          data.status === "failed"
        ) {
          return; // terminal — stop polling
        }
      } catch (err) {
        if (cancelled) return;

        consecutiveErrorsRef.current += 1;
        setError(
          err instanceof HttpError
            ? err.message
            : err instanceof NetworkError
              ? err.message
              : "Failed to fetch report status.",
        );

        if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
          setIsLoading(false);
          return;
        }
      }

      timer = setTimeout(poll, POLL_INTERVAL_MS);
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [taskId]);

  return { status, error, isLoading };
}
