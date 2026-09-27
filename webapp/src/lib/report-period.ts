import {todayVN} from "./date-vn";

export type ReportPeriod = "day" | "week" | "month";

export function periodBounds(period: ReportPeriod, value: string): {from: string; to: string} {
  const date = new Date(`${value}T12:00:00+07:00`);
  if (period === "day") return {from: value, to: value};
  if (period === "week") {
    const monday = new Date(date);
    const day = monday.getDay() || 7;
    monday.setDate(monday.getDate() - day + 1);
    const sunday = new Date(monday);
    sunday.setDate(sunday.getDate() + 6);
    return {from: todayVN(monday), to: todayVN(sunday)};
  }
  const first = new Date(date.getFullYear(), date.getMonth(), 1, 12);
  const last = new Date(date.getFullYear(), date.getMonth() + 1, 0, 12);
  return {from: todayVN(first), to: todayVN(last)};
}

export function shiftPeriod(period: ReportPeriod, value: string, offset: number): string {
  const date = new Date(`${value}T12:00:00+07:00`);
  if (period === "day") date.setDate(date.getDate() + offset);
  if (period === "week") date.setDate(date.getDate() + offset * 7);
  if (period === "month") date.setMonth(date.getMonth() + offset);
  return todayVN(date);
}

export function periodLabel(period: ReportPeriod, value: string): string {
  const {from, to} = periodBounds(period, value);
  if (period === "day") return new Intl.DateTimeFormat("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", weekday: "long", day: "2-digit", month: "2-digit", year: "numeric"}).format(new Date(`${value}T12:00:00+07:00`));
  if (period === "month") return `Tháng ${value.slice(5, 7)}/${value.slice(0, 4)}`;
  return `${from.slice(8, 10)}/${from.slice(5, 7)} – ${to.slice(8, 10)}/${to.slice(5, 7)}/${to.slice(0, 4)}`;
}
