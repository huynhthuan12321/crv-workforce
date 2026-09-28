import {describe, expect, it} from "vitest";
import type {PayrollDetail, PayrollSession, PayrollSummary} from "../../../types/api";
import {groupPayrollSessions, payrollStatusText} from "./PayrollScreen";

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
    })).toBe("Cần xem lại vị trí");
  });

  it("distinguishes employees without sessions from paid-up employees", () => {
    expect(payrollStatusText({...base, has_sessions: false})).toBe("Chưa có phiên");
    expect(payrollStatusText({...base, paid_amount: 162000})).toBe("Đã trả hết");
  });
});

const sessionBase: PayrollSession = {
  id: 1,
  employee_id: 1,
  work_date: "2024-04-24",
  check_in_at: "2024-04-24T07:00:00+07:00",
  check_out_at: "2024-04-24T08:00:00+07:00",
  minutes: 60,
  rate_snapshot: 30000,
  amount_raw: 30000,
  status: "closed",
  flags: [],
  check_in_distance_m: 9,
  check_out_distance_m: 9,
  pay_batch_id: null,
  is_locked: false,
};

describe("payroll detail grouping", () => {
  it("separates eligible, GPS-blocked and open/review sessions", () => {
    const detail = {
      ...base,
      sessions: [
        {...sessionBase, id: 11, payroll_group: "pending_eligible"},
        {...sessionBase, id: 12, flags: ["gps_out_of_range"], payroll_group: "blocked_gps"},
        {...sessionBase, id: 13, status: "open", check_out_at: null, minutes: null, amount_raw: null, payroll_group: "open_or_review"},
        {...sessionBase, id: 14, status: "needs_review", check_out_at: null, minutes: null, amount_raw: null, payroll_group: "open_or_review"},
      ],
      batches: [],
      eligible_session_ids: [11],
      unreviewed_flag_session_ids: [12],
      needs_review_session_ids: [14],
    } satisfies PayrollDetail;

    const groups = groupPayrollSessions(detail);
    expect(groups.pendingEligible.map((row) => row.id)).toEqual([11]);
    expect(groups.blockedGps.map((row) => row.id)).toEqual([12]);
    expect(groups.openOrReview.map((row) => row.id)).toEqual([13, 14]);
  });
});
