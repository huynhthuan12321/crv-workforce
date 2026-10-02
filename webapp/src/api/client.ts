import type {AuthData} from "../types/api";
import {ApiError} from "./errors";

const API_URL = import.meta.env.VITE_API_URL || "/api";
const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1";
const NETWORK_MESSAGE = "Không thể kết nối máy chủ. Vui lòng thử lại.";
const VALIDATION_MESSAGE = "Dữ liệu chưa hợp lệ, vui lòng kiểm tra lại.";

export {ApiError};

type MockApi = typeof import("../mock/mock-api").mockApi;
let mockApiPromise: Promise<MockApi> | null = null;

async function getMockApi() {
  if (!mockApiPromise) {
    const modulePath = "/src/mock/mock-api.ts";
    mockApiPromise = import(/* @vite-ignore */ modulePath).then((module) => module.mockApi as MockApi);
  }
  return mockApiPromise;
}

class ApiClient {
  private token = sessionStorage.getItem("crv_token") || "";

  async login(): Promise<AuthData> {
    if (USE_MOCK) return (await getMockApi()).login();
    let initData = window.Telegram?.WebApp?.initData || "";

    // Một số máy (Android chậm) cấp initData trễ vài trăm ms sau khi tải trang → chờ tối đa ~3 giây.
    for (let i = 0; i < 10 && !initData; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      window.Telegram?.WebApp?.ready?.();
      initData = window.Telegram?.WebApp?.initData || "";
    }

    if (!initData) {
      throw new ApiError(
        "INITDATA_INVALID",
        "Telegram chưa cấp phiên đăng nhập. Vui lòng đóng app và mở lại từ nút Chấm công hoặc nút trong tin nhắn bot.",
        401,
      );
    }

    const startParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
    try {
      return await this.publicPost<AuthData>("/auth/session", {init_data: initData});
    } catch (error) {
      if (error instanceof ApiError && error.code === "NOT_REGISTERED" && startParam && !startParam.startsWith("tab_")) {
        return this.publicPost<AuthData>("/auth/redeem-invite", {init_data: initData});
      }
      throw error;
    }
  }

  private async parseJson(response: Response) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  private errorFromResponse(response: Response, json: any) {
    if (response.status >= 500) {
      return new ApiError(json?.code || "API_ERROR", json?.message || NETWORK_MESSAGE, response.status, json?.details);
    }
    if (json?.code || json?.message) {
      return new ApiError(json?.code || "API_ERROR", json?.message || VALIDATION_MESSAGE, response.status, json?.details);
    }
    if (response.status === 422 && Array.isArray(json?.detail)) {
      return new ApiError("VALIDATION_ERROR", VALIDATION_MESSAGE, response.status, json);
    }
    return new ApiError("API_ERROR", VALIDATION_MESSAGE, response.status, json?.details);
  }

  private async publicPost<T>(path: string, body: unknown): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
      });
    } catch {
      throw new ApiError("NETWORK_ERROR", NETWORK_MESSAGE);
    }
    const json = await this.parseJson(response);
    if (!response.ok) throw this.errorFromResponse(response, json);
    this.token = json.data.token;
    sessionStorage.setItem("crv_token", this.token);
    return json.data as T;
  }

  async request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
    if (USE_MOCK) return (await getMockApi()).request<T>(path, options);
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${this.token}`, ...options.headers},
      });
    } catch {
      throw new ApiError("NETWORK_ERROR", NETWORK_MESSAGE);
    }
    const json = await this.parseJson(response);
    if (!response.ok) {
      if (json?.code === "SESSION_EXPIRED" && retry) {
        await this.login();
        return this.request(path, options, false);
      }
      throw this.errorFromResponse(response, json);
    }
    return json.data as T;
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {method: "POST", body: body ? JSON.stringify(body) : undefined});
  }

  put<T>(path: string, body: unknown) {
    return this.request<T>(path, {method: "PUT", body: JSON.stringify(body)});
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {method: "PATCH", body: JSON.stringify(body)});
  }

  delete<T>(path: string) {
    return this.request<T>(path, {method: "DELETE"});
  }
}

export const api = new ApiClient();

export type ClientErrorPayload = {
  message: string;
  stack?: string;
  tab?: string;
  role?: string;
  app_version?: string;
};

export function reportClientError(payload: ClientErrorPayload) {
  if (USE_MOCK) return;
  const key = `crv_client_error:${payload.tab ?? "unknown"}:${payload.message.slice(0, 80)}`;
  const now = Date.now();
  const last = Number(localStorage.getItem(key) || "0");
  if (now - last < 60_000) return;
  localStorage.setItem(key, String(now));
  const safePayload = {
    message: payload.message.slice(0, 500),
    stack: payload.stack?.slice(0, 4000),
    tab: payload.tab?.slice(0, 64),
    role: payload.role?.slice(0, 64),
    app_version: payload.app_version?.slice(0, 64),
  };
  void fetch(`${API_URL}/client-errors`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(safePayload),
  }).catch(() => {});
}
