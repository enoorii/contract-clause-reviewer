// Reports domain contract types.

import type { TaskStatus } from "./common";

// Pydantic: ReportStatusResponse (after our status-endpoint refactor)
export interface ReportTaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  download_url: string | null; // set only when status === "completed"
  error: string | null; // set only when status === "failed"
}

// Response of POST /api/v1/reports/{analysis_id}.
// Backend currently returns an untyped object; actual payload is { task_id }.
export interface ReportTaskCreatedResponse {
  task_id: string;
}
