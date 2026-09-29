// src/features/analysis/hooks.ts
import { useEffect, useRef, useState } from "react";

import { getAnalysisStatus } from "./api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { AnalysisStatusResponse } from "@/types/analysis";

const POLL_INTERVAL_MS = 5000;
const MAX_CONSECUTIVE_ERRORS = 3;

interface UseAnalysisStatusResult {
  status: AnalysisStatusResponse | null;
  isLoading: boolean;
  error: string | null;
}

/**
 * Polls the status of a Celery analysis task every 5s until it reaches a
 * terminal state (completed | failed | unknown), or until too many
 * consecutive errors occur.
 *
 * IMPORTANT: consumers must pass the taskId as a `key` on the component
 * that uses this hook. This resets internal state when the taskId
 * changes, without requiring synchronous setState inside the effect.
 *
 *   <AnalysisStatusView key={taskId} taskId={taskId} />
 */
export function useAnalysisStatus(
  taskId: string | undefined,
): UseAnalysisStatusResult {
  // Initial values ARE the reset values. With the `key` pattern, we
  // never need to reset them after mount.
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(taskId));

  // useRef, not useState: we mutate this in the effect and don't want
  // an extra render on every increment.
  const consecutiveErrorsRef = useRef(0);

  useEffect(() => {
    if (!taskId) return;

    // AbortController would also work here; this flag is the minimal
    // equivalent for the "ignore late responses" concern.
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const data = await getAnalysisStatus(taskId);
        if (cancelled) return;

        consecutiveErrorsRef.current = 0;
        setStatus(data);
        setError(null);
        setIsLoading(false);

        if (
          data.status === "completed" ||
          data.status === "failed" ||
          data.status === "unknown"
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
              : "Failed to fetch status.",
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
