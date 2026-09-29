import {render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import {api} from "../../../api/client";
import {EmployeeDetailScreen, formatLocationInUseMessage, pendingRatesForDisplay} from "./EmployeesScreen";
import type {ManagedEmployee} from "../../../types/api";

describe("location in-use message", () => {
  it("includes current assignments and open sessions", () => {
    expect(formatLocationInUseMessage("Kho A", {
      current_assignments: [{id: 1}, {id: 2}],
      open_sessions: [{id: 10}],
    })).toBe("Không thể ngừng dùng Kho A: còn 2 nhân viên đang phân công, 1 ca đang mở. Chuyển nhân viên sang kho khác trước.");
  });

  it("omits open session text when there is no open session", () => {
    expect(formatLocationInUseMessage("Kho B", {
      current_assignments: 3,
      open_sessions: 0,
    })).toBe("Không thể ngừng dùng Kho B: còn 3 nhân viên đang phân công. Chuyển nhân viên sang kho khác trước.");
  });
});

describe("legacy rate history after 0006", () => {
  it("keeps every pending rate and tolerates an out-of-range value", () => {
    const employee = {
      id: 1,
      code: "NV001",
      full_name: "Nguyễn Văn A",
      role: "employee",
      telegram_id: null,
      is_active: true,
      pending_rate: {
        id: 10,
        hourly_rate: 32_000,
        effective_from: "2026-09-30T00:00:00+07:00",
      },
      pending_rates: [
        {id: 10, hourly_rate: 32_000, effective_from: "2026-09-30T00:00:00+07:00", is_out_of_range: false},
        {id: 11, hourly_rate: 3_200_000, effective_from: "2026-10-01T00:00:00+07:00", is_out_of_range: true},
      ],
    } as ManagedEmployee;

    const rates = pendingRatesForDisplay(employee);
    expect(rates).toHaveLength(2);
    expect(rates[1].hourly_rate).toBe(3_200_000);
    expect(rates[1].is_out_of_range).toBe(true);
  });

  it("falls back to the legacy single pending_rate field", () => {
    const employee = {
      id: 1,
      code: "NV001",
      full_name: "Nguyễn Văn A",
      role: "employee",
      telegram_id: null,
      is_active: true,
      pending_rate: {id: 10, hourly_rate: 32_000, effective_from: "2026-09-30T00:00:00+07:00"},
    } as ManagedEmployee;
    expect(pendingRatesForDisplay(employee)).toHaveLength(1);
  });

  afterEach(() => { vi.restoreAllMocks(); });

  it("renders employee detail with multiple pending and out-of-range rates", async () => {
    const employee = {
      id: 1,
      code: "NV001",
      full_name: "Nguyễn Văn A",
      role: "employee",
      telegram_id: null,
      is_active: true,
      current_hourly_rate: 32_000,
      current_rate_effective_from: "2026-09-27T08:00:00+07:00",
      pending_rates: [
        {id: 10, hourly_rate: 32_000, effective_from: "2026-09-30T00:00:00+07:00"},
        {id: 11, hourly_rate: 3_200_000, effective_from: "2026-10-01T00:00:00+07:00", is_out_of_range: true},
      ],
      pending_rate: {id: 10, hourly_rate: 32_000, effective_from: "2026-09-30T00:00:00+07:00"},
      is_linked: true,
      has_open_session: false,
      current_location: null,
      work_location: null,
    } as ManagedEmployee;
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path.endsWith("/rates")) return employee.pending_rates;
      if (path.endsWith("/location-history")) return [];
      if (path === "/locations?active=true") return [];
      return employee;
    });

    render(<EmployeeDetailScreen employee={employee} onBack={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getAllByText("Mức hẹn")).toHaveLength(2));
    expect(screen.getByText("Vượt giới hạn cho phép – nên hủy")).toBeTruthy();
    expect(screen.getByText("3.200.000đ/giờ")).toBeTruthy();
  });
});
