import { describe, it, expect, beforeEach } from "vitest";
import * as api from "./api";

describe("auth login (per-user)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores token and returns user from API", async () => {
    const res = await api.login({ email: "a@b.com", password: "pw" });
    expect(res?.access_token).toBeTruthy();
    expect(localStorage.getItem("access_token")).toBeTruthy();
    expect(res?.user?.email).toBeTruthy();
  });
});
