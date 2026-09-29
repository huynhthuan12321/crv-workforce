from source.telegram.messages import (
    batch_paid,
    checkout_reminder,
    consent_withdrawn,
    forgot_sessions,
    rate_changed,
    rate_scheduled,
)


def test_batch_paid_uses_html_sections_and_zero_note():
    text = batch_paid({"date": "24/04", "batch_no": 1, "amount": 0, "paid_total": 162000})
    assert "<b>💰 ĐÃ DUYỆT LƯƠNG</b>" in text
    assert "162.000đ" in text
    assert "(đã được làm tròn ở đợt trước)" in text


def test_checkout_reminder_escapes_location_and_has_snapshot():
    text = checkout_reminder({"check_in": "08:12", "location_name": "Kho <A>", "minutes": 208})
    assert "Kho &lt;A&gt;" in text
    assert "⏱ Đã làm: <b>208 phút</b>" in text


def test_forgot_sessions_is_limited_and_escapes_user_data():
    sessions = [
        {"employee_code": "NV001", "employee_name": "A <B>", "check_in": "08:00", "location_name": "Kho 1"}
        for _ in range(17)
    ]
    text = forgot_sessions({"sessions": sessions})
    assert "A &lt;B&gt;" in text
    assert "… và 2 phiên khác" in text


def test_rate_messages_do_not_include_internal_reason():
    text = rate_changed({"old_hourly_rate": 30000, "hourly_rate": 40000, "reason": "nội bộ"})
    assert "30.000đ/giờ" in text
    assert "40.000đ/giờ" in text
    assert "nội bộ" not in text
    scheduled = rate_scheduled({"current_hourly_rate": 30000, "hourly_rate": 40000, "effective_from": "01/11/2026"})
    assert "01/11/2026" in scheduled


def test_consent_withdrawn_escapes_name():
    assert "&lt;Nhân viên&gt;" in consent_withdrawn({"employee_code": "NV1", "employee_name": "<Nhân viên>"})
