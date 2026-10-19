import { describe, it, expect } from "vitest";
import { handleResponse, createNetworkError } from "./errors";
import { HttpError, NetworkError } from "./types";

describe("handleResponse", () => {
  it("returns parsed JSON on success", async () => {
    const response = new Response(JSON.stringify({ ok: true }), {
      status: 200,
    });
    expect(await handleResponse<{ ok: boolean }>(response)).toEqual({
      ok: true,
    });
  });

  it("returns undefined on 204 No Content", async () => {
    const response = new Response(null, { status: 204 });
    expect(await handleResponse(response)).toBeUndefined();
  });

  it("throws HttpError with string detail on 4xx", async () => {
    const response = new Response(JSON.stringify({ detail: "Not found" }), {
      status: 404,
    });
    await expect(handleResponse(response)).rejects.toMatchObject({
      status: 404,
      message: "Not found",
    });
  });

  it("throws HttpError with array detail on 422", async () => {
    const detail = [
      { loc: ["body", "title"], msg: "required", type: "missing" },
    ];
    const response = new Response(JSON.stringify({ detail }), { status: 422 });

    try {
      await handleResponse(response);
      expect.fail("Expected handleResponse to throw");
    } catch (err) {
      expect(err).toBeInstanceOf(HttpError);
      const httpErr = err as HttpError;
      expect(httpErr.status).toBe(422);
      expect(httpErr.details).toEqual(detail);
    }
  });
});

describe("createNetworkError", () => {
  it("converts 'Failed to fetch' TypeErrors", () => {
    const err = createNetworkError(new TypeError("Failed to fetch"));
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.message).toMatch(/network connection failed/i);
  });

  it("converts AbortError DOMExceptions", () => {
    const err = createNetworkError(new DOMException("Aborted", "AbortError"));
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.message).toMatch(/cancelled/i);
  });

  it("falls back to a generic message for unknown errors", () => {
    const err = createNetworkError(new Error("boom"));
    expect(err).toBeInstanceOf(NetworkError);
  });
});
