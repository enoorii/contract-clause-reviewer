import { describe, it, expect, beforeEach, vi } from "vitest";
import { api, setAuthHandler } from "./client";
import type { AuthHandler } from "./types";

function installAuth(overrides: Partial<AuthHandler> = {}): AuthHandler {
  const handler: AuthHandler = {
    getToken: () => "test-token",
    refreshToken: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
  setAuthHandler(handler);
  return handler;
}

describe("apiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    installAuth(); // safe default; each test overrides if needed
  });

  it("serializes query params, including arrays and skipping nulls", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );

    await api.get("/api/test", {
      params: { page: 1, role: "admin", skip: null, tags: ["a", "b"] },
    });

    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).toContain("page=1");
    expect(url).toContain("role=admin");
    expect(url).toContain("tags=a");
    expect(url).toContain("tags=b");
    expect(url).not.toContain("skip=");
  });

  it("attaches the Authorization header from the auth handler", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    installAuth({ getToken: () => "my-token" });

    await api.get("/test");

    const headers = (fetchSpy.mock.calls[0][1] as RequestInit)
      .headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("omits the Authorization header when skipAuth is set", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    installAuth({ getToken: () => "my-token" });

    await api.get("/test", { skipAuth: true });

    const headers = (fetchSpy.mock.calls[0][1] as RequestInit)
      .headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("serializes a JSON body and sets Content-Type", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    await api.post("/test", { name: "Alice" });

    const opts = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(opts.body).toBe(JSON.stringify({ name: "Alice" }));
    expect((opts.headers as Headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("throws HttpError on non-2xx responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
    );

    await expect(api.get("/test")).rejects.toMatchObject({ status: 404 });
  });

  it("wraps fetch failures in NetworkError", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch"),
    );

    await expect(api.get("/test")).rejects.toMatchObject({
      name: "NetworkError",
    });
  });

  it("refreshes the token and retries the request on 401", async () => {
    let currentToken = "old-token";
    let callCount = 0;

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => {
        callCount += 1;
        return callCount === 1
          ? new Response(JSON.stringify({ detail: "Expired" }), { status: 401 })
          : new Response(JSON.stringify({ ok: true }), { status: 200 });
      });

    installAuth({
      getToken: () => currentToken,
      refreshToken: async () => {
        currentToken = "new-token";
        return "new-token";
      },
    });

    const result = await api.get<{ ok: boolean }>("/test");

    expect(result).toEqual({ ok: true });
    expect(callCount).toBe(2);

    // The retry used the refreshed token, not the old one.
    const retryHeaders = (fetchSpy.mock.calls[1][1] as RequestInit)
      .headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer new-token");
  });

  it("logs out and throws on 401 from the refresh endpoint", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Refresh failed" }), {
        status: 401,
      }),
    );
    const handler = installAuth();

    await expect(
      api.post(
        "/api/v1/auth/refresh",
        { refresh_token: "x" },
        { skipAuth: true },
      ),
    ).rejects.toMatchObject({ status: 401 });

    expect(handler.logout).toHaveBeenCalledTimes(1);
  });
});
