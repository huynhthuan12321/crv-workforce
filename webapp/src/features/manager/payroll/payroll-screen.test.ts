import {describe, expect, it} from "vitest";
import type {PayrollSummary} from "../../../types/api";
import {payrollStatusText} from "./PayrollScreen";

const base: PayrollSummary = {
  employee_id: 1,
  code: "NV001",
  full_name: "Nguyễn Văn A",
  work_date: "2024-04-24",
  hourly_rate: 30000,
  closed_minutes: 0,
  eligible_minutes: 0,
  eligible_session_ids: [],
  paid_amount: 0,
  day_total_rounded: 0,
  pending_amount: 0,
  blocked_amount: 0,
  can_approve: false,
  unreviewed_flag_session_ids: [],
  has_open_session: false,
  has_sessions: true,
  needs_review_session_ids: [],
  pending_reason: null,
  pending_reasons: [],
};

describe("payroll row status", () => {
  it("does not show paid-up for GPS-blocked sessions with an open session", () => {
    expect(payrollStatusText({
      ...base,
      blocked_amount: 60000,
      has_open_session: true,
      pending_reason: "unreviewed_gps",
      pending_reasons: ["unreviewed_gps", "open_session"],
    })).toBe("Cần xử lý GPS");
  });

  it("distinguishes employees without sessions from paid-up employees", () => {
    expect(payrollStatusText({...base, has_sessions: false})).toBe("Chưa có phiên");
    expect(payrollStatusText({...base, paid_amount: 162000})).toBe("Đã trả hết");
  });
});
