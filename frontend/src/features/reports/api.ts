import { api } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/storage";
import type {
  ReportTaskCreatedResponse,
  ReportTaskStatusResponse,
} from "@/types";

// ─── Async Task Operations ───────────────────────────────────────────

/**
 * Triggers report generation for an analysis.
 * Returns a task_id for polling. The PDF is generated asynchronously via Celery.
 */
export async function generateReport(
  analysisId: number,
): Promise<ReportTaskCreatedResponse> {
  return api.post<ReportTaskCreatedResponse>(`/api/v1/reports/${analysisId}`);
}

/**
 * Polls the status of a report generation task.
 * Returns status + download_url (if completed) or error (if failed).
 */
export async function getReportStatus(
  taskId: string,
): Promise<ReportTaskStatusResponse> {
  return api.get<ReportTaskStatusResponse>(`/api/v1/reports/status/${taskId}`);
}

// ─── File Download (The One Exception) ───────────────────────────────

/**
 * Downloads the generated PDF report as a Blob.
 *
 * NOTE: This endpoint returns a binary file, not JSON.
 * We cannot use the standard `api.get()` because it automatically parses JSON.
 * Using native `fetch` here is the one justified exception to the
 * "don't use fetch in features" rule, because file downloads require
 * fundamentally different response handling (Blob vs JSON).
 */
export async function downloadReport(analysisId: number): Promise<Blob> {
  const token = tokenStorage.getAccessToken();
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
  const url = `${baseUrl}/api/v1/reports/download/${analysisId}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/pdf",
    },
  });

  if (!response.ok) {
    throw new Error(`Download failed with status ${response.status}`);
  }

  return response.blob();
}

/**
 * Triggers a browser file download from a Blob.
 * This is a utility function used by the UI component after calling downloadReport().
 */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
