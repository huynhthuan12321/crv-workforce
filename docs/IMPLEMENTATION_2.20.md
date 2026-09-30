# SPEC 2.20 – Danh mục sản phẩm: kế hoạch triển khai

## Bước 0 – rà soát mô hình cũ

Những điểm code hiện đang dùng danh mục sản phẩm cũ và phải thay:

| Nhóm | File | Hiện trạng | Kế hoạch thay theo 2.20 |
|---|---|---|---|
| ORM | `source/database/models/workforce.py` | `products.kg_per_bag`; `output_items.bags`; `output_items.kg` | Migration 0008 đổi sang `kg_per_unit`, `quantity`, `total_kg` generated và thêm snapshot sản phẩm |
| Schema API | `source/schemas/workforce.py` | output form/submit/report còn trường `bags`, `kg_per_bag`, `kg` | Đổi sang `quantity`, `unit_*_snapshot`, `kg_per_unit_snapshot`, `total_kg`, trạng thái output |
| Form sản lượng | `source/services/workforce.py` (`OutputService.form`) | Đọc `products` hiện tại khi mở form | Form chỉ đọc `output_items` đã chốt lúc phiên đóng |
| Gửi sản lượng | `source/services/workforce.py` (`OutputService.submit`) | Tạo mới `output_items` theo `ProductOrm` hiện tại; tính `kg = bags × kg_per_bag` | Chỉ cập nhật `quantity` các dòng đã chốt; sản phẩm ngoài phiên trả `PRODUCT_NOT_IN_SESSION`; `status=submitted` |
| Đóng phiên | `source/services/workforce.py` checkout/close forgotten | Chưa chốt catalog khi phiên đóng | Khi đóng phiên tạo `output_log` pending/opened_at/locked_at và tạo `output_items` snapshot cho sản phẩm áp dụng |
| Báo cáo sản phẩm | `source/services/workforce.py` report methods | Sum `OutputItemOrm.bags` và `OutputItemOrm.kg`; dựa danh mục hiện tại | Chỉ cộng `output_logs.status='submitted'`, gom theo `product_code_snapshot`, cảnh báo nhiều quy cách, đếm `locked_unsubmitted` |
| Lark outbox | `source/services/workforce.py` `output_submitted` | Payload schema v2 dùng số lượng/kg cũ | Chỉ phát khi submitted, `schema_version=3`, gửi snapshot từng dòng |
| Test backend | `tests/integration/*`, `tests/unit/*` | Fixture tạo `kg_per_bag`, `bags`, `kg` | Cập nhật fixture và thêm test nghiệm thu 2.20 |
| Frontend types | `webapp/src/types/api.ts` | Type `bags`, `kg_per_bag`, `kg` | Đổi/ mở rộng type snapshot, trạng thái output, catalog API |
| Frontend output form | `webapp/src/features/outputs/OutputsScreen.tsx` | Tính kg từ `kg_per_bag`, label hard-code `túi` | Dùng snapshot và `unit_label_snapshot`; trạng thái đã xác nhận / đã khóa – chưa khai |
| Frontend report | `webapp/src/features/director/ReportsScreen.tsx` | Bảng cột `Túi`, cộng `bags/kg` | Hiển thị theo đơn vị snapshot, cảnh báo nhiều quy cách, phiên chưa khai |
| Frontend format | `webapp/src/lib/format.ts` | Helper `totalKg` dùng `kg_per_bag` | Dùng `total_kg` snapshot hoặc quantity × kg_per_unit_snapshot |
| Mock | `webapp/src/mock/scenarios.ts`, `webapp/src/mock/mock-api.ts` | Hard-code 7 mặt hàng với `bags/kg_per_bag` | Thêm catalog all/restricted/ngừng SX/đổi quy cách/chưa khai/không áp dụng |
| Docs Lark | `docs/LARK_SYNC.md` | `output_submitted` schema cũ | Cập nhật schema_version 3 và idempotency giữ `event_id` |

## Bảng đối chiếu triển khai

| Mục 2.20 | Code | Màn hình | Test |
|---|---|---|---|
| 0. Quy tắc gốc | Đang triển khai | Đang triển khai | Đang triển khai |
| 1. Mô hình dữ liệu | Đang triển khai `0008_product_catalog` | – | Đang triển khai |
| 2. Chốt danh mục cho phiên | Đang triển khai | Form Sản lượng | Đang triển khai |
| 3. Thao tác danh mục | Đang triển khai | Quản lý/Giám đốc · Sản phẩm | Đang triển khai |
| 4. Giao thức khóa | Đang triển khai | – | Đang triển khai |
| 5. Báo cáo và hiển thị | Đang triển khai | Báo cáo, Lịch sử, Chi tiết lương | Đang triển khai |
| 6. Lark / outbox | Đang triển khai | – | Đang triển khai |
| 7. Quyền và giao diện | Đang triển khai | Quản lý, Báo cáo Giám đốc | Đang triển khai |
| 8. Migration 0008 | Đang triển khai | – | Đang triển khai |
| 9. Test nghiệm thu | Đang triển khai | – | Đang triển khai |
