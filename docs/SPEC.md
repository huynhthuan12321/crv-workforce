## PHẦN 2 – ĐẶC TẢ NGHIỆP VỤ (SPEC)

> Phần này sẽ được AI chép nguyên vào `docs/SPEC.md` ở Giai đoạn 1.

### 2.1. Bối cảnh

- Xưởng sản xuất thực phẩm Cờ Rếp Việt, **1 điểm xưởng**.
- Nhân viên sản xuất làm **bán thời gian**, không có ca cố định, trả lương **theo giờ thực tế, tính theo ngày, trả ngay trong ngày**.
- Múi giờ duy nhất: **Asia/Ho_Chi_Minh**.

### 2.2. Vai trò

| Vai trò | Mã | Tab trong app | Quyền |
|---|---|---|---|
| Nhân viên | `employee` | Chấm công · Sản lượng · Lịch sử | Vào/ra ca, khai sản lượng, xem dữ liệu **của chính mình** |
| Quản lý | `manager` | Đang làm · Cần xử lý · Duyệt lương · Nhân viên | Xử lý phiên bất thường, sửa giờ công, duyệt lương, quản lý nhân viên và đơn giá. **Không chấm công, không có lương trong app** |
| Giám đốc | `director` | Báo cáo · Cần xử lý · Duyệt lương | Xem báo cáo (chỉ xem). Xử lý phiên bất thường và duyệt lương **giống quản lý** (làm thay khi quản lý vắng, luôn có quyền). **Không** quản lý nhân viên, **không** cài đơn giá |

- Một Mini App duy nhất. Vai trò xác định bằng Telegram ID đã liên kết với hồ sơ.
- **Phạm vi dữ liệu được xem:**
  - Nhân viên: chỉ dữ liệu của chính mình (phiên, sản lượng, đợt thanh toán, đơn giá hiện tại).
  - Quản lý: dữ liệu chấm công, sản lượng, lương của mọi nhân viên để xử lý và duyệt; hồ sơ và lịch sử đơn giá. **Không có tab Báo cáo tổng hợp.**
  - Giám đốc: mọi dữ liệu và báo cáo tổng hợp; không có quyền thêm/khóa nhân viên hay cài đơn giá.
- Người không có hồ sơ, hoặc hồ sơ bị khóa → không dùng được app.

### 2.3. Vào ca

1. Bắt buộc gửi vị trí GPS: vĩ độ, kinh độ, sai số (`accuracy`, mét).
2. **Chặn** nếu giờ server hiện tại **≥ 18:00**.
3. **Chặn** nếu nhân viên đang có phiên trạng thái `open`. Phiên `needs_review` (quên ra ca) của **các ngày trước** **không** chặn vào ca; nó vẫn nằm trong Cần xử lý và chưa được duyệt lương cho tới khi xử lý xong.
4. **Chặn** nếu nhân viên bị khóa, hoặc chưa đồng ý / đã rút lại đồng ý thu thập vị trí (xem 2.13).
5. Không giới hạn giờ vào ca sớm nhất trong ngày.
6. Tính khoảng cách (Haversine) từ vị trí gửi lên đến tọa độ xưởng:
   - Khoảng cách > **100 m** → vẫn cho vào ca, gắn cờ `gps_out_of_range`.
   - Sai số GPS > 100 m → vẫn cho vào ca, gắn cờ `gps_low_accuracy` (để quản lý phân biệt "GPS kém" với "đứng ngoài xưởng").
7. Chụp lại **đơn giá giờ đang có hiệu lực** vào phiên (`rate_snapshot`).

### 2.4. Ra ca

1. Bắt buộc gửi GPS, áp dụng cùng quy tắc gắn cờ như vào ca.
2. Giờ ra = giờ server lúc bấm.
3. Sau khi ra ca, nhân viên khai sản lượng (xem 2.6).

### 2.5. Tính giờ và tiền

