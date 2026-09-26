import {describe, expect, it} from "vitest";
import {fmtKg, fmtMoney, totalKg} from "./format";

describe("format", () => {
  it("formats VND with Vietnamese separators", () => {
    expect(fmtMoney(162000)).toBe("162.000đ");
  });

  it("formats kg with one decimal", () => {
    expect(fmtKg(14)).toBe("14,0 kg");
  });

  it("sums production by kg_per_bag", () => {
    expect(totalKg([
      {bags: 5, kg_per_bag: 1.2},
      {bags: 3, kg_per_bag: 1},
      {bags: 2, kg_per_bag: 1},
      {bags: 1, kg_per_bag: 1},
      {bags: 1, kg_per_bag: 2},
    ])).toBe(14);
  });
});
