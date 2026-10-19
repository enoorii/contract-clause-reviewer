import { describe, it, expect, vi } from "vitest";
import { handleAuthError } from "./auth-interceptor";
import { HttpError } from "./types";

function makeHandler(
  overrides: Partial<{
    getToken: () => string | null;
    refreshToken: () => Promise<string | null>;
    logout: () => void;
  }> = {},
) {
  return {
    getToken: vi.fn(() => "old-token"),
    refreshToken: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
}

describe("handleAuthError", () => {
  it("rethrows non-401 errors without refreshing", async () => {
    const handler = makeHandler();
    const request = vi.fn();
    const error = new HttpError(403, "Forbidden");

    await expect(handleAuthError(error, request, handler)).rejects.toBe(error);
    expect(handler.refreshToken).not.toHaveBeenCalled();
    expect(request).not.toHaveBeenCalled();
  });

  it("refreshes the token and retries on 401", async () => {
    const handler = makeHandler({
      refreshToken: vi.fn().mockResolvedValue("new-token"),
    });
    const request = vi.fn().mockResolvedValue("ok");
    const error = new HttpError(401, "Unauthorized");

    const result = await handleAuthError(error, request, handler);

    expect(result).toBe("ok");
    expect(handler.refreshToken).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("queues concurrent 401s behind a single refresh", async () => {
    let resolveRefresh: (token: string | null) => void;
    const refreshPromise = new Promise<string | null>((resolve) => {
      resolveRefresh = resolve;
    });

    const handler = makeHandler({
      refreshToken: vi.fn().mockReturnValue(refreshPromise),
    });

    const r1 = vi.fn().mockResolvedValue("r1");
    const r2 = vi.fn().mockResolvedValue("r2");
    const r3 = vi.fn().mockResolvedValue("r3");

    const error = new HttpError(401, "Unauthorized");

    const p1 = handleAuthError(error, r1, handler);
    const p2 = handleAuthError(error, r2, handler);
    const p3 = handleAuthError(error, r3, handler);

    // Only one refresh is in flight; other requests are queued.
    expect(handler.refreshToken).toHaveBeenCalledTimes(1);
    expect(r1).not.toHaveBeenCalled();
    expect(r2).not.toHaveBeenCalled();
    expect(r3).not.toHaveBeenCalled();

    resolveRefresh!("new-token");

    const results = await Promise.all([p1, p2, p3]);
    expect(results).toEqual(["r1", "r2", "r3"]);
    expect(handler.refreshToken).toHaveBeenCalledTimes(1);
    expect(r1).toHaveBeenCalledTimes(1);
    expect(r2).toHaveBeenCalledTimes(1);
    expect(r3).toHaveBeenCalledTimes(1);
  });

  it("logs out and rethrows when refresh resolves null", async () => {
    const handler = makeHandler({
      refreshToken: vi.fn().mockResolvedValue(null),
    });
    const request = vi.fn();
    const error = new HttpError(401, "Unauthorized");

    await expect(handleAuthError(error, request, handler)).rejects.toBe(error);
    expect(handler.logout).toHaveBeenCalledTimes(1);
    expect(request).not.toHaveBeenCalled();
  });

  it("logs out and rethrows when refresh throws", async () => {
    const refreshError = new Error("Network down");
    const handler = makeHandler({
      refreshToken: vi.fn().mockRejectedValue(refreshError),
    });
    const request = vi.fn();
    const error = new HttpError(401, "Unauthorized");

    await expect(handleAuthError(error, request, handler)).rejects.toBe(
      refreshError,
    );
    expect(handler.logout).toHaveBeenCalledTimes(1);
  });
});
