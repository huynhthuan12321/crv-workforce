import {describe, expect, it} from "vitest";
import type {HistorySession} from "../../types/api";
import {groupHistorySessions} from "./HistoryScreen";

const base = {
  id: 1,
  employee_id: 1,
  work_date: "2026-09-29",
  check_in_at: "2026-09-29T08:00:00+07:00",
  check_out_at: "2026-09-29T09:00:00+07:00",
  minutes: 60,
  rate_snapshot: 30000,
  amount_raw: 30000,
  status: "closed" as const,
  flags: [] as string[],
  check_in_distance_m: 0,
  check_out_distance_m: 0,
  pay_batch_id: null,
  pending_reason: null,
  output: [],
} satisfies HistorySession;

describe("history payroll groups", () => {
  it("splits unpaid sessions into eligible, blocked GPS and open/review", () => {
    const groups = groupHistorySessions([
      {...base, id: 1, payroll_group: "pending_eligible"},
      {...base, id: 2, flags: ["gps_out_of_range"], payroll_group: "blocked_gps"},
      {...base, id: 3, status: "open", check_out_at: null, minutes: null, amount_raw: null, payroll_group: "open_or_review"},
      {...base, id: 4, status: "needs_review", check_out_at: null, minutes: null, amount_raw: null, payroll_group: "open_or_review"},
    ]);
    expect(groups.pendingEligible.map((row) => row.id)).toEqual([1]);
    expect(groups.blockedGps.map((row) => row.id)).toEqual([2]);
    expect(groups.openOrReview.map((row) => row.id)).toEqual([3, 4]);
  });
});
