# Ghi chú thiết kế giao diện V1 (đọc cùng `crv_ui_v1.png`)

Ảnh `docs/design/crv_ui_v1.png` là thiết kế đã chốt về **màu sắc, bố cục, component**.
Khi ảnh và `docs/SPEC.md` khác nhau, **SPEC thắng**. Các điểm dưới đây là chỗ ảnh sai/thiếu so với SPEC, phải làm theo ghi chú này.

## 1. Sai vai trò (bắt buộc sửa)
- Hai màn "Danh sách nhân viên" (công tắc khóa/mở) và "Thiết lập đơn giá giờ" đang vẽ trong phần GIÁM ĐỐC.
  Theo SPEC 2.2 đây là màn của tab **Nhân viên – chỉ QUẢN LÝ**. Giám đốc không có bất kỳ lối vào nào tới quản lý nhân viên/đơn giá.
- Nút lưu trong màn "Thiết lập đơn giá giờ" ghi nhầm "Báo cáo" → phải là "Lưu đơn giá".

## 2. Khái niệm "đợt" (bắt buộc sửa)
- Hệ thống chỉ tạo **đợt** khi duyệt, và duyệt = đã trả (SPEC 2.10). Không tồn tại "đợt chờ duyệt".
- Ảnh vẽ "Đợt 2 – Chờ duyệt 122.000đ" (Lịch sử, Chi tiết lương) → phải hiển thị:
  "Chờ duyệt: 122.000đ" (không đánh số đợt), bên dưới là các phiên chưa vào đợt, kèm lý do nếu có (đang mở / cờ GPS chưa xử lý / quên ra ca).
- Các đợt đã trả: "Đợt N · Đã trả · số tiền".

## 3. Số liệu trong ảnh là minh họa
- Không chép số từ ảnh. Mọi số (kg, tiền, phút) lấy từ API hoặc tính từ dữ liệu.
- Ví dụ ảnh Sản lượng sai: Bột 3 túi ghi 6,0 kg (đúng 3,6 kg); tổng các dòng không bằng 14,0 kg.
- Mẫu đúng để đối chiếu (Phụ lục B): Bột 5 (6,0) · Xúc xích 3 (3,0) · Phô mai 2 (2,0) · Chà bông 1 (1,0) · Sốt cam 1 (2,0) · Sốt trắng 0 · Bơ 0 → 14,0 kg.

## 4. Màn còn thiếu trong ảnh – tự thiết kế cùng phong cách
- **Đồng ý thu thập vị trí** (nhân viên, trước lần vào ca đầu và khi có phiên bản mới): nội dung từ `GET /api/consent/current`, nút "Tôi đồng ý".
- **Quyền riêng tư** (nhân viên): xem nội dung đã đồng ý, nút "Rút lại đồng ý" + hộp xác nhận nêu hậu quả (không vào ca được nữa).
- **Chưa được cấp quyền** (NOT_REGISTERED, không có mã mời) và **Tài khoản đã bị khóa** (ACCOUNT_LOCKED).
- **Phiên đăng nhập hết hạn** (INITDATA_EXPIRED): "Vui lòng đóng và mở lại ứng dụng".
- **Thêm nhân viên** (quản lý): mã, họ tên, đơn giá, hiệu lực từ ngày → hiện link mời + nút Sao chép + nút Chia sẻ qua Telegram. Có nút "Tạo lại link mời" trong chi tiết nhân viên.
- **Lịch sử đơn giá** và **Thêm đơn giá** không cho chọn ngày trước hôm nay.

## 5. Chỉnh nhỏ
- Đếm ngược sản lượng: "Còn mm:ss để chỉnh sửa" (không hiển thị "Còn 672 giây").
- Biểu đồ giám đốc: cột **giờ công** + đường **lương** theo ngày (SPEC 2.12). Sản lượng xem ở bảng mặt hàng.
- Thẻ lương giám đốc: hiển thị tách **Đã trả / Tạm tính / Tổng**, không chỉ một số "ước tính".
- Ngày trong ảnh là 2024 – chỉ là minh họa, dùng ngày thật theo giờ VN.
- Cờ GPS ghi "Ngoài xưởng (X m)" lấy từ `check_in_distance_m`; "Trong xưởng" khi không có cờ `gps_out_of_range`.

## 6. Giữ nguyên theo ảnh
- Màu: xanh dương chính (nút VÀO CA, Xác nhận), đỏ (RA CA, Xác nhận duyệt), cam (cảnh báo), xanh lá (Đã trả, Trong xưởng).
- Bố cục thanh tab dưới theo vai trò, header có avatar + tên + mã NV + chip vai trò.
- Các trạng thái đặc biệt ở mục 6 của ảnh: Trống dữ liệu, Đang tải, Lỗi mạng + nút Thử lại.
