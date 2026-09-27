import {describe, expect, it} from "vitest";
import {gpsLabel} from "./gps-label";

describe("gps-label", () => {
  it("uses checkout distance when the GPS flag happened at checkout", () => {
    expect(gpsLabel({
      flags: ["gps_out_of_range"],
      flag_source: "check_out",
      check_in_distance_m: 9,
      check_out_distance_m: 230,
    })).toBe("Ra ca ngoài xưởng (230 m)");
  });

  it("distinguishes check-in out-of-range and low-accuracy flags", () => {
    expect(gpsLabel({
      flags: ["gps_out_of_range"],
      flag_source: "check_in",
      check_in_distance_m: 180,
      check_out_distance_m: 9,
    })).toBe("Vào ca ngoài xưởng (180 m)");

    expect(gpsLabel({
      flags: ["gps_low_accuracy"],
      flag_source: "check_out",
      check_in_accuracy_m: 20,
      check_out_accuracy_m: 130,
    })).toBe("Sai số vị trí lớn (±130 m)");
  });

  it("returns in-workshop text when there is no GPS flag", () => {
    expect(gpsLabel({flags: [], check_in_distance_m: 9})).toBe("Trong xưởng");
  });
});
