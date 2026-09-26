import {describe, expect, it} from "vitest";
import {fmtClock, fmtDuration, fmtTime, isAfterCheckinCutoff, todayVN} from "./date-vn";

describe("date-vn", () => {
  it("uses Asia/Ho_Chi_Minh for 00:00-06:59 boundary", () => {
    expect(todayVN(new Date("2024-04-23T17:00:00.000Z"))).toBe("2024-04-24");
    expect(todayVN(new Date("2024-04-23T23:59:00.000Z"))).toBe("2024-04-24");
  });

  it("formats time and durations in Vietnamese app style", () => {
    expect(fmtTime("2024-04-23T23:12:00.000Z")).toBe("06:12");
    expect(fmtDuration(208)).toBe("3h 28p");
    expect(fmtClock(125)).toBe("00:02:05");
  });

  it("detects cutoff by VN time", () => {
    expect(isAfterCheckinCutoff(new Date("2024-04-24T10:59:59.000Z"))).toBe(false);
    expect(isAfterCheckinCutoff(new Date("2024-04-24T11:00:00.000Z"))).toBe(true);
  });
});
