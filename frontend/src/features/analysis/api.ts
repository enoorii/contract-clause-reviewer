// src/features/analysis/api.ts
import { api } from "@/lib/api/client";
import type {
  AnalysisCreate,
  AnalysisCreateResponse,
  AnalysisDetailed,
  AnalysisStatusResponse,
  AnalysisSummary,
} from "@/types/analysis";
import type { PaginatedResponse } from "@/types/common";

export function submitAnalysis(data: AnalysisCreate) {
  return api.post<AnalysisCreateResponse>("/api/v1/analysis/analyze", data);
}

export function getAnalysisStatus(taskId: string) {
  return api.get<AnalysisStatusResponse>(`/api/v1/analysis/status/${taskId}`);
}

export function getAnalysis(analysisId: number) {
  return api.get<AnalysisDetailed>(`/api/v1/analysis/${analysisId}`);
}

export function listAnalyses(params?: Record<string, unknown>) {
  return api.get<PaginatedResponse<AnalysisSummary>>("/analysis", {
    params,
  });
}

export function deleteAnalysis(analysisId: number) {
  return api.delete<void>(`/api/v1/analysis/${analysisId}`);
}
