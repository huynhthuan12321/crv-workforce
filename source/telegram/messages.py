from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any, Mapping

from source.utils.formatting import fmt_date_vn, fmt_money_vn, fmt_time_vn


def _text(value: Any) -> str:
    return escape("" if value is None else str(value))


def _money(value: Any) -> str:
    return _text(fmt_money_vn(value))


def _date(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return _text(fmt_date_vn(parsed))
        except ValueError:
            try:
                return _text(fmt_date_vn(date.fromisoformat(value)))
            except ValueError:
                return _text(value)
    return _text(fmt_date_vn(value))


def _time(value: Any) -> str:
    if isinstance(value, str):
        return _text(value)
    return _text(fmt_time_vn(value))


def batch_paid(payload: Mapping[str, Any]) -> str:
    amount = int(payload.get("amount", 0) or 0)
    rounded_note = "\n(đã được làm tròn ở đợt trước)" if amount == 0 else ""
    return (
        "<b>💰 ĐÃ DUYỆT LƯƠNG</b>\n\n"
        f"📅 Ngày: <b>{_date(payload.get('date'))}</b>\n"
        f"🧾 Đợt: <b>{_text(payload.get('batch_no'))}</b>\n"
        f"💵 Số tiền đợt này: <b>{_money(amount)}</b>\n"
        f"✅ Tổng đã nhận hôm nay: <b>{_money(payload.get('paid_total', 0))}</b>"
        f"{rounded_note}"
    )


def checkout_reminder(payload: Mapping[str, Any]) -> str:
    location = payload.get("location_name") or payload.get("location_code") or "Chưa xác định"
    minutes = payload.get("minutes")
    duration = f"{minutes} phút" if minutes is not None else "đang tính"
    return (
        "<b>⏰ NHẮC RA CA</b>\n\n"
        f"🕐 Vào ca lúc: <b>{_time(payload.get('check_in'))}</b>\n"
        f"📍 Kho: <b>{_text(location)}</b>\n"
        f"⏱ Đã làm: <b>{_text(duration)}</b>\n\n"
        "Nếu đã nghỉ, vui lòng bấm Ra ca."
    )


def forgot_sessions(payload: Mapping[str, Any]) -> str:
    sessions = list(payload.get("sessions") or [])
    lines = []
    for item in sessions[:15]:
        employee = item.get("employee_name") or item.get("employee_code") or item.get("employee_id")
        location = item.get("location_name") or item.get("location_code") or "Chưa xác định"
        lines.append(
            f"• {_text(item.get('employee_code', ''))} {_text(employee)} – "
            f"vào {_time(item.get('check_in'))} · {_text(location)}"
        )
    remaining = max(0, len(sessions) - 15)
    if remaining:
        lines.append(f"… và {remaining} phiên khác")
    body = "\n".join(lines) or "Không có phiên chi tiết."
    return f"<b>⚠️ PHIÊN CHƯA RA CA · {len(sessions)} người</b>\n\n{body}"


def forgot_session_closed(payload: Mapping[str, Any]) -> str:
    entered = payload.get("check_in") or payload.get("check_in_at")
    exited = payload.get("check_out") or payload.get("check_out_at") or payload.get("closed_time")
    date_value = payload.get("work_date")
    date_line = _date(date_value)
    time_line = f"{_time(entered)}–{_time(exited)}" if entered else _time(exited)
    actor = payload.get("closed_by_name") or payload.get("processor_name") or "Quản lý"
    return (
        "<b>📝 PHIÊN ĐÃ ĐƯỢC ĐÓNG</b>\n\n"
        f"📅 Ngày: <b>{date_line} · {time_line}</b>\n"
        f"👤 Người xử lý: <b>{_text(actor)}</b>\n\n"
        "⏳ Còn 10 phút để khai sản lượng."
    )


def consent_withdrawn(payload: Mapping[str, Any]) -> str:
    code = payload.get("employee_code") or payload.get("employee_id") or ""
    name = payload.get("employee_name") or ""
    return f"<b>🔒 NHÂN VIÊN RÚT ĐỒNG Ý VỊ TRÍ</b>\n\n👤 {_text(code)} {_text(name)}"


def rate_changed(payload: Mapping[str, Any]) -> str:
    old = _money(payload.get("old_hourly_rate", payload.get("current_hourly_rate", 0)))
    new = _money(payload.get("hourly_rate", 0))
    return (
        "<b>💵 CẬP NHẬT ĐƠN GIÁ</b>\n\n"
        f"Giá cũ: <s>{old}/giờ</s>\n"
        f"Giá mới: <b>{new}/giờ</b>\n"
        "Áp dụng: từ lần vào ca tiếp theo."
    )


def rate_scheduled(payload: Mapping[str, Any]) -> str:
    current = _money(payload.get("current_hourly_rate", 0))
    new = _money(payload.get("hourly_rate", 0))
    return (
        "<b>💵 ĐƠN GIÁ SẮP THAY ĐỔI</b>\n\n"
        f"Giá hiện tại: <b>{current}/giờ</b>\n"
        f"Giá mới: <b>{new}/giờ</b>\n"
        f"Có hiệu lực từ {_date(payload.get('effective_from'))}."
    )


def rate_cancelled(payload: Mapping[str, Any]) -> str:
    current = _money(payload.get("current_hourly_rate", 0))
    return (
        "<b>💵 HỦY THAY ĐỔI ĐƠN GIÁ</b>\n\n"
        f"Thay đổi dự kiến từ {_date(payload.get('effective_from'))} đã được hủy.\n"
        f"Đơn giá hiện tại: <b>{current}/giờ</b>."
    )


def account_locked(payload: Mapping[str, Any]) -> str:
    return "Tài khoản đã bị khóa."


MESSAGE_BUILDERS = {
    "batch_paid": batch_paid,
    "checkout_reminder": checkout_reminder,
    "forgot_sessions": forgot_sessions,
    "forgot_session_closed": forgot_session_closed,
    "consent_withdrawn": consent_withdrawn,
    "rate_changed": rate_changed,
    "rate_scheduled": rate_scheduled,
    "rate_cancelled": rate_cancelled,
    "account_locked": account_locked,
}


def render_notification(notification_type: str, payload: Mapping[str, Any]) -> str:
    builder = MESSAGE_BUILDERS.get(notification_type)
    if builder:
        return builder(payload)
    return _text(payload.get("text") or "Thông báo từ CRV Workforce")
