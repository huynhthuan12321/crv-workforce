# 2.21 Thông báo và tin nhắn riêng — đối chiếu triển khai

| Mục | Code | Màn hình / bot | Test |
|---|---|---|---|
| 0. Phạm vi và quy tắc | `docs/SPEC.md` mục 2.21; `0462d42` | Quyền theo vai trò trong Mini App và bot | `tests/integration/test_permissions.py` |
| 1. Gửi thông báo | `source/services/messaging.py`, `source/api/routes/messaging.py`, `source/workers.py` | Tab Tin nhắn → Thông báo; nút `📢 Gửi thông báo`; tin HTML có `Đã nhận` | `test_2_21_announcement_never_leaks_employee_to_employee`, `test_2_21_manager_audience_restricted_and_skips_unlinked_locked`, `test_2_21_location_audience_only_sends_assigned_employees`, `test_2_21_text_limit_rejects_over_2000` |
| 2. Trả lời và nhắn riêng | `source/services/messaging.py`, `source/telegram/handlers/user/messages.py`, `callbacks.py` | Reply thông báo; `💬 Nhắn quản lý`; hội thoại Hộp thư | `tests/unit/test_messaging.py`, `tests/unit/test_workers.py` |
| 3. Quyền xem hội thoại | `source/api/routes/messaging.py` (`list_conversations`, `conversation_messages`) | Quản lý chỉ kênh Quản lý; giám đốc xem kênh Quản lý chỉ đọc và kênh Giám đốc | `tests/integration/test_permissions.py` |
| 4. Đã nhận idempotent | `MessagingService.acknowledge`, callback `announcement_ack` | Nút đổi thành `✅ Đã nhận lúc HH:MM` | `test_2_21_acknowledge_idempotent` |
| 5. Lưu trữ và outbox | `migrations/versions/0007_notifications_messages.py`, ORM workforce, `notification_outbox` | Không lộ chi tiết lưu trữ; worker gửi chống trùng theo `dedupe_key` | migration check; worker notification tests |
| 6. Tab Tin nhắn | `webapp/src/features/messages/MessagesScreen.tsx`, `AppShell.tsx`, mock/screenshot scripts | Thông báo / Hộp thư / Soạn thông báo, readonly manager channel cho giám đốc | Vitest frontend; `npm run test:overflow`; `npm run screenshots:gd-thong-bao` |
| 7. Bảng quyền | `tests/integration/test_permissions.py` và route dependencies | Tab chỉ xuất hiện đúng vai trò; bot keyboard theo vai trò | permission matrix |

## Ghi chú kiểm chứng

- Nội dung tin được escape tại `source/telegram/messages.py`; worker gửi `parse_mode="HTML"` khi Bot hỗ trợ tham số.
- Nếu Telegram trả lỗi `can't parse entities`, worker ghi `WARNING` chỉ gồm loại tin và id, gửi lại ngay bản chữ thường, đánh dấu `sent` và không retry.
- Tin ảnh/tệp/sticker bị từ chối với thông báo chỉ hỗ trợ tin nhắn chữ; giới hạn 2.000 ký tự.
- Người chưa liên kết hoặc bị khóa không nhận announcement; `/start` và tin khóa tài khoản đều gỡ ReplyKeyboard cũ.
