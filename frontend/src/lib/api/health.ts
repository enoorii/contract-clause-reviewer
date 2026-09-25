// src/lib/api/health.ts
import { api } from "./client";

export interface HealthCheckResponse {
  status: string;
  message: string;
}

export async function checkHealth(): Promise<HealthCheckResponse> {
  return api.get<HealthCheckResponse>("/api/health");
}
