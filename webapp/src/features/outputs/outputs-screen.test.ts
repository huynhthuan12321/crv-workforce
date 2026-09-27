import {describe, expect, it} from "vitest";
import type {History, HistorySession} from "../../types/api";
import {eligibleSessions, sessionLabel} from "./OutputsScreen";

function session(id: number, checkIn: string, checkOut: string, outputLocked: boolean): HistorySession {
  return {
    id,
    employee_id: 1,
    work_date: checkIn.slice(0, 10),
    check_in_at: checkIn,
    check_out_at: checkOut,
    minutes: 1,
    rate_snapshot: 30000,
    amount_raw: 500,
    status: "closed",
    flags: [],
    check_in_distance_m: 9,
    check_out_distance_m: 9,
    pay_batch_id: null,
    pending_reason: "cho_duyet",
    output_locked: outputLocked,
    output_locked_at: outputLocked ? "2024-04-24T16:36:00+07:00" : "2024-04-24T16:40:00+07:00",
    output: [],
  };
}

function history(sessions: HistorySession[]): History {
  return {
    from: "2024-04-23",
    to: "2024-04-24",
    days: [{
      date: "2024-04-24",
      total_amount: 0,
      paid_amount: 0,
      pending_amount: 0,
      blocked_amount: 0,
      batches: [],
      unpaid_sessions: sessions,
    }],
  };
}

describe("OutputsScreen helpers", () => {
  it("shows only editable closed sessions and sorts newest first", () => {
    const oldLocked = session(1, "2024-04-24T07:54:00+07:00", "2024-04-24T09:42:00+07:00", true);
    const newEditable = session(2, "2024-04-24T16:25:00+07:00", "2024-04-24T16:26:00+07:00", false);
    const picked = eligibleSessions(history([oldLocked, newEditable]));
    expect(picked.map((item) => item.id)).toEqual([2]);
  });

  it("falls back to the latest locked session when nothing is editable", () => {
    const oldLocked = session(1, "2024-04-23T16:25:00+07:00", "2024-04-23T16:26:00+07:00", true);
    const latestLocked = session(2, "2024-04-24T07:54:00+07:00", "2024-04-24T09:42:00+07:00", true);
    const picked = eligibleSessions(history([oldLocked, latestLocked]));
    expect(picked.map((item) => item.id)).toEqual([2]);
    expect(sessionLabel(latestLocked, "2024-04-24")).toBe("Hôm nay · 07:54–09:42");
    expect(sessionLabel(oldLocked, "2024-04-24")).toBe("23/04 · 16:25–16:26");
  });
});
