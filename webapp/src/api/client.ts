import type {AuthData} from "../types/api";
import {ApiError} from "./errors";

const API_URL = import.meta.env.VITE_API_URL || "/api";
const USE_MOCK = import.meta.env.DEV && import.meta.env.VITE_MOCK === "1";

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
    const initData = window.Telegram?.WebApp?.initData || "";
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

  private async publicPost<T>(path: string, body: unknown): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
      });
    } catch {
      throw new ApiError("NETWORK_ERROR", "Không thể kết nối máy chủ. Vui lòng thử lại.");
    }
    const json = await this.parseJson(response);
    if (!response.ok) {
      throw new ApiError(json?.code || "API_ERROR", json?.message || "Không thể kết nối máy chủ. Vui lòng thử lại.", response.status, json?.details);
    }
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
      throw new ApiError("NETWORK_ERROR", "Không thể kết nối máy chủ. Vui lòng thử lại.");
    }
    const json = await this.parseJson(response);
    if (!response.ok) {
      if (json?.code === "SESSION_EXPIRED" && retry) {
        await this.login();
        return this.request(path, options, false);
      }
      throw new ApiError(json?.code || "API_ERROR", json?.message || "Không thể kết nối máy chủ. Vui lòng thử lại.", response.status, json?.details);
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
}

export const api = new ApiClient();
