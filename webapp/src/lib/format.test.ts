import {describe, expect, it} from "vitest";
import {fmtKg, fmtMoney, totalKg} from "./format";

describe("format", () => {
  it("formats VND with Vietnamese separators", () => {
    expect(fmtMoney(162000)).toBe("162.000đ");
  });

  it("formats kg with one decimal", () => {
    expect(fmtKg(14)).toBe("14,0 kg");
  });

  it("sums production by snapshot kg_per_unit", () => {
    expect(totalKg([
      {quantity: 5, kg_per_unit: 1.2},
      {quantity: 3, kg_per_unit: 1},
      {quantity: 2, kg_per_unit: 1},
      {quantity: 1, kg_per_unit: 1},
      {quantity: 1, kg_per_unit: 2},
    ])).toBe(14);
  });
});
