import {describe, expect, it} from "vitest";
import {elapsedMinutes, temporarySalary} from "./clock";

describe("clock", () => {
  it("calculates temporary rounded salary", () => {
    expect(temporarySalary(208, 30000)).toBe(104000);
  });

  it("floors elapsed minutes", () => {
    expect(elapsedMinutes("2024-04-24T06:12:30+07:00", new Date("2024-04-24T09:40:59+07:00"))).toBe(208);
  });
});
