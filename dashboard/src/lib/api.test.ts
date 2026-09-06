import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createJob,
  evidenceImageUrl,
  getJobStatus,
  getViolation,
  listViolations,
  updateViolation,
} from "./api";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listViolations", () => {
  it("fetches the violations endpoint", async () => {
    const fetchMock = mockFetchOnce([]);
    await listViolations();
    const url = fetchMock.mock.calls[0][0] as URL;
    expect(url.pathname).toBe("/violations");
    expect(url.searchParams.has("status")).toBe(false);
  });

  it("passes a status filter as a query param", async () => {
    const fetchMock = mockFetchOnce([]);
    await listViolations("pending_review");
    const url = fetchMock.mock.calls[0][0] as URL;
    expect(url.searchParams.get("status")).toBe("pending_review");
  });

  it("throws on a non-ok response", async () => {
    mockFetchOnce({ detail: "nope" }, false, 500);
    await expect(listViolations()).rejects.toThrow(/500/);
  });
});

describe("getViolation", () => {
  it("fetches a single violation by id", async () => {
    const fetchMock = mockFetchOnce({ id: 1 });
    await getViolation(1);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/violations\/1$/);
  });
});

describe("updateViolation", () => {
  it("PATCHes with the given fields as JSON", async () => {
    const fetchMock = mockFetchOnce({ id: 1, status: "confirmed" });
    await updateViolation(1, { status: "confirmed" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/violations\/1$/);
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body)).toEqual({ status: "confirmed" });
  });

  it("can send an explicit null to clear a field", async () => {
    const fetchMock = mockFetchOnce({ id: 1, plate_text: null });
    await updateViolation(1, { plate_text: null });
    const options = fetchMock.mock.calls[0][1];
    // JSON.stringify keeps explicit null keys - this is what makes clearing
    // a field distinguishable from omitting it, matching the API's
    // exclude_unset semantics (see cv-service/app/routers/violations.py)
    expect(JSON.parse(options.body)).toEqual({ plate_text: null });
  });
});

describe("createJob", () => {
  it("sends speed_limit_kmh as a query param, not a form field", async () => {
    // a real bug caught during manual testing: the API defines this as a
    // query param (FastAPI's default for a plain type alongside UploadFile),
    // not a form field - a client sending it as form data has it silently
    // ignored in favor of the default value
    const fetchMock = mockFetchOnce({ job_id: "abc", source_id: "x.mp4" });
    const file = new File([new Uint8Array([1, 2, 3])], "test.mp4", { type: "video/mp4" });
    await createJob(file, 42);
    const [url, options] = fetchMock.mock.calls[0];
    expect((url as URL).searchParams.get("speed_limit_kmh")).toBe("42");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
  });

  it("omits simulate_live by default and sends it as a query param when true", async () => {
    const fetchMock = mockFetchOnce({ job_id: "abc", source_id: "x.mp4" });
    const file = new File([new Uint8Array([1, 2, 3])], "test.mp4", { type: "video/mp4" });

    await createJob(file, 42);
    expect((fetchMock.mock.calls[0][0] as URL).searchParams.has("simulate_live")).toBe(false);

    await createJob(file, 42, true);
    expect((fetchMock.mock.calls[1][0] as URL).searchParams.get("simulate_live")).toBe("true");
  });
});

describe("getJobStatus", () => {
  it("fetches a job by id", async () => {
    const fetchMock = mockFetchOnce({ job_id: "abc", status: "queued", result: null, error: null });
    await getJobStatus("abc");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/jobs\/abc$/);
  });
});

describe("evidenceImageUrl", () => {
  it("builds the evidence image url for a violation", () => {
    expect(evidenceImageUrl(5)).toMatch(/\/violations\/5\/evidence$/);
  });
});
