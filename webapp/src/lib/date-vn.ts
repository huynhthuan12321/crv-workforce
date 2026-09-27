const TZ = "Asia/Ho_Chi_Minh";

export function vnDate(value: Date | string | number = new Date()): Date {
  const date = value instanceof Date ? value : new Date(value);
  return new Date(date.toLocaleString("en-US", {timeZone: TZ}));
}

export function todayVN(now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function fmtDate(value: Date | string | number, options: Intl.DateTimeFormatOptions = {}): string {
  const formatterOptions: Intl.DateTimeFormatOptions = {
    timeZone: TZ,
    day: "2-digit",
    month: "2-digit",
    ...options,
  };
  const hasCustomParts = Object.keys(options).some((key) => !["timeZone", "day", "month"].includes(key));
  if (hasCustomParts) return new Intl.DateTimeFormat("vi-VN", formatterOptions).format(new Date(value));
  const parts = new Intl.DateTimeFormat("vi-VN", formatterOptions).formatToParts(new Date(value));
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("day")}/${get("month")}`;
}

export function fmtDateLong(value: Date | string | number): string {
  const raw = new Intl.DateTimeFormat("vi-VN", {
    timeZone: TZ,
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

export function fmtTime(value: Date | string | number | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function fmtDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest}p`;
  if (!rest) return `${hours}h`;
  return `${hours}h ${rest}p`;
}

export function fmtClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((part) => String(part).padStart(2, "0")).join(":");
}

export function fmtCountdown(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function isAfterCheckinCutoff(now: Date, cutoffHour = 18): boolean {
  const vn = vnDate(now);
  return vn.getHours() >= cutoffHour;
}

export function appNow(): Date {
  if (import.meta.env.DEV && import.meta.env.VITE_MOCK === "1") {
    const scenario = new URLSearchParams(window.location.search).get("scenario");
    if (scenario === "after_cutoff") return new Date("2024-04-24T18:01:00+07:00");
    if (scenario === "output_locked") return new Date("2024-04-24T11:46:00+07:00");
    return new Date("2024-04-24T09:40:15+07:00");
  }
  return new Date();
}
