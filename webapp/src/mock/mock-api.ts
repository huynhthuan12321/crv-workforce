import {ApiError} from "../api/errors";
import type {AuthData, Consent, History, OutputForm, Today, WorkSession} from "../types/api";
import {
  mockConsent,
  mockEmployee,
  mockEmployees,
  mockHistory,
  mockManager,
  mockDirector,
  mockReportEmployees,
  mockReportProducts,
  mockReportSeries,
  mockReportSummary,
  mockPayroll,
  mockPayrollADetail,
  mockPayrollRealPhone,
  mockReviewPending,
  mockReviewResolved,
  mockWorkingNow,
  outputForScenario,
  scenarioFromUrl,
  todayForScenario,
  type MockScenario,
} from "./scenarios";

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
    if (this.scenario.startsWith("director_")) {
      return {token: "mock-token", employee: mockDirector};
    }
    if (this.scenario.startsWith("manager_")) {
      return {token: "mock-token", employee: mockManager};
    }
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
    if (path.startsWith("/reports/employees")) return mockReportEmployees as T;
    if (path.startsWith("/reports/summary")) {
      if (this.scenario === "director_report_empty") return {...mockReportSummary, minutes: 0, paid: 0, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, total: 0, bags: 0, kg: 0, salary: {paid: 0, pending: 0, pending_eligible: 0, pending_blocked: 0, needs_review_count: 0, total: 0}} as T;
      return mockReportSummary as T;
    }
    if (path.startsWith("/reports/products")) return mockReportProducts as T;
    if (path.startsWith("/reports/timeseries")) return (this.scenario === "director_report_day" ? [mockReportSeries[1]] : mockReportSeries) as T;
    if (path === "/working-now") {
      return (this.scenario === "manager_working_empty" ? [] : mockWorkingNow) as T;
    }
    if (path.startsWith("/review/") && path.endsWith("/checkout-bounds")) {
      return {
        session_id: Number(path.split("/")[2]),
        min_check_out: "2024-04-24T08:06:00+07:00",
        max_check_out: "2024-04-24T13:10:00+07:00",
        sessions: [
          {...mockReviewPending[0], id: 501, status: "closed", check_in_at: "2024-04-24T06:12:00+07:00", check_out_at: "2024-04-24T07:35:00+07:00", minutes: 83},
          {...mockReviewPending[2], id: 503, status: "needs_review"},
        ],
      } as T;
    }
    if (path.startsWith("/review/pending")) return mockReviewPending as T;
    if (path.startsWith("/review/resolved")) return mockReviewResolved as T;
    if (path.includes("/flags-reviewed") && options.method === "POST") {
      if (this.scenario === "manager_already_handled") {
        throw new ApiError("ALREADY_HANDLED", "Mục này đã được xử lý.", 409, {
          handled_by_name: "Giám đốc",
          handled_at: "2024-04-24T10:35:00+07:00",
          action: "flags_reviewed",
        });
      }
      return mockReviewPending[0] as T;
    }
    if (path.includes("/close") && options.method === "POST") return {...mockReviewPending[1], status: "closed"} as T;
    if (path.startsWith("/review/") && options.method === "PATCH") return {...mockPayrollADetail.sessions[1], minutes: 323} as T;
    if (path.startsWith("/payroll/approve") && options.method === "POST") return [
      {employee_id: 2, batch_id: 20, batch_no: 1, amount: 224000},
      {employee_id: 4, batch_id: 21, batch_no: 1, amount: 168000},
    ] as T;
    if (path.startsWith("/payroll/1")) return mockPayrollADetail as T;
    if (path.startsWith("/payroll")) return (this.scenario === "manager_payroll_empty" ? [] : this.scenario === "manager_payroll_real_phone" ? mockPayrollRealPhone : mockPayroll) as T;
    if (path.startsWith("/employees/1/rates") && options.method === "POST") return {id: 9, hourly_rate: 32000, effective_from: "2024-04-25"} as T;
    if (path.startsWith("/employees/1/rates")) return [
      {id: 1, hourly_rate: 30000, effective_from: "2024-04-24"},
      {id: 2, hourly_rate: 28000, effective_from: "2024-01-01"},
    ] as T;
    if (path.startsWith("/employees/1/invite") && options.method === "POST") return {...mockEmployees[0], invite_url: "https://t.me/crv_bot/app?startapp=invite-new"} as T;
    if (path.startsWith("/employees/") && path.endsWith("/lock") && options.method === "POST") {
      if (this.scenario === "manager_lock_open") throw new ApiError("EMPLOYEE_HAS_OPEN_SESSION", "Nhân viên đang trong ca, không thể khóa.", 409);
      return {...mockEmployees[1], is_active: false} as T;
    }
    if (path.startsWith("/employees/") && path.endsWith("/unlock") && options.method === "POST") return {...mockEmployees[2], is_active: true} as T;
    if (path === "/employees" && options.method === "POST") return {...mockEmployees[0], id: 9, code: "NV009", full_name: "Nhân viên mới", is_linked: false, invite_url: "https://t.me/crv_bot/app?startapp=invite-nv009"} as T;
    if (path.startsWith("/employees")) return mockEmployees as T;
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
