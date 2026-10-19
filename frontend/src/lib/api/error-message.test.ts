import { describe, it, expect } from "vitest";
import { getErrorMessage } from "./error-message";
import { HttpError, NetworkError } from "./types";

describe("getErrorMessage", () => {
  it("returns the HttpError message", () => {
    expect(getErrorMessage(new HttpError(404, "Not found"), "fallback")).toBe(
      "Not found",
    );
  });

  it("returns the NetworkError message", () => {
    expect(getErrorMessage(new NetworkError("Offline"), "fallback")).toBe(
      "Offline",
    );
  });

  it("returns the fallback for generic Errors", () => {
    expect(getErrorMessage(new Error("boom"), "fallback")).toBe("fallback");
  });

  it("returns the fallback for non-Error values", () => {
    expect(getErrorMessage("string", "fallback")).toBe("fallback");
    expect(getErrorMessage(undefined, "fallback")).toBe("fallback");
    expect(getErrorMessage(null, "fallback")).toBe("fallback");
  });
});
