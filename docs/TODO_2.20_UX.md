# TODO UX 2.20 – Danh mục sản phẩm

## UX-2.20-01 – Giám đốc khó thấy màn Sản phẩm trên điện thoại

Ngày ghi nhận: 2026-09-30

Trạng thái: ghi nhận, fix sau.

Hiện trạng:

- Nhánh `gd-san-pham` đã có code và DB cho danh mục sản phẩm.
- DB đã migrate tới `0008_product_catalog`.
- Bảng `products` đã có 7 sản phẩm mặc định.
- Webapp bundle đã có `/api/catalog/products`.
- Với role giám đốc, màn quản lý sản phẩm hiện nằm trong `Báo cáo` qua nút nhỏ `Danh mục → Sản phẩm` trên header.
- Khi thử thật trên điện thoại, người dùng dễ hiểu nhầm là phần sản phẩm chưa hiển thị vì nút này không đủ nổi bật.

Hướng sửa đề xuất:

- Trong màn `Báo cáo`, thêm một card/menu riêng tên `Danh mục`.
- Hiển thị 2 nút lớn, dễ bấm:
  - `Kho`
  - `Sản phẩm`
- Hoặc đưa `Sản phẩm` vào header/menu rõ ràng hơn, tránh chỉ đặt trong action nhỏ của tiêu đề.

Mức độ: P2 – UX chưa rõ, không chặn core backend/migration/report.

File liên quan:

- `webapp/src/features/director/ReportsScreen.tsx`
- `webapp/src/features/manager/employees/EmployeesScreen.tsx`