- **Số phút của phiên** = (giờ ra − giờ vào), bỏ phần giây lẻ (làm tròn xuống phút nguyên). Không trừ giờ nghỉ.
- **Tiền của phiên (chưa làm tròn)** = số phút × `rate_snapshot` ÷ 60.
- **Tổng ngày (chưa làm tròn)** = tổng tiền mọi phiên đã đóng trong ngày của nhân viên đó.
- **Làm tròn LÊN tới 1.000đ, áp dụng trên TỔNG NGÀY**, không làm tròn từng phiên.
- Không có phiên qua nửa đêm. Giờ ra luôn cùng ngày với giờ vào.

### 2.6. Sản lượng

- Chỉ để **theo dõi**, không ảnh hưởng lương.
- Mỗi phiên có một bản khai gồm 7 mặt hàng, khai theo **túi** (số nguyên ≥ 0), hệ thống tự quy ra kg:

| Mặt hàng | kg/túi |
|---|---|
| Bột | 1,2 |
| Xúc xích | 1 |
| Phô mai | 1 |
| Chà bông | 1 |
| Sốt cam | 2 |
| Sốt trắng | 2 |
| Bơ | 2 |

- Bảng quy đổi **cố định**.
- Nhân viên được sửa bản khai trong **10 phút kể từ thời điểm phiên được đóng**:
  - Nhân viên tự ra ca → 10 phút kể từ lúc bấm Ra ca.
  - Phiên quên ra ca do quản lý/giám đốc đóng → 10 phút kể từ lúc quản lý/giám đốc xử lý xong; bot nhắn nhân viên vào khai sản lượng ngay khi phiên được đóng.
- Quá 10 phút → khóa, không ai sửa được (quản lý, giám đốc cũng không khai hộ).
- Không khai sản lượng không chặn việc tính lương.

### 2.7. Thông báo tự động và phiên quên ra ca

- **18:00**: bot nhắn cho từng nhân viên còn phiên đang mở: nhắc ra ca.
- **18:30**: mọi phiên còn mở được chuyển trạng thái `needs_review` (lý do `forgot_checkout`). Bot gửi danh sách cho **cả quản lý và giám đốc**.
- Quản lý hoặc giám đốc nhập **giờ ra** cho phiên đó, kèm **lý do bắt buộc**. Giờ ra phải sau giờ vào và cùng ngày.
- **Quét phiên tồn:** mỗi khi service bot khởi động và lúc **00:05** hằng ngày, mọi phiên `open` có `work_date` trước hôm nay được chuyển thành `needs_review` (lý do `forgot_checkout`) và báo cho quản lý, giám đốc. Mục đích: server dừng lâu hoặc scheduler lỗi cũng không để phiên cũ treo ở trạng thái `open`.
- Mọi job thông báo đều chống gửi trùng (xem bảng `notification_log`).

### 2.8. Mục "Cần xử lý"

Gồm hai loại:
1. Phiên bị gắn cờ GPS (`gps_out_of_range` hoặc `gps_low_accuracy`) → người xử lý bấm **"Đã xem"**.
2. Phiên quên ra ca → người xử lý nhập giờ ra + lý do.

**Ai xử lý trước thì mục đó khóa.** Người sau thấy "Đã xử lý bởi [tên] lúc [giờ]" và không thao tác được. Phải đảm bảo ở tầng database (khóa bản ghi trong transaction), không chỉ ở giao diện.

### 2.9. Sửa giờ công

- Chỉ **quản lý và giám đốc** được sửa giờ vào/ra của phiên. Nhân viên không sửa được.
- Bắt buộc ghi lý do. Mọi lần sửa ghi vào nhật ký (`audit_log`): ai sửa, lúc nào, giá trị cũ, giá trị mới, lý do.
- **Không được sửa** phiên đã thuộc một đợt thanh toán.

### 2.10. Đợt thanh toán (duyệt lương)

