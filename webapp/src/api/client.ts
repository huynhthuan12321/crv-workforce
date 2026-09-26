const API_URL = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) { super(message); this.code = code; }
}

class ApiClient {
  private token = sessionStorage.getItem("crv_token") || "";

  async login(): Promise<any> {
    const initData = window.Telegram?.WebApp?.initData || "";
    const startParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
    try {
      return await this.publicPost("/auth/session", { init_data: initData });
    } catch (error) {
      if (error instanceof ApiError && error.code === "NOT_REGISTERED" && startParam) {
        return this.publicPost("/auth/redeem-invite", { init_data: initData });
      }
      throw error;
    }
  }

  private async publicPost(path: string, body: unknown) {
    const response = await fetch(`${API_URL}${path}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const json = await response.json();
    if (!response.ok) throw new ApiError(json.code || "API_ERROR", json.message || "Có lỗi xảy ra");
    this.token = json.data.token;
    sessionStorage.setItem("crv_token", this.token);
    return json.data;
  }

  async request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {...options, headers: {"Content-Type": "application/json", Authorization: `Bearer ${this.token}`, ...options.headers}});
    const json = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (json.code === "SESSION_EXPIRED" && retry) { await this.login(); return this.request(path, options, false); }
      throw new ApiError(json.code || "API_ERROR", json.message || "Không thể kết nối máy chủ");
    }
    return json.data as T;
  }
  get<T>(path: string) { return this.request<T>(path); }
  post<T>(path: string, body?: unknown) { return this.request<T>(path, {method: "POST", body: body ? JSON.stringify(body) : undefined}); }
  put<T>(path: string, body: unknown) { return this.request<T>(path, {method: "PUT", body: JSON.stringify(body)}); }
  patch<T>(path: string, body: unknown) { return this.request<T>(path, {method: "PATCH", body: JSON.stringify(body)}); }
}

export const api = new ApiClient();
