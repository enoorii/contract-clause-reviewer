import { describe, it, expect } from "vitest";
import { decodeJwt, isTokenExpired, getTokenExpiration } from "./tokens";

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe("decodeJwt", () => {
  it("decodes a valid payload", () => {
    const token = makeJwt({ sub: "user1", exp: 12345 });
    expect(decodeJwt(token)).toEqual({ sub: "user1", exp: 12345 });
  });

  it("returns null for invalid formats", () => {
    expect(decodeJwt("not.a.jwt")).toBeNull();
    expect(decodeJwt("")).toBeNull();
    expect(decodeJwt("no-dots")).toBeNull();
  });
});

describe("isTokenExpired", () => {
  it("returns true when exp is in the past", () => {
    const exp = Math.floor(Date.now() / 1000) - 100;
    expect(isTokenExpired(makeJwt({ sub: "u", exp }))).toBe(true);
  });

  it("returns false when exp is well in the future", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    expect(isTokenExpired(makeJwt({ sub: "u", exp }))).toBe(false);
  });

  it("treats tokens within the 30s buffer as expired", () => {
    const exp = Math.floor(Date.now() / 1000) + 10;
    expect(isTokenExpired(makeJwt({ sub: "u", exp }))).toBe(true);
  });

  it("returns true for invalid tokens", () => {
    expect(isTokenExpired("invalid")).toBe(true);
  });
});

describe("getTokenExpiration", () => {
  it("returns the expiration timestamp in milliseconds", () => {
    const exp = 1700000000;
    expect(getTokenExpiration(makeJwt({ sub: "u", exp }))).toBe(exp * 1000);
  });

  it("returns null for invalid tokens", () => {
    expect(getTokenExpiration("invalid")).toBeNull();
  });
});
