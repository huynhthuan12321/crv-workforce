## PHẦN 1 – KIẾN TRÚC ĐÃ CHỐT

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Khung dự án | `MrConsoleka/aiogram-miniapp-template` | Bot + API + Webapp + Migration + nginx trong 1 bộ Docker |
| Service `bot` | aiogram 3 (Python), tiến trình riêng | Polling, mở Mini App, gửi mọi thông báo, scheduler (18:00, 18:30, 00:05, quét khi khởi động), gửi outbox sang n8n. **Chỉ chạy 1 instance** |
| Service `api` | FastAPI (Python), tiến trình riêng | Toàn bộ quy tắc nghiệp vụ, đăng nhập bằng initData, cấp token phiên. Có thể chạy nhiều worker |
| Database | PostgreSQL | **Nguồn dữ liệu gốc duy nhất** |
| Migration | Alembic | Tạo/cập nhật bảng |
| Frontend | React (thư mục `webapp/` của template) | 3 giao diện theo vai trò |
| Tham khảo UI | `Telegram-Mini-Apps/reactjs-template` | Chỉ tham khảo cách dùng theme, viewport, BackButton, safe area |
| Đồng bộ báo cáo | n8n → Lark Base | **Chỉ** nhận dữ liệu một chiều để làm báo cáo |
| Reverse proxy | nginx (có sẵn trong template) + HTTPS | Phục vụ webapp và API trên 1 tên miền |
| Cấu hình | Theo quy ước biến môi trường của template (dạng `NHOM__TEN`) | Chỉ một bộ cấu hình duy nhất |

> `bot` và `api` dùng chung một codebase, chung database, nhưng là **hai service Docker riêng**. Scheduler đặt trong `bot` để bảo đảm chỉ một tiến trình chạy lịch, không gửi trùng thông báo khi `api` chạy nhiều worker.

**Luồng dữ liệu:**

```
Nhân viên / Quản lý / Giám đốc
        │ (mở từ bot)
        ▼
  Telegram Mini App (React)
        │  gửi kèm initData ở mọi request
        ▼
  FastAPI ──── kiểm tra initData ──── áp quy tắc nghiệp vụ
        │
        ▼
   PostgreSQL (nguồn gốc)
        │
        ├──► Service bot: nhắc 18:00, báo 18:30, quét phiên tồn,
        │    báo lương đã duyệt, nhắc khai sản lượng
        │
        └──► Outbox (ghi cùng transaction) ──► service bot gửi
             ──► webhook n8n ──► Lark Base (bản sao báo cáo)
```

**Nguyên tắc bất di bất dịch:**
- Mọi quy tắc nghiệp vụ nằm ở **backend**. Frontend chỉ hiển thị và gửi yêu cầu.
- Mọi mốc thời gian lấy từ **đồng hồ server**, không bao giờ lấy từ điện thoại.
- Lark **không bao giờ** là nơi ghi dữ liệu gốc.

**Ghi chú vận hành thông báo:** hệ thống không dùng bảng `notification_log` riêng; chống gửi trùng bằng `notification_outbox.dedupe_key` có unique constraint.

---

## Bảng ánh xạ biến môi trường thực tế

| Nhóm trong source/config/config_reader.py | Biến thực tế | Trong Phụ lục A | Ghi chú |
|---|---|---|---|
| `AppSettings` | `APP__ENV`, `APP__DOMAIN` | Có | Khớp Phụ lục A. |
| `TelegramSettings` | `TG__BOT_TOKEN`, `TG__BOT_USERNAME`, `TG__MINIAPP_SHORT_NAME` | Có | Khớp Phụ lục A. |
| `TelegramSettings` | `TG__ADMIN_IDS`, `TG__WEBHOOK_USE`, `TG__WEBHOOK_PATH` | Không | Biến kế thừa/mở rộng từ template. |
| `WebhookSettings` | `WEBHOOK__URL`, `WEBHOOK__HOST`, `WEBHOOK__PORT`, `WEBHOOK__SECRET` | Không | Biến template cho webhook/bot; V1 dùng polling nhưng vẫn giữ cấu hình. |
| `DatabaseSettings` | `DB__HOST`, `DB__PORT`, `DB__USER`, `DB__PASSWORD`, `DB__NAME` | Có | Khớp Phụ lục A. |
| `RedisSettings` | `REDIS__HOST`, `REDIS__PORT` | Có | Khớp Phụ lục A. |
| `RedisSettings` | `REDIS__USER`, `REDIS__PASSWORD`, `REDIS__DB` | Không | Mở rộng thực tế để hỗ trợ Redis có xác thực/chọn DB. |
| `ApiSettings` | `API__HOST`, `API__PORT`, `API__DEBUG` | Không | Mở rộng thực tế cho FastAPI service. |
| `WebAppSettings` | `WEBAPP__URL` | Có | Khớp Phụ lục A. |
| `AuthSettings` | `AUTH__INITDATA_MAX_AGE_SECONDS`, `AUTH__SESSION_SECRET`, `AUTH__DEV_BYPASS` | Có | Khớp Phụ lục A. |
| `WorkshopSettings` | `WORKSHOP__LAT`, `WORKSHOP__LNG`, `WORKSHOP__RADIUS_M` | Có | Khớp Phụ lục A. |
| `RuleSettings` | `RULES__GPS_MAX_ACCURACY_M`, `RULES__CHECKIN_CUTOFF`, `RULES__REMINDER_AT`, `RULES__ESCALATE_AT`, `RULES__SWEEP_AT`, `RULES__OUTPUT_EDIT_MINUTES`, `RULES__PAY_ROUND_UNIT`, `RULES__INVITE_EXPIRE_DAYS` | Có | Khớp Phụ lục A. |
| `LarkSettings` | `LARK__SYNC_WEBHOOK_URL`, `LARK__SYNC_SECRET` | Có | Khớp Phụ lục A. |
| `AlertSettings` | `ALERT__ADMIN_CHAT_ID` | Có | Khớp Phụ lục A. |
| `SeedSettings` | `SEED__MANAGER_NAME`, `SEED__DIRECTOR_NAME` | Có | Khớp Phụ lục A. |
| Hệ thống container | `TZ` | Có | Không thuộc Pydantic settings; đặt cho container/OS runtime. |
 
---

## Endpoint thực tế so với prompt

| Nghiệp vụ | Prompt gốc | Endpoint thực tế | Ghi chú |
|---|---|---|---|
| Sửa giờ phiên | `PUT /api/sessions/{id}` | `PATCH /api/review/{id}` | Giữ endpoint hiện có để không phá client/API đã triển khai. Chỉ quản lý/giám đốc được gọi. |
