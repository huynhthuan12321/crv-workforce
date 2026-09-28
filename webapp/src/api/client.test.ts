import {afterEach, describe, expect, it, vi} from "vitest";
import {api, ApiError} from "./client";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {"content-type": "application/json"},
  });
}

describe("api client errors", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not show network message for FastAPI 422 detail payload", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(422, {detail: [{loc: ["body", "code"], msg: "Field required"}]})));

    await expect(api.get("/locations")).rejects.toMatchObject({
      code: "VALIDATION_ERROR",
      status: 422,
      message: "Dữ liệu chưa hợp lệ, vui lòng kiểm tra lại.",
    } satisfies Partial<ApiError>);
  });

  it("shows network message for 5xx", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(502, {detail: "bad gateway"})));

    await expect(api.get("/health")).rejects.toMatchObject({
      code: "API_ERROR",
      status: 502,
      message: "Không thể kết nối máy chủ. Vui lòng thử lại.",
    } satisfies Partial<ApiError>);
  });

  it("shows network message when fetch throws", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));

    await expect(api.get("/health")).rejects.toMatchObject({
      code: "NETWORK_ERROR",
      message: "Không thể kết nối máy chủ. Vui lòng thử lại.",
    } satisfies Partial<ApiError>);
  });
});
