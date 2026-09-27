# So sánh ảnh GĐ7d – giao diện giám đốc

Ảnh chụp viewport 390px, sáng/tối. Đối chiếu theo `docs/design/crv_ui_v1.png` mục 3 và `DESIGN_NOTES.md`; dữ liệu mock dùng đúng 7 mặt hàng và tổng 990 túi / 1.284,0 kg.

| Màn | Ảnh sáng | Ảnh tối | Ghi chú |
|---|---|---|---|
| Báo cáo – Ngày | [light](01_bao_cao_ngay_light.png) | [dark](01_bao_cao_ngay_dark.png) | Có 1 điểm dữ liệu nên ẩn biểu đồ và hiện hướng dẫn chọn Tuần/Tháng. |
| Báo cáo – Tuần | [light](02_bao_cao_tuan_light.png) | [dark](02_bao_cao_tuan_dark.png) | Có biểu đồ SVG giờ công + lương, bộ lọc và 3 nhóm lương Đã trả/Tạm tính/Tổng. |
| Báo cáo – Tháng | [light](03_bao_cao_thang_light.png) | [dark](03_bao_cao_thang_dark.png) | Nhãn kỳ dạng Tháng MM/YYYY, không cho đi tới kỳ tương lai. |
| Báo cáo – đang lọc nhân viên | [light](04_bao_cao_loc_nhan_vien_light.png) | [dark](04_bao_cao_loc_nhan_vien_dark.png) | Chip NV001 · Nguyễn Văn A. |
| Bộ lọc nhân viên | [light](05_chon_nhan_vien_light.png) | [dark](05_chon_nhan_vien_dark.png) | Có tìm theo tên/mã và lựa chọn Tất cả nhân viên. |
| Báo cáo – không có dữ liệu | [light](06_bao_cao_trong_light.png) | [dark](06_bao_cao_trong_dark.png) | Các thẻ hiển thị 0, trạng thái không lỗi. |
| Cần xử lý (giám đốc) | [light](07_can_xu_ly_light.png) | [dark](07_can_xu_ly_dark.png) | Tái sử dụng nguyên ReviewScreen của GĐ7c. |
| Duyệt lương (giám đốc) | [light](08_duyet_luong_light.png) | [dark](08_duyet_luong_dark.png) | Tái sử dụng PayrollScreen, gồm chọn tất cả và sửa phiên. |
| Chi tiết lương (giám đốc) | [light](09_chi_tiet_luong_light.png) | [dark](09_chi_tiet_luong_dark.png) | Không có nút quản lý nhân viên/đơn giá/link mời. |

Kiểm tra kỹ thuật:

- `npm run test:overflow`: 148 kịch bản ở 360px/390px, sáng/tối.
- Báo cáo ngày/tuần/tháng/lọc nhân viên được chụp fullPage; biểu đồ tuần có đủ 7 cột (kể cả ngày 0 dữ liệu), nhãn trục Giờ/Lương và chú thích.
- Tab bar dưới dùng nền đặc theo theme, không để nội dung phía sau lộ qua.
- Production bundle không import dữ liệu mock khi build production.
- Không thêm thư viện biểu đồ; biểu đồ là SVG tự viết.
