import {describe, expect, it} from "vitest";
import {periodBounds, periodLabel} from "./report-period";

describe("report periods", () => {
  it("starts week on Monday across month boundary", () => {
    expect(periodBounds("week", "2026-09-01")).toEqual({from: "2026-08-31", to: "2026-09-06"});
  });
  it("handles year boundary", () => {
    expect(periodBounds("week", "2027-01-01")).toEqual({from: "2026-12-28", to: "2027-01-03"});
  });
  it("formats labels", () => {
    expect(periodLabel("week", "2026-09-27")).toBe("21/09 – 27/09/2026");
    expect(periodLabel("month", "2026-09-27")).toBe("Tháng 09/2026");
  });
});
