# So sánh ảnh GĐ7c – giao diện quản lý

Ảnh chụp ở viewport 390px, gồm chế độ sáng và tối. Thiết kế đối chiếu: `docs/design/crv_ui_v1.png`, mục 2 “Giao diện quản lý”, cộng thêm màn “Danh sách nhân viên” và “Thiết lập đơn giá giờ” theo `DESIGN_NOTES.md`.

| Màn trong thiết kế / ghi chú | Ảnh sáng | Ảnh tối | Khác biệt còn lại |
|---|---|---|---|
| Đang làm – có nhân viên trong ca | [light](01_dang_lam_light.png) | [dark](01_dang_lam_dark.png) | Đạt bố cục chính; thời lượng dùng dạng `3h 28p` thay đồng hồ chạy từng giây để khớp dữ liệu `/working-now`. |
| Đang làm – danh sách trống | [light](02_dang_lam_trong_light.png) | [dark](02_dang_lam_trong_dark.png) | Đạt; thêm trạng thái rỗng rõ ràng. |
| Cần xử lý – chưa xử lý | [light](03_can_xu_ly_light.png) | [dark](03_can_xu_ly_dark.png) | Đạt; có lọc GPS / quên ra ca, không có bulk checkbox vì SPEC không yêu cầu. |
| Cần xử lý – đã xử lý | [light](04_da_xu_ly_light.png) | [dark](04_da_xu_ly_dark.png) | Đạt; hiển thị người xử lý, giờ xử lý và lý do. |
| Cần xử lý – người khác xử lý trước | [light](05_already_handled_light.png) | [dark](05_already_handled_dark.png) | Đạt; banner “Đã xử lý bởi…” lấy từ lỗi `ALREADY_HANDLED.details`. |
| Duyệt lương – danh sách ngày | [light](06_duyet_luong_light.png) | [dark](06_duyet_luong_dark.png) | Đạt; có chọn tất cả các dòng đủ điều kiện, nút duyệt khóa khi chưa chọn, ngày hiển thị DD/MM/YYYY. |
| Duyệt lương – chi tiết nhân viên | [light](07_chi_tiet_luong_a_light.png) | [dark](07_chi_tiet_luong_a_dark.png) | Đạt; phiên đã trả bị khóa, phiên chờ duyệt có nút sửa. |
| Duyệt lương – sửa phiên | [light](08_sua_phien_light.png) | [dark](08_sua_phien_dark.png) | Đạt; giữ endpoint thực tế `PATCH /api/review/{id}` theo kiến trúc. |
| Duyệt lương – hộp xác nhận | [light](09_hop_xac_nhan_light.png) | [dark](09_hop_xac_nhan_dark.png) | Đạt; mock chọn sẵn Lê Thị B + Phạm Thị D, hiển thị 840 phút và 392.000đ. |
| Duyệt lương – kết quả đã duyệt | [light](10_tong_ket_duyet_light.png) | [dark](10_tong_ket_duyet_dark.png) | Đạt; hiển thị từng đợt tạo ra. |
| Duyệt lương – không có dữ liệu | [light](11_khong_co_du_lieu_light.png) | [dark](11_khong_co_du_lieu_dark.png) | Đạt; trạng thái rỗng không báo lỗi giả. |
| Nhân viên – danh sách | [light](12_danh_sach_nhan_vien_light.png) | [dark](12_danh_sach_nhan_vien_dark.png) | Đạt; có tìm kiếm, lọc trạng thái, chip chưa liên kết / đang trong ca. |
| Nhân viên – thêm nhân viên | [light](13_them_nhan_vien_light.png) | [dark](13_them_nhan_vien_dark.png) | Đạt; link mời hiển thị sau khi tạo thành công ở trạng thái thao tác thật. |
| Nhân viên – chi tiết & đơn giá giờ | [light](14_chi_tiet_don_gia_light.png) | [dark](14_chi_tiet_don_gia_dark.png) | Đạt; có lịch sử đơn giá và ngày hiệu lực. |
| Nhân viên – khóa khi đang trong ca | [light](15_khoa_dang_trong_ca_light.png) | [dark](15_khoa_dang_trong_ca_dark.png) | Đạt; hiển thị lỗi nghiệp vụ `EMPLOYEE_HAS_OPEN_SESSION`. |

Kiểm tra kỹ thuật:

- `npm run test:overflow`: không tràn ngang ở 360px và 390px cho 112 ca mock.
- Ảnh tối dùng biến theme; không còn nền sáng/chữ tối như lỗi GĐ7b trước đó.
- Bundle production đã kiểm tra không chứa dữ liệu mock (`Nguyễn Văn A`, `mock-token`, `manager_working`, `QL:`).
- Ô ngày ở Duyệt lương, Thêm nhân viên và Thêm đơn giá đều có nhãn DD/MM/YYYY theo múi giờ Việt Nam.
- Tab bar dưới đã dùng nền đặc theo theme, áp dụng nhất quán cho các màn quản lý.
