import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  getRegistryEntry,
  identityKeyFor,
  relativeDays,
} from "../api";

// Minimal stand-in for the parts of `Response` that lib/api.ts touches.
interface FakeResponse {
  ok: boolean;
  status: number;
  statusText: string;
  json: () => Promise<unknown>;
}

function fakeResponse(init: Partial<FakeResponse>): FakeResponse {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: init.statusText ?? "",
    json: init.json ?? (async () => ({})),
  };
}

function stubFetch(resp: FakeResponse) {
  const fetchMock = vi.fn(async () => resp as unknown as Response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("identityKeyFor", () => {
  it("formats the durable key as `source:id`", () => {
    expect(identityKeyFor("aws", "role-abc")).toBe("aws:role-abc");
    expect(identityKeyFor("github", "app-42")).toBe("github:app-42");
  });
});

describe("getRegistryEntry", () => {
  it("returns null on a 404 instead of throwing", async () => {
    stubFetch(fakeResponse({ ok: false, status: 404, statusText: "Not Found" }));

    await expect(getRegistryEntry("aws:role-abc")).resolves.toBeNull();
  });

  it("throws ApiError with the parsed { detail } on a non-404 error", async () => {
    stubFetch(
      fakeResponse({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => ({ detail: "registry is on fire" }),
      })
    );

    const error = await getRegistryEntry("aws:role-abc").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
    expect((error as ApiError).message).toBe("registry is on fire");
  });
});

describe("relativeDays", () => {
  it("labels a null timestamp as never used", () => {
    expect(relativeDays(null)).toEqual({ text: "never used", days: null });
  });

  it("labels the current instant as today", () => {
    expect(relativeDays(new Date().toISOString())).toEqual({ text: "today", days: 0 });
  });

  it("labels one day ago as yesterday", () => {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    expect(relativeDays(oneDayAgo)).toEqual({ text: "yesterday", days: 1 });
  });

  it("labels older timestamps with a day count", () => {
    const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString();
    expect(relativeDays(tenDaysAgo)).toEqual({ text: "10 days ago", days: 10 });
  });
});
