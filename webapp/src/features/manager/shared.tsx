import {useEffect} from "react";
import {fmtTime} from "../../lib/date-vn";
import type {PayrollSummary, ReviewItem} from "../../types/api";

export function useBackButton(active: boolean, onBack: () => void) {
  useEffect(() => {
    const back = window.Telegram?.WebApp?.BackButton;
    if (!back) return;
    if (!active) {
      back.hide();
      return;
    }
    back.show();
    back.onClick(onBack);
    return () => {
      back.offClick(onBack);
      back.hide();
    };
  }, [active, onBack]);
}

export function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Không thể tải dữ liệu. Vui lòng thử lại.";
}

export function pendingText(reason: PayrollSummary["pending_reason"]) {
  if (reason === "open_session") return "Có phiên đang mở, sẽ vào đợt sau";
  if (reason === "unreviewed_gps") return "Có cờ GPS chưa xử lý";
  if (reason === "forgot_checkout") return "Có phiên quên ra ca";
  return "Sẵn sàng duyệt";
}

export function reviewType(row: ReviewItem): "gps" | "forgot" {
  return row.status === "needs_review" || row.review_reason === "forgot_checkout" ? "forgot" : "gps";
}

export function sessionTime(row: {check_in_at: string; check_out_at: string | null; minutes: number | null}) {
  return `${fmtTime(row.check_in_at)}–${fmtTime(row.check_out_at)} · ${row.minutes ?? "—"} phút`;
}
