# Tin bot – kiểm chứng

Môi trường hiện tại không có thông tin bot test/chat để chụp Telegram thật. Vì vậy các ảnh tin nhắn thật được đánh dấu `NOT VERIFIED`; nội dung và bàn phím đã được kiểm tra bằng unit/integration test.

| Mẫu | Trạng thái | Kiểm tra tự động |
|---|---|---|
| Duyệt lương | NOT VERIFIED | `tests/unit/test_workers.py` |
| Đợt 0đ | NOT VERIFIED | `tests/unit/test_messages.py` |
| Nhắc ra ca | NOT VERIFIED | `tests/unit/test_workers.py` |
| Phiên quên ra ca | NOT VERIFIED | `tests/unit/test_workers.py` |
| Đóng phiên quên | NOT VERIFIED | `tests/unit/test_workers.py` |
| Đổi đơn giá | NOT VERIFIED | `tests/unit/test_messages.py` |
| Hẹn đơn giá | NOT VERIFIED | `tests/unit/test_messages.py` |
| Hủy đơn giá | NOT VERIFIED | `tests/unit/test_messages.py` |
| Bàn phím nhân viên/quản lý/giám đốc | NOT VERIFIED | `source/telegram/keyboards/reply.py` + worker tests |
