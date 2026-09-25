import { api } from "@/lib/api/client";
import type {
  AnalysisCreate,
  AnalysisDetailed,
  AnalysisSummary,
  AnalysisTaskStatusResponse,
  AnalysisTaskCreatedResponse,
  AnalysisListParams,
  PaginatedResponse,
} from "@/types";

// ─── Async Task Operations ───────────────────────────────────────────

/**
 * Submits a document for analysis.
 * Returns a task_id for polling. The actual analysis happens asynchronously via Celery.
 */
export async function submitAnalysis(
  payload: AnalysisCreate,
): Promise<AnalysisTaskCreatedResponse> {
  return api.post<AnalysisTaskCreatedResponse>(
    "/api/v1/analysis/analyze",
    payload,
  );
}

/**
 * Polls the status of an analysis task.
 * Returns status + analysis data (if completed) or error (if failed).
 */
export async function getAnalysisStatus(
  taskId: string,
): Promise<AnalysisTaskStatusResponse> {
  return api.get<AnalysisTaskStatusResponse>(
    `/api/v1/analysis/status/${taskId}`,
  );
}

// ─── CRUD Operations ─────────────────────────────────────────────────

/**
 * Lists all analyses for the current user (paginated).
 */
export async function getAnalyses(
  params?: AnalysisListParams,
): Promise<PaginatedResponse<AnalysisSummary>> {
  return api.get<PaginatedResponse<AnalysisSummary>>("/api/v1/analysis", {
    params,
  });
}

/**
 * Gets a single analysis by ID (detailed, with clauses).
 */
export async function getAnalysis(
  analysisId: number,
): Promise<AnalysisDetailed> {
  return api.get<AnalysisDetailed>(`/api/v1/analysis/${analysisId}`);
}

/**
 * Deletes an analysis. Returns 204 No Content.
 */
export async function deleteAnalysis(analysisId: number): Promise<void> {
  return api.delete<void>(`/api/v1/analysis/${analysisId}`);
}
