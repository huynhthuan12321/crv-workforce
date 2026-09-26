# So sánh GĐ7a/7b với thiết kế CRV UI V1

Ảnh thiết kế gốc: [docs/design/crv_ui_v1.png](../../design/crv_ui_v1.png)

Các ảnh dưới đây được chụp bằng mock DEV (`VITE_MOCK=1`), mobile viewport 390px bằng Puppeteer, gồm cả sáng và tối. Đã kiểm tra không tràn ngang ở 360px và 390px bằng `npm run test:overflow`.

| Màn trong thiết kế / DESIGN_NOTES | Ảnh sáng | Ảnh tối | Khác biệt còn lại |
|---|---|---|---|
| Chấm công – Chưa vào ca | [light](01_cham_cong_chua_vao_ca_light.png) | [dark](01_cham_cong_chua_vao_ca_dark.png) | Có thanh “Xem thử” chỉ trong mock DEV; production không có. |
| Đang lấy vị trí | [light](02_dang_lay_vi_tri_light.png) | [dark](02_dang_lay_vi_tri_dark.png) | Tự thiết kế theo DESIGN_NOTES, có hướng dẫn bật quyền vị trí. |
| Trong ca | [light](03_trong_ca_light.png) | [dark](03_trong_ca_dark.png) | Đồng hồ và lương tạm tính dùng dữ liệu mock Phụ lục B. |
| Vị trí ngoài xưởng / GPS > 100m | [light](04_gps_ngoai_250m_light.png) | [dark](04_gps_ngoai_250m_dark.png) | Hiển thị banner cam theo SPEC; mock dùng khoảng cách 250m. |
| Sau 18:00 – khóa vào ca | [light](05_sau_18h_light.png) | [dark](05_sau_18h_dark.png) | Nút VÀO CA disabled/aria-disabled và hiển thị xám; backend vẫn là nơi chặn thật. |
| Sản lượng – còn 10 phút | [light](06_san_luong_con_10_phut_light.png) | [dark](06_san_luong_con_10_phut_dark.png) | Stepper + nhập trực tiếp; số kg dùng mẫu đúng DESIGN_NOTES: tổng 14,0 kg. |
| Sản lượng – đã khóa | [light](07_san_luong_da_khoa_light.png) | [dark](07_san_luong_da_khoa_dark.png) | Form tự khóa khi countdown về 00:00. |
| Lịch sử – nhiều đợt | [light](08_lich_su_nhieu_dot_light.png) | [dark](08_lich_su_nhieu_dot_dark.png) | Dùng “Chờ duyệt” không đánh số đợt; mỗi phiên chỉ hiện giờ, thời lượng, GPS, sản lượng. |
| Đồng ý thu thập vị trí | [light](09_chua_dong_y_vi_tri_light.png) | [dark](09_chua_dong_y_vi_tri_dark.png) | Tự thiết kế cùng phong cách vì ảnh gốc thiếu màn này; chỉ giữ nội dung từ API trong khung. |
| Chưa được cấp quyền | [light](10_chua_duoc_cap_quyen_light.png) | [dark](10_chua_duoc_cap_quyen_dark.png) | Tự thiết kế cùng phong cách vì ảnh gốc thiếu màn này. |
| Tài khoản bị khóa | [light](11_bi_khoa_light.png) | [dark](11_bi_khoa_dark.png) | Tự thiết kế cùng phong cách vì ảnh gốc thiếu màn này. |
| Phiên đăng nhập hết hạn | [light](12_het_phien_light.png) | [dark](12_het_phien_dark.png) | Tự thiết kế cùng phong cách vì ảnh gốc thiếu màn này. |
| Lỗi mạng / 502 dễ hiểu | [light](13_loi_mang_light.png) | [dark](13_loi_mang_dark.png) | Đã thay lỗi HTML/Unexpected token bằng thông báo mạng dễ hiểu. |
