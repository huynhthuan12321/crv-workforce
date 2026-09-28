export type GpsLabelInput = {
  flags: string[];
  flag_source?: "check_in" | "check_out" | "both" | string | null;
  check_in_distance_m?: number | null;
  check_out_distance_m?: number | null;
  check_in_accuracy_m?: number | null;
  check_out_accuracy_m?: number | null;
  location_name_snapshot?: string | null;
  location_code_snapshot?: string | null;
  location_name?: string | null;
  location_code?: string | null;
  nearby_location_name?: string | null;
  nearby_location_code?: string | null;
  nearby_location_distance_m?: number | null;
};

function round(value: number | null | undefined): number {
  return Math.round(Number(value ?? 0));
}

export function gpsLabel(row: GpsLabelInput): string {
  if (row.flags.includes("gps_low_accuracy")) {
    const accuracy = row.flag_source === "check_out"
      ? row.check_out_accuracy_m
      : Math.max(Number(row.check_in_accuracy_m ?? 0), Number(row.check_out_accuracy_m ?? 0));
    return `Sai số vị trí lớn (±${round(accuracy)} m)`;
  }

  if (row.flags.includes("gps_out_of_range")) {
    const assigned = row.location_name_snapshot || row.location_name || row.location_code_snapshot || row.location_code;
    const nearby = row.nearby_location_name || row.nearby_location_code;
    const nearbyText = nearby && row.nearby_location_distance_m != null
      ? ` · Đang trong phạm vi ${nearby} (${round(row.nearby_location_distance_m)} m)`
      : "";
    if (assigned) {
      const distance = row.flag_source === "check_out" ? row.check_out_distance_m : row.check_in_distance_m;
      return `Ngoài phạm vi ${assigned} được phân công (${round(distance)} m)${nearbyText}`;
    }
    if (row.flag_source === "check_out") return `Ra ca ngoài xưởng (${round(row.check_out_distance_m)} m)`;
    if (row.flag_source === "both") {
      return `Vào/ra ca ngoài xưởng (${round(Math.max(Number(row.check_in_distance_m ?? 0), Number(row.check_out_distance_m ?? 0)))} m)`;
    }
    return `Vào ca ngoài xưởng (${round(row.check_in_distance_m)} m)`;
  }

  return "Trong xưởng";
}
