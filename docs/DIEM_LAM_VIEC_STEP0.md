# BƯỚC 0 – Điểm làm việc (Kho)

Ngày rà soát: 2026-09-28.

## Kết luận đọc SPEC 2.17

- Đã đọc `CLAUDE.md`, `docs/SPEC.md`, `docs/LARK_SYNC.md`, `docs/design/DESIGN_NOTES.md` và `docs/spec/2.17_diem_lam_viec.md`.
- Không phát hiện mâu thuẫn nội bộ trong `docs/spec/2.17_diem_lam_viec.md`.
- Có lệch với SPEC cũ ở câu "1 điểm xưởng"; đã cập nhật `docs/SPEC.md` để dùng mô hình nhiều điểm làm việc, giao diện gọi là "Kho".
- `docs/spec/2.17_diem_lam_viec.md` vẫn là nguồn quy tắc đóng băng cho tính năng này. Nếu cần đổi quy tắc, sửa file đó trước.

## Các chỗ đang đọc `settings.workshop.*`

Kết quả rà bằng:

```powershell
rg -n "settings\.workshop|WORKSHOP__|workshop\.|Workshop|workshop" source tests scripts migrations docs webapp -g "!*node_modules*"
```

| File | Dòng hiện tại | Đang dùng | Kế hoạch thay thế theo SPEC 2.17 |
|---|---:|---|---|
| `source/services/workforce.py` | 39 | `_gps_flags()` so `distance > settings.workshop.radius_m` | Đổi helper nhận `radius_m_snapshot`/bán kính kho được phân công. Check-in dùng bán kính `work_locations.radius_m`; check-out dùng `work_sessions.location_radius_m_snapshot`. |
| `source/services/workforce.py` | 76 | `_flag_source()` so `check_in_distance_m` với `settings.workshop.radius_m` | Đổi helper nhận bán kính snapshot của phiên để suy `flag_source`. Migration 0004 backfill dùng bán kính cũ từ WORKSHOP__* một lần. Runtime không đọc settings workshop. |
| `source/services/workforce.py` | 80 | `_flag_source()` so `check_out_distance_m` với `settings.workshop.radius_m` | Như trên: dùng `location_radius_m_snapshot` của phiên. |
| `source/services/workforce.py` | 280 | Check-in tính Haversine tới `settings.workshop.lat/lng` | Thay bằng: khóa employee `FOR UPDATE` → đọc phân công hiện hành → khóa `work_locations FOR SHARE` → tính khoảng cách tới kho được phân công → snapshot kho vào `work_sessions`. Đồng thời tìm `nearby_location_*` nếu GPS nằm trong bán kính kho active khác. |
| `source/services/workforce.py` | 303 | Check-out tính Haversine tới `settings.workshop.lat/lng` | Thay bằng tọa độ snapshot của phiên (`location_lat_snapshot`, `location_lng_snapshot`, `location_radius_m_snapshot`), không đọc phân công hiện tại và không đọc settings workshop. |
| `source/config/config_reader.py` | 77 | `WorkshopSettings` khai báo env `WORKSHOP__*` | Giữ tạm để migration/seed lần đầu đọc theo SPEC 2.17 mục 8–9, nhưng runtime service không được phụ thuộc. Sau khi migration ổn có thể chú thích/deprecate trong config. |
| `source/config/config_reader.py` | 121 | `Settings.workshop` | Giữ cho migration/seed/backfill; không dùng trong runtime check-in/check-out. |
| `tests/conftest.py` | 25–27 | Set default `WORKSHOP__LAT/LNG/RADIUS_M` cho test | Giữ để migration/seed/backfill có giá trị mặc định; thêm test 2.17 s8 để xóa WORKSHOP__* khỏi môi trường runtime mà vào ca vẫn chạy. |
| `tests/unit/test_auth/test_auth_workforce.py` | 140–151 | Env `WORKSHOP__LAT/LNG` phục vụ Settings production validation | Cập nhật nếu production validation vẫn yêu cầu WORKSHOP__*. Theo SPEC 2.17 runtime không được phụ thuộc WORKSHOP__*, nên test cần chuyển trọng tâm sang biến bắt buộc khác hoặc chỉ xác nhận migration/seed có fallback. |
| `docs/ARCHITECTURE.md` | 62 | Bảng cấu hình liệt kê `WorkshopSettings` là bắt buộc | Cập nhật ở commit triển khai cấu hình: `WORKSHOP__*` chỉ cho migration/seed lần đầu, không còn bắt buộc runtime. |
| `docs/IMPLEMENTATION.md` | 498 | Liệt kê biến Workshop | Cập nhật/xóa theo thực tế sau triển khai. |

## Nguyên tắc thay thế

1. PostgreSQL là nguồn duy nhất cho điểm làm việc sau migration.
2. Runtime check-in/check-out không đọc `settings.workshop.*`.
3. Snapshot kho trên `work_sessions` là bất biến.
4. Check-out luôn dùng snapshot của phiên, kể cả khi phân công nhân viên đã đổi.
5. Migration 0004 là nơi duy nhất được dùng WORKSHOP__* để tạo `KHO01 – Xưởng chính` và backfill dữ liệu cũ.
