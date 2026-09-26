import {ApiError} from "../api/errors";
import type {AuthData, Consent, History, OutputForm, Today, WorkSession} from "../types/api";
import {mockConsent, mockEmployee, mockHistory, outputForScenario, scenarioFromUrl, todayForScenario, type MockScenario} from "./scenarios";

class MockApi {
  scenario: MockScenario = scenarioFromUrl();

  setScenario(next: MockScenario) {
    this.scenario = next;
    const url = new URL(window.location.href);
    url.searchParams.set("scenario", next);
    window.history.replaceState(null, "", url);
  }

  async login(): Promise<AuthData> {
    if (this.scenario === "not_registered") throw new ApiError("NOT_REGISTERED", "Chưa được cấp quyền", 403);
    if (this.scenario === "locked") throw new ApiError("ACCOUNT_LOCKED", "Tài khoản đã bị khóa", 403);
    if (this.scenario === "expired") throw new ApiError("INITDATA_EXPIRED", "Phiên đăng nhập hết hạn", 401);
    if (this.scenario === "network") throw new ApiError("NETWORK_ERROR", "Không thể kết nối máy chủ", 502);
    return {
      token: "mock-token",
      employee: {...mockEmployee, has_location_consent: this.scenario !== "consent"},
    };
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    await new Promise((resolve) => window.setTimeout(resolve, 80));
    if (path === "/attendance/today") return todayForScenario(this.scenario) as T;
    if (path === "/consent/current") {
      return {...mockConsent, accepted: this.scenario !== "consent"} as Consent as T;
    }
    if (path === "/consent" && options.method === "POST") return {accepted: true, version: 1} as T;
    if (path === "/consent/withdraw" && options.method === "POST") return {accepted: false} as T;
    if (path.startsWith("/outputs/") && options.method === "PUT") return {session_id: 102, total_kg: 14, locked_at: new Date().toISOString()} as T;
    if (path.startsWith("/outputs/")) {
      const sessionId = Number(path.split("/").pop() || 102);
      return outputForScenario(this.scenario, sessionId) as OutputForm as T;
    }
    if (path === "/history") return mockHistory as History as T;
    if (path === "/attendance/check-in" && options.method === "POST") {
      return todayForScenario("open").open_session as WorkSession as T;
    }
    if (path === "/attendance/check-out" && options.method === "POST") {
      return {...todayForScenario("open").open_session!, check_out_at: new Date().toISOString(), status: "closed", minutes: 323, amount_raw: 161500} as WorkSession as T;
    }
    throw new ApiError("NOT_FOUND", "Mock chưa có endpoint này", 404);
  }
}

export const mockApi = new MockApi();
