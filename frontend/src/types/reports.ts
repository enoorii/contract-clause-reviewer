// Reports domain contract types.

import type { TaskStatus } from "./common";

// Pydantic: ReportStatusResponse (after our status-endpoint refactor)
export interface ReportTaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  download_url: string | null; // set only when status === "completed"
  error: string | null; // set only when status === "failed"
}

/**
 * Response from POST /reports/{analysis_id}.
 *
 * Two outcomes, discriminated by `status`:
 *   - "queued": a new task was scheduled → poll `status_url`.
 *   - "ready":  the report already exists → download `download_url`.
 *
 * Kept separate from `ReportTaskStatusResponse` (the polling shape)
 * because the two endpoints describe different contracts: one is the
 * outcome of a *decision*, the other the state of a *task*.
 */
export type GenerateReportResponse =
  | { status: "queued"; task_id: string; status_url: string }
  | { status: "ready"; download_url: string };