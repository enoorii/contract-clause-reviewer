// Analysis domain contract types. AnalysisSummary is shared with
// the users feature, which is why these live in the shared layer
// rather than features/analysis/.

import type { SortOrder, TaskStatus } from "./common";

// Pydantic: RiskLevel
export type RiskLevel = "low" | "average" | "high" | "critical";

// Pydantic: AnalysisSortBy
export type AnalysisSortByField =
  "created_at" | "title" | "overall_risk_score" | "document_type";

// Pydantic: AnalysisSummaryResponse
export interface AnalysisSummary {
  id: number;
  title: string;
  description: string | null; // required field, but nullable
  created_at: string; // ISO datetime
}

// Pydantic: ClauseResponse
export interface Clause {
  id: number;
  clause_type: string;
  summary: string;
  risk_level: RiskLevel;
  key_terms: string[];
  suggested_actions: string[];
}

// Pydantic: AnalysisDetailedResponse
export interface AnalysisDetailed {
  id: number;
  title: string;
  description: string | null;
  text: string;
  document_summary: string;
  document_type: string;
  overall_risk_score: number; // 1–10
  recommendations: string[];
  clauses: Clause[];
  created_at: string;
  updated_at: string;
}

// Pydantic: AnalysisCreate
export interface AnalysisCreate {
  title: string; // maxLength: 200
  text: string;
  description?: string | null;
}

// Query params for GET /api/v1/analysis
export interface AnalysisListParams {
  page?: number;
  size?: number;
  search?: string | null;
  sort?: SortOrder | null;
  sort_by?: AnalysisSortByField | null;
  document_type?: string | null;
  min_risk_score?: number | null; // 1–10
  max_risk_score?: number | null; // 1–10
  from_date?: string | null;
  to_date?: string | null;
}

// Pydantic: AnalysisStatusResponse (after our status-endpoint refactor)
// NOTE: Pydantic serializes None fields as null by default, so
// `analysis` and `error` are always present on the wire.
export interface AnalysisTaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  analysis: AnalysisDetailed | null; // set only when status === "completed"
  error: string | null; // set only when status === "failed"
}

// Response of POST /api/v1/analysis/analyze.
// Backend currently returns an untyped object; actual payload is { task_id }.
export interface AnalysisTaskCreatedResponse {
  task_id: string;
}
