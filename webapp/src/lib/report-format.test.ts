import {describe, expect, it} from "vitest";
import {fmtHours, fmtKg} from "./report-format";

describe("report formatting", () => {
  it("formats hours with Vietnamese decimal comma", () => {
    expect(fmtHours(5790)).toBe("96,5 giờ");
  });
  it("formats kilograms with Vietnamese thousands separator", () => {
    expect(fmtKg(1284)).toBe("1.284,0 kg");
  });
});
