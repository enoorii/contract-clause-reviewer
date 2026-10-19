import { describe, it, expect, beforeEach } from "vitest";
import { tokenStorage } from "./storage";

describe("tokenStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("hasTokens is false when storage is empty", () => {
    expect(tokenStorage.hasTokens()).toBe(false);
  });

  it("stores and reads the access token", () => {
    tokenStorage.setAccessToken("access123");
    expect(tokenStorage.getAccessToken()).toBe("access123");
  });

  it("stores and reads the refresh token", () => {
    tokenStorage.setRefreshToken("refresh456");
    expect(tokenStorage.getRefreshToken()).toBe("refresh456");
  });

  it("hasTokens is true only when both tokens exist", () => {
    tokenStorage.setAccessToken("a");
    expect(tokenStorage.hasTokens()).toBe(false);

    tokenStorage.setRefreshToken("r");
    expect(tokenStorage.hasTokens()).toBe(true);
  });

  it("clearTokens removes both tokens", () => {
    tokenStorage.setAccessToken("a");
    tokenStorage.setRefreshToken("r");
    tokenStorage.clearTokens();
    expect(tokenStorage.getAccessToken()).toBeNull();
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });
});