- Một ngày có thể có **nhiều đợt**. Sau khi duyệt, nhân viên vẫn vào ca tiếp được trong ngày (trước 18:00).
- **Phiên đủ điều kiện** vào đợt: đã đóng, không còn cờ chưa xử lý, không ở trạng thái `needs_review`, chưa thuộc đợt nào.
- Phiên đang mở **không chặn** duyệt; nó sẽ vào đợt sau.
- **Số tiền của đợt mới** = làm tròn LÊN 1.000đ (tổng tiền mọi phiên đã đóng trong ngày, gồm cả phiên đã trả và phiên đủ điều kiện) − tổng tiền các đợt đã trả trong ngày đó.
- Duyệt = **trả ngay**. Đợt được tạo ở trạng thái `paid`. Đợt và các phiên bên trong bị **khóa vĩnh viễn**, không ai sửa được.
- Có thể duyệt nhiều nhân viên cùng lúc; mỗi nhân viên tạo một đợt riêng.
- Nếu không còn phiên nào đủ điều kiện → báo "Không có dữ liệu để duyệt".
- Duyệt xong, bot nhắn cho nhân viên số tiền của đợt.
- Hai người cùng duyệt một nhân viên cùng lúc → chỉ một đợt được tạo.

### 2.11. Quản lý nhân viên (chỉ quản lý)

- Thêm nhân viên: họ tên, mã NV, đơn giá giờ, ngày hiệu lực. Hệ thống tạo **link mời dùng một lần** (dạng `https://t.me/<bot>/<app>?startapp=<mã_mời>`). Nhân viên mở link → hệ thống gắn Telegram ID vào hồ sơ. Link **dùng một lần, hết hạn sau 7 ngày**; quản lý tạo lại được.
- Khóa / mở khóa nhân viên. Không khóa được người đang có phiên mở.
- Đơn giá: thêm mức mới kèm "hiệu lực từ ngày" (không được trước ngày hôm nay). Giữ lịch sử đơn giá. Phiên đã tạo giữ nguyên `rate_snapshot` của nó.

### 2.12. Báo cáo (giám đốc)

- Lọc theo ngày / tuần / tháng và theo nhân viên.
- Chỉ số: tổng giờ công, tổng lương (đã trả + tạm tính chưa trả), tổng túi, tổng kg.
- Biểu đồ giờ công theo thời gian. Bảng sản lượng theo mặt hàng.

### 2.13. Dữ liệu cá nhân

- Lần đầu mở app, nhân viên phải bấm đồng ý cho thu thập vị trí khi vào/ra ca (theo Nghị định 13/2023/NĐ-CP). Chưa đồng ý → không chấm công được.
- Nội dung thông báo đồng ý có **số phiên bản** (`consent_version`). Lưu lịch sử: nhân viên, phiên bản, thời điểm đồng ý, thời điểm rút lại.
- Khi công ty đổi nội dung thông báo (tăng phiên bản) → nhân viên phải đồng ý lại ở lần mở app kế tiếp.
- Nhân viên được **rút lại đồng ý** trong app. Sau khi rút: không vào ca được; nếu đang trong ca thì vẫn được ra ca; quản lý nhận thông báo để sắp xếp cách chấm công khác.
- Chỉ thu vị trí **tại thời điểm bấm vào ca / ra ca**, không theo dõi liên tục.
- Không ghi tọa độ, token, initData, số điện thoại vào log ứng dụng.

### 2.14. Đồng bộ Lark

- Khi có phiên đóng, phiên được sửa, bản khai sản lượng, hoặc đợt thanh toán mới → ghi một bản ghi vào bảng outbox **trong cùng transaction** với thay đổi nghiệp vụ. Transaction lỗi thì cả hai cùng không được ghi.
- Tiến trình nền trong service bot gửi bản ghi outbox tới webhook n8n (kèm chữ ký HMAC), thử lại khi lỗi.

### 2.15. Đăng nhập và phiên làm việc

- Mini App gửi initData lên `POST /api/auth/session`. Backend kiểm tra chữ ký và chỉ chấp nhận initData có `auth_date` **không quá 1 giờ**.
- Hợp lệ → backend cấp **token phiên** (ký bằng khóa bí mật của server), hết hạn lúc **23:59 cùng ngày** (giờ VN). Mọi API khác dùng token này.
- Token hết hạn hoặc bị từ chối → app tự lấy initData hiện có để đăng nhập lại; nếu initData cũng quá hạn → yêu cầu đóng và mở lại app.
- Mỗi request vẫn kiểm tra lại trạng thái tài khoản (bị khóa là chặn ngay, không chờ token hết hạn).
- n8n ghi vào Lark Base. Lark chỉ để xem báo cáo.
