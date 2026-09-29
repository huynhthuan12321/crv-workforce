import {render, screen, waitFor} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {AttendanceScreen} from "./AttendanceScreen";

vi.mock("../../api/client", () => ({
  api: {
    get: vi.fn(async () => ({
      open_session: {
        id: 1,
        employee_id: 1,
        work_date: "2026-09-29",
        check_in_at: "2026-09-29T08:00:00+07:00",
        check_out_at: null,
        minutes: null,
        rate_snapshot: 30000,
        amount_raw: null,
        status: "open",
        flags: [],
        check_in_distance_m: 0,
        check_out_distance_m: null,
        location_code_snapshot: "KHO01",
        location_name_snapshot: "Kho A",
      },
      estimated_day_amount: 162000,
      paid_today: 0,
      server_now: "2026-09-29T10:00:00+07:00",
      checkin_cutoff: "18:00",
      can_check_in: false,
      work_location: {id: 1, code: "KHO01", name: "Kho A"},
    })),
    post: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

describe("AttendanceScreen", () => {
  it("separates day estimate from current session formula", async () => {
    render(<AttendanceScreen onNeedConsent={vi.fn()} onCheckedOut={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Tạm tính hôm nay")).toBeTruthy());
    expect(screen.getByText("162.000đ")).toBeTruthy();
    expect(screen.getByText(/Ca này: .*phút × 30\.000đ\/giờ/)).toBeTruthy();
  });
});
