# CRV Workforce – Module Chấm công V1

Dự án Telegram Mini App nội bộ cho xưởng Cờ Rếp Việt: nhân viên vào/ra ca, khai sản lượng; quản lý/giám đốc xử lý phiên bất thường và duyệt lương theo ngày; dữ liệu gốc nằm trong PostgreSQL, Lark chỉ là bản sao báo cáo.

## Quy tắc bắt buộc

a) Mọi quy tắc nghiệp vụ phải khớp `docs/SPEC.md`. Nếu thấy SPEC mâu thuẫn hoặc thiếu, DỪNG LẠI và hỏi, không tự quyết.

b) Mọi mốc thời gian lấy từ server, múi giờ `Asia/Ho_Chi_Minh`, lưu DB bằng `timestamptz`.

c) Mọi quy tắc nghiệp vụ nằm ở backend (`source/services/`). Frontend không tự tính lương, không tự quyết chặn/cho phép.

d) Tiền lưu bằng số nguyên VND (không dùng float). Giá trị tiền thô theo phiên có thể dùng `Decimal/Numeric` để tính chính xác trước khi làm tròn.

e) Mọi thay đổi giờ công ghi `audit_log`.

f) Viết test cho mọi service nghiệp vụ.

g) Mọi thay đổi nghiệp vụ cần đồng bộ Lark phải ghi `sync_outbox` trong CÙNG transaction.

h) Không ghi tọa độ GPS, token, `initData`, số điện thoại vào log.

i) Scheduler chỉ chạy trong service `bot`.

## Lệnh thường dùng

```powershell
# Cài dependencies Python
python -m pip install -e ".[dev]"

# Chạy API local
python -m uvicorn source.api_main:app --host 0.0.0.0 --port 8000 --reload

# Chạy bot local
python -m source.bot_main

# Chạy frontend
cd webapp
npm install
npm run dev

# Kiểm tra cú pháp / test
python -m compileall -q source migrations scripts tests
python -m pytest

# Docker compose
docker compose config --quiet
docker compose up --build

# Alembic migration
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
```
