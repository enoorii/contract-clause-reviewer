import { describe, it, expect, beforeEach, vi } from "vitest";
import { waitFor } from "@testing-library/react";

import { renderHookWithProviders } from "@/tests/test-utils";

vi.mock("./api", () => ({
  getReportStatus: vi.fn(),
}));

import * as reportsApi from "./api";
import { useReportStatus } from "./hooks";

describe("useReportStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not fetch when taskId is undefined", () => {
    const { result } = renderHookWithProviders(() =>
      useReportStatus(undefined),
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(reportsApi.getReportStatus).not.toHaveBeenCalled();
  });

  it("returns completed status and stops polling", async () => {
    vi.mocked(reportsApi.getReportStatus).mockResolvedValue({
      task_id: "t1",
      status: "completed",
      download_url: "/reports/download/1",
      error: null,
    });

    const { result } = renderHookWithProviders(() => useReportStatus("t1"));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("completed");
    // Terminal state — only one fetch was made.
    expect(reportsApi.getReportStatus).toHaveBeenCalledTimes(1);
  });

  it("returns failed status without retrying", async () => {
    vi.mocked(reportsApi.getReportStatus).mockResolvedValue({
      task_id: "t1",
      status: "failed",
      download_url: null,
      error: "Generation failed",
    });

    const { result } = renderHookWithProviders(() => useReportStatus("t1"));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("failed");
    expect(result.current.data?.error).toBe("Generation failed");
    expect(reportsApi.getReportStatus).toHaveBeenCalledTimes(1);
  });
});
