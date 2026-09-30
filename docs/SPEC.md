## PHẦN 2 – ĐẶC TẢ NGHIỆP VỤ (SPEC)

> Phần này sẽ được AI chép nguyên vào `docs/SPEC.md` ở Giai đoạn 1.

### 2.1. Bối cảnh

- Xưởng sản xuất thực phẩm Cờ Rếp Việt, có thể có nhiều **điểm làm việc**; giao diện V1 gọi điểm làm việc là **Kho** (xem 2.17).
- Nhân viên sản xuất làm **bán thời gian**, không có ca cố định, trả lương **theo giờ thực tế, tính theo ngày, trả ngay trong ngày**.
- Múi giờ duy nhất: **Asia/Ho_Chi_Minh**.

### 2.2. Vai trò

| Vai trò | Mã | Tab trong app | Quyền |
|---|---|---|---|
| Nhân viên | `employee` | Chấm công · Sản lượng · Lịch sử | Vào/ra ca, khai sản lượng, xem dữ liệu **của chính mình**, xem kho được phân công và khoảng cách tại thời điểm chấm công; nhận thông báo và nhắn tới quản lý/giám đốc theo 2.21 |
| Quản lý | `manager` | Đang làm · Cần xử lý · Duyệt lương · Quản lý · Tin nhắn | Xử lý phiên bất thường, sửa giờ công, duyệt lương, quản lý nhân viên, đơn giá, kho và phân công kho. **Không chấm công, không có lương trong app**. Gửi thông báo **chỉ cho nhân viên**, xem/trả lời hộp thư kênh Quản lý |
| Giám đốc | `director` | Báo cáo · Cần xử lý · Duyệt lương · Tin nhắn | Xem báo cáo (chỉ xem). Xử lý phiên bất thường và duyệt lương **giống quản lý** (làm thay khi quản lý vắng, luôn có quyền). Được xem/thêm/sửa/ngừng dùng/kích hoạt kho, lọc báo cáo theo kho. **Không** quản lý nhân viên, **không** cài đơn giá, **không** phân công nhân viên vào kho. Gửi thông báo tới mọi nhóm theo 2.21, xem kênh Giám đốc và xem chỉ đọc kênh Quản lý |

- Một Mini App duy nhất. Vai trò xác định bằng Telegram ID đã liên kết với hồ sơ.
- **Phạm vi dữ liệu được xem:**
  - Nhân viên: chỉ dữ liệu của chính mình (phiên, sản lượng, đợt thanh toán, đơn giá hiện tại).
  - Quản lý: dữ liệu chấm công, sản lượng, lương của mọi nhân viên để xử lý và duyệt; hồ sơ, lịch sử đơn giá, kho và phân công kho. **Không có tab Báo cáo tổng hợp.**
  - Giám đốc: mọi dữ liệu và báo cáo tổng hợp; có quyền quản lý danh mục kho nhưng không có quyền thêm/khóa nhân viên, cài đơn giá hay phân công nhân viên vào kho.
- Người không có hồ sơ, hoặc hồ sơ bị khóa → không dùng được app.

### 2.3. Vào ca

1. Bắt buộc gửi vị trí GPS: vĩ độ, kinh độ, sai số (`accuracy`, mét).
2. **Chặn** nếu giờ server hiện tại **≥ 18:00**.
3. **Chặn** nếu nhân viên đang có phiên trạng thái `open`. Phiên `needs_review` (quên ra ca) của **các ngày trước** **không** chặn vào ca; nó vẫn nằm trong Cần xử lý và chưa được duyệt lương cho tới khi xử lý xong.
4. **Chặn** nếu nhân viên bị khóa, hoặc chưa đồng ý / đã rút lại đồng ý thu thập vị trí (xem 2.13).
5. Không giới hạn giờ vào ca sớm nhất trong ngày.
6. Tính khoảng cách (Haversine) từ vị trí gửi lên đến **snapshot kho được phân công hiện hành tại thời điểm check-in** (xem 2.17):
   - Khoảng cách > bán kính của kho được phân công → vẫn cho vào ca, gắn cờ `gps_out_of_range`.
   - Sai số GPS > 100 m → vẫn cho vào ca, gắn cờ `gps_low_accuracy` (để quản lý phân biệt "GPS kém" với "đứng ngoài xưởng").
   - Nếu vị trí nằm trong bán kính của kho đang hoạt động khác thì chỉ ghi cảnh báo `nearby_location_*`; tuyệt đối không tự đổi phiên sang kho khác.
7. Chụp lại **đơn giá giờ đang có hiệu lực** vào phiên (`rate_snapshot`) và snapshot kho được phân công (`work_location_id`, mã/tên/tọa độ/bán kính kho).

### 2.4. Ra ca

1. Bắt buộc gửi GPS, áp dụng cùng quy tắc gắn cờ như vào ca nhưng so với **snapshot kho của phiên**, không đọc lại phân công hiện tại.
2. Giờ ra = giờ server lúc bấm.
3. Sau khi ra ca, nhân viên khai sản lượng (xem 2.6).

### 2.5. Tính giờ và tiền

- **Số phút của phiên** = (giờ ra − giờ vào), bỏ phần giây lẻ (làm tròn xuống phút nguyên). Không trừ giờ nghỉ.
- **Tiền của phiên (chưa làm tròn)** = số phút × `rate_snapshot` ÷ 60.
- **Tổng ngày (chưa làm tròn)** = tổng tiền mọi phiên đã đóng trong ngày của nhân viên đó, dù trong ngày có nhiều đơn giá hoặc nhiều kho.
- **Làm tròn LÊN tới 1.000đ, áp dụng trên TỔNG NGÀY**, không làm tròn từng phiên.
- Không có phiên qua nửa đêm. Giờ ra luôn cùng ngày với giờ vào.

### 2.6. Sản lượng

- Chỉ để **theo dõi**, không ảnh hưởng lương.
- Mỗi phiên có một bản khai theo **danh mục sản phẩm đã chốt tại thời điểm phiên đóng** (SPEC 2.20). Danh mục có thể gồm sản phẩm chung, sản phẩm theo kho hoặc sản phẩm riêng nhân viên.
- V1 chỉ hỗ trợ đơn vị đếm nguyên (mặc định `Túi`); số lượng là số nguyên ≥ 0, hệ thống tự quy ra kg bằng snapshot quy cách của từng dòng sản lượng.
- 7 sản phẩm mặc định (Bột, Xúc xích, Phô mai, Chà bông, Sốt cam, Sốt trắng, Bơ) chỉ là dữ liệu seed khi bảng sản phẩm rỗng, không phải bảng quy đổi cố định.
- Mỗi dòng sản lượng lưu snapshot mã, tên, đơn vị, quy cách, thứ tự và tổng kg; không diễn giải lại lịch sử từ danh mục hiện tại.
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
- Mọi job thông báo đều chống gửi trùng bằng `notification_outbox.dedupe_key` (unique).
- Thông báo do người dùng tạo và tin nhắn riêng tuân theo SPEC 2.21: luôn là chat 1-1 qua bot, lưu vĩnh viễn trong PostgreSQL, không đồng bộ Lark, chỉ gửi tới người đang hoạt động và đã liên kết Telegram. Quyền xem, trả lời, xác nhận đã nhận, giới hạn 2.000 ký tự và thời gian chờ chọn người nhận thực hiện ở backend; frontend/bot không tự suy diễn quyền.

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
- Nếu còn phiên đủ điều kiện nhưng số tiền đợt mới = 0đ (phần làm tròn của đợt trước đã bao phủ), vẫn tạo đợt 0đ để gắn và khóa các phiên đó. Bot nhắn nhân viên: 'Đợt N: 0đ (đã được làm tròn ở đợt trước)'.
- Duyệt = **trả ngay**. Đợt được tạo ở trạng thái `paid`. Đợt và các phiên bên trong bị **khóa vĩnh viễn**, không ai sửa được.
- Có thể duyệt nhiều nhân viên cùng lúc; mỗi nhân viên tạo một đợt riêng.
- Bộ lọc kho trong màn Duyệt lương chỉ xác định nhân viên được hiển thị; khi duyệt một nhân viên, hệ thống xử lý toàn bộ phiên đủ điều kiện của nhân viên đó trong ngày, bất kể các phiên thuộc kho nào. Lương vẫn làm tròn một lần theo tổng ngày của nhân viên, không làm tròn riêng từng kho.
- Nếu một ngày có nhiều đơn giá, hệ thống vẫn cộng tiền phiên theo từng `rate_snapshot` rồi làm tròn một lần trên tổng ngày. Chi tiết duyệt lương phải hiển thị đơn giá và tiền thô từng phiên để người duyệt kiểm tra.
- Nếu không còn phiên nào đủ điều kiện → báo "Không có dữ liệu để duyệt".
- Duyệt xong, bot nhắn cho nhân viên số tiền của đợt.
- Hai người cùng duyệt một nhân viên cùng lúc → chỉ một đợt được tạo.

### 2.11. Quản lý nhân viên (chỉ quản lý)

- Thêm nhân viên: họ tên, mã NV, đơn giá giờ ban đầu và **kho được phân công ban đầu**. Đơn giá ban đầu dùng cơ chế lịch sử đơn giá theo thời điểm ở 2.18. Hệ thống tạo **link mời dùng một lần** (dạng `https://t.me/<bot>/<app>?startapp=<mã_mời>`). Nhân viên mở link → hệ thống gắn Telegram ID vào hồ sơ. Link **dùng một lần, hết hạn sau 7 ngày**; quản lý tạo lại được.
- Khóa / mở khóa nhân viên. Không khóa được người đang có phiên mở.
- Đơn giá: quản lý được điều chỉnh theo 2 chế độ ở 2.18: "Từ lần vào ca tiếp theo" hoặc "Từ ngày ..." (ngày mai trở đi, 00:00 giờ VN). Giữ lịch sử đơn giá theo thời điểm, cho hủy mức hẹn chưa hiệu lực, bắt buộc lý do. Phiên đã tạo giữ nguyên `rate_snapshot` của nó.
- Quản lý được đổi kho phân công cho nhân viên, bắt buộc ghi lý do; phiên đang mở và lịch sử giữ snapshot kho cũ. Giám đốc không được phân công nhân viên vào kho.

### 2.12. Báo cáo (giám đốc)

- Lương trong báo cáo = **Đã trả + Chờ duyệt + Cần xử lý trước**:
  - **Đã trả**: tổng `pay_batches.amount`.
  - **Chờ duyệt**: đúng bằng tổng `pending_amount` của `PayrollService` cho từng cặp (nhân viên, ngày), dùng chung logic phiên đủ điều kiện với duyệt lương.
  - **Cần xử lý trước**: phần còn lại của các phiên đã đóng chưa vào đợt nhưng còn cờ GPS chưa xem. Tính theo làm tròn ngày: `ceil(tổng thô mọi phiên đã đóng) − đã trả − chờ duyệt`, không âm.
  - Phiên `needs_review` (quên ra ca, chưa có giờ ra) không tính tiền, chỉ đếm số phiên để hiển thị cảnh báo.
- Lọc theo ngày / tuần / tháng và theo nhân viên.
- Lọc theo kho:
  - "Tất cả kho": dùng đúng số liệu Đã trả / Chờ duyệt / Cần xử lý trước / Tổng đã làm tròn theo ngày như trên.
  - Một kho cụ thể: giờ công, số lượng, kg tính chính xác theo phiên thuộc kho đó; lương hiển thị là **Chi phí theo phiên (chưa làm tròn)** = tổng `amount_raw` của các phiên tại kho đó, kèm ghi chú rằng lương làm tròn theo ngày nên tổng các kho có thể lệch vài nghìn đồng so với "Tất cả kho".
- Chỉ số: tổng giờ công, tổng lương (đã trả + chờ duyệt + cần xử lý trước), tổng số lượng theo đơn vị sản phẩm, tổng kg, và số **phiên chưa khai sản lượng** theo 2.20.
- Biểu đồ giờ công theo thời gian. Bảng sản lượng theo mặt hàng gom theo snapshot sản phẩm; chỉ cộng bản khai `submitted`, sản phẩm ngừng sản xuất vẫn hiện nếu kỳ có dữ liệu, sản phẩm đã xóa không hiện.

### 2.13. Dữ liệu cá nhân

- Lần đầu mở app, nhân viên phải bấm đồng ý cho thu thập vị trí khi vào/ra ca (theo Nghị định 13/2023/NĐ-CP). Chưa đồng ý → không chấm công được.
- Nội dung thông báo đồng ý có **số phiên bản** (`consent_version`). Lưu lịch sử: nhân viên, phiên bản, thời điểm đồng ý, thời điểm rút lại.
- Khi công ty đổi nội dung thông báo (tăng phiên bản) → nhân viên phải đồng ý lại ở lần mở app kế tiếp.
- Nhân viên được **rút lại đồng ý** trong app. Sau khi rút: không vào ca được; nếu đang trong ca thì vẫn được ra ca; quản lý nhận thông báo để sắp xếp cách chấm công khác.
- Chỉ thu vị trí **tại thời điểm bấm vào ca / ra ca**, không theo dõi liên tục.
- Không ghi tọa độ, token, initData, số điện thoại vào log ứng dụng.

### 2.14. Đồng bộ Lark

- Khi có phiên đóng, phiên được sửa, bản khai sản lượng, hoặc đợt thanh toán mới → ghi một bản ghi vào bảng outbox **trong cùng transaction** với thay đổi nghiệp vụ. Transaction lỗi thì cả hai cùng không được ghi.
- Payload outbox/Lark mặc định dùng `schema_version = 2`, cấu trúc lồng có `employee`, `location`/`locations`, `session`/`sessions`; riêng `output_submitted` dùng `schema_version = 3` và gửi snapshot sản phẩm theo 2.20. `event_id` là khóa idempotency duy nhất và phải giữ nguyên khi retry.
- Tiến trình nền trong service bot gửi bản ghi outbox tới webhook n8n (kèm chữ ký HMAC), thử lại khi lỗi.

### 2.15. Đăng nhập và phiên làm việc

- Mini App gửi initData lên `POST /api/auth/session`. Backend kiểm tra chữ ký và chỉ chấp nhận initData có `auth_date` **không quá 1 giờ**.
- Hợp lệ → backend cấp **token phiên** (ký bằng khóa bí mật của server), hết hạn lúc **23:59 cùng ngày** (giờ VN). Mọi API khác dùng token này.
- Token hết hạn hoặc bị từ chối → app tự lấy initData hiện có để đăng nhập lại; nếu initData cũng quá hạn → yêu cầu đóng và mở lại app.
- Mỗi request vẫn kiểm tra lại trạng thái tài khoản (bị khóa là chặn ngay, không chờ token hết hạn).
- n8n ghi vào Lark Base. Lark chỉ để xem báo cáo.

### 2.17. Điểm làm việc (UI: "Kho")

Trạng thái: **ĐÃ CHỐT – đóng băng trước khi code.** Mọi thay đổi phải sửa `docs/spec/2.17_diem_lam_viec.md` trước.
Domain backend: `work_locations`. Giao diện V1 gọi là "Kho".

#### 2.17.0. Quy tắc gốc

> Mỗi nhân viên có đúng một điểm làm việc hiện hành. Mỗi phiên làm việc được gắn cố định với điểm làm việc có hiệu lực tại thời điểm check-in và lưu snapshot tọa độ/bán kính của điểm đó. Mọi thay đổi phân công hoặc cấu hình điểm làm việc sau thời điểm check-in không được làm thay đổi phiên đang mở hoặc lịch sử. Check-out tiếp tục sử dụng snapshot của phiên.

#### 2.17.1. Mô hình dữ liệu

##### 2.17.1.1 `work_locations`

| Cột | Ghi chú |
|---|---|
| id | |
| code | duy nhất, ví dụ `KHO01` |
| name | duy nhất |
| location_type | mặc định `warehouse` (V1 không hiện trên UI) |
| address | |
| latitude, longitude | kiểm tra trong Việt Nam: lat 8–24, lng 102–110 (bắt lỗi dán ngược) |
| radius_m | 30–1000 |
| coordinate_source | `device_gps` \| `manual_coordinates` |
| location_accuracy_m | nullable; NULL khi nhập tay (không giả định là chính xác) |
| is_active | |
| created_by, created_at, updated_at | |

##### 2.17.1.2 `employee_location_assignments`

| Cột | Ghi chú |
|---|---|
| id, employee_id, location_id | |
| effective_from | timestamptz |
| effective_to | timestamptz, NULL = hiện hành |
| changed_by, reason, created_at | |

Ràng buộc DB:

- `CHECK (effective_to IS NULL OR effective_to > effective_from)`
- Partial unique: `(employee_id) WHERE effective_to IS NULL` – tối đa 1 phân công hiện hành.
- Chống chồng thời gian: `EXCLUDE USING gist (employee_id WITH =, tstzrange(effective_from, effective_to, '[)') WITH &&)` (extension `btree_gist`).

##### 2.17.1.3 Snapshot trên `work_sessions` (BẤT BIẾN sau khi tạo)

`work_location_id, location_code_snapshot, location_name_snapshot, location_lat_snapshot, location_lng_snapshot, location_radius_m_snapshot`
+ GPS nghiệp vụ: `check_in_lat/lng/accuracy_m/distance_m`, `check_out_lat/lng/accuracy_m/distance_m`
+ `flag_source` (`check_in` \| `check_out` \| `both`), `nearby_location_id`, `nearby_location_distance_m` (nullable).

Các cột `location_*_snapshot` KHÔNG bao giờ được cập nhật theo `work_locations`: đổi tên, đổi tọa độ, đổi bán kính, ngừng dùng kho hay chuyển kho nhân viên đều không ảnh hưởng phiên đã tạo.

#### 2.17.2. Phân công

- R1. Mỗi nhân viên (role employee) đúng 1 phân công hiện hành. Thêm nhân viên bắt buộc chọn kho.
- Đổi kho = trong cùng transaction: `effective_to = now()` cho phân công cũ, tạo phân công mới `effective_from = now()`; bắt buộc `reason`; audit `employee_location_changed`.
- Mốc là **timestamp**, không có khái niệm "hiệu lực từ ngày mai". "Áp dụng từ lần vào ca sau" là hệ quả tự nhiên: phiên đang mở giữ snapshot cũ.
- Không được phân công vào kho đã ngừng dùng (`LOCATION_INACTIVE`).
- Quyền: CHỈ quản lý phân công. Giám đốc không phân công (giữ ranh giới SPEC 2.2).

#### 2.17.3. Vào ca / ra ca

- R2. Check-in đọc phân công hiện hành **tại thời điểm check-in** → snapshot vào phiên.
- R3. `distance(GPS, kho được phân công)`:
  - ≤ bán kính: bình thường;
  - > bán kính: VẪN vào ca, gắn cờ `gps_out_of_range`.
- R3b. Cảnh báo kho khác CHỈ khi vị trí nằm TRONG bán kính của một kho đang hoạt động khác → ghi `nearby_location_*`. Kho khác ở xa (ví dụ 2,5 km) thì không nhắc.
  Hiển thị: "Ngoài phạm vi [Kho A] được phân công · Bạn đang trong phạm vi [Kho B] (30 m)".
- **Kho gần/chồng lấn chỉ là thông tin cho quản lý. TUYỆT ĐỐI không tự đổi phiên sang kho khác.** Phân công luôn quyết định kho hợp lệ.
- Kho được phân công đã ngừng dùng → từ chối vào ca `LOCATION_INACTIVE` ("Liên hệ quản lý").
- R10. Check-out so GPS với **snapshot của phiên**, không đọc phân công hiện tại.
  Ví dụ: 08:00 vào ca Kho A → 12:00 quản lý chuyển sang Kho B → 17:00 ra ca: so với Kho A. Lần vào ca sau mới là Kho B.

#### 2.17.4. Ngừng dùng kho

- R7. Không xóa cứng. Chỉ Ngừng dùng / Kích hoạt lại. Quản lý và giám đốc đều làm được.
- Bị cấm khi: `số phân công hiện hành (effective_to IS NULL) > 0` HOẶC `số phiên status = open gắn kho > 0` → `LOCATION_IN_USE` kèm 2 con số.
- Phân công lịch sử và phiên lịch sử KHÔNG chặn. Phiên `needs_review` (quên ra ca) KHÔNG chặn – xử lý dựa trên snapshot.

#### 2.17.5. Giao thức khóa (bắt buộc – chống race)

Thứ tự khóa chung: **employee → assignment → work_location**.

| Thao tác | Khóa |
|---|---|
| Check-in | `employees` FOR UPDATE → đọc phân công hiện hành → `work_locations` FOR SHARE → kiểm tra is_active → tạo phiên |
| Đổi kho | `employees` FOR UPDATE → phân công hiện hành FOR UPDATE → kho MỚI FOR SHARE (kiểm tra is_active) → đóng cũ, mở mới |
| Ngừng dùng kho | `work_locations` FOR UPDATE → đếm phân công hiện hành + phiên open → cập nhật |

- Không dùng `FOR KEY SHARE` cho check-in: nó không chặn cập nhật `is_active`.
- Kết quả tranh chấp đều hợp lệ và rõ ràng: check-in khóa trước → phiên thuộc kho cũ; đổi kho commit trước → phiên thuộc kho mới. Không bao giờ có snapshot "nửa A nửa B", không bao giờ có phiên mới gắn kho vừa ngừng dùng.

#### 2.17.6. Lương và báo cáo

- R6 (quy tắc lương chính thức): **Bộ lọc điểm làm việc trong Duyệt lương chỉ xác định nhân viên được hiển thị, không thay đổi đơn vị tính lương theo ngày. Khi duyệt một nhân viên, hệ thống xử lý toàn bộ phiên đủ điều kiện của nhân viên đó trong ngày, bất kể các phiên thuộc điểm làm việc nào.**
- Làm tròn lên 1.000đ một lần trên tổng cả ngày của nhân viên. KHÔNG làm tròn riêng từng kho.
- Lọc Duyệt lương theo Kho A: hiện nhân viên có ≥ 1 phiên (MỌI trạng thái) tại Kho A trong ngày. Số tiền trên dòng = toàn bộ của ngày. Nếu có phiên ở kho khác: "⚠ Có phiên tại 2 điểm làm việc" + danh sách kho.
- Báo cáo giám đốc:
  - "Tất cả kho": Đã trả / Chờ duyệt / Cần xử lý / Tổng (đã làm tròn theo ngày) như hiện tại.
  - Lọc 1 kho: giờ công, túi, kg chính xác theo phiên; lương hiện "Chi phí theo phiên (chưa làm tròn)" = Σ amount_raw của phiên tại kho đó, kèm ghi chú "Lương làm tròn theo ngày của từng nhân viên nên tổng các kho có thể chênh vài nghìn đồng so với Tất cả kho".
- Lọc không bao giờ làm mất hoặc nhân đôi phiên.

#### 2.17.7. Tạo kho bằng GPS

UI ghi "Độ chính xác ước tính: ±X m" (KHÔNG ghi "sai số X m").

| accuracy | UI |
|---|---|
| ≤ 30 m | ● Tốt |
| 31–100 m | ⚠ Độ chính xác trung bình – nên kiểm tra trên bản đồ trước khi lưu |
| > 100 m | ⚠ Độ chính xác thấp – [Thử lấy lại vị trí] [Vẫn lưu vị trí này] |

Chọn "Vẫn lưu" khi > 100 m → audit `location_saved_with_low_accuracy` (accuracy_m, confirmed_by, confirmed_at).
Dán tọa độ / link Google Maps → `coordinate_source = manual_coordinates`, `location_accuracy_m = NULL`.

#### 2.17.8. Cấu hình

- R4. `WORKSHOP__LAT/LNG/RADIUS_M` chỉ dùng cho migration/seed lần đầu. Sau migration PostgreSQL là nguồn duy nhất; runtime KHÔNG đọc các biến này.

#### 2.17.9. Migration dữ liệu cũ

- R5. Tạo kho `KHO01 – Xưởng chính` từ WORKSHOP__* (coordinate_source = manual_coordinates).
- Phân công mọi employee vào KHO01, `effective_from = employees.created_at`.
- Mọi phiên cũ: `work_location_id = KHO01` + đủ snapshot (tọa độ, bán kính CŨ) + suy `flag_source` một lần theo bán kính cũ.
- downgrade hoạt động; đếm số phiên trước/sau bằng nhau.

#### 2.17.10. Lark / outbox

- Payload chuyển sang cấu trúc lồng, `schema_version = 2` (payload hiện tại coi là 1):

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "event_type": "session_closed",
  "occurred_at": "2026-09-28T14:30:00+07:00",
  "employee": {"id": 1, "code": "NV001", "name": "Nguyễn Văn A"},
  "location": {"id": 1, "code": "KHO01", "name": "Xưởng chính"},
  "session": {"id": 123, "...": "..."}
}
```

- Áp dụng: session_closed, session_updated, output_submitted, batch_paid (batch nhiều kho → `locations: [...]` và mỗi session mang location).
- `event_id` là khóa idempotency duy nhất. Không dùng schema_version để chống trùng. Gửi lại giữ nguyên cả event_id và schema_version.

#### 2.17.11. Quyền

| Thao tác | Quản lý | Giám đốc | Nhân viên |
|---|---|---|---|
| Xem danh sách kho | ✓ | ✓ | – |
| Thêm/sửa/ngừng dùng/kích hoạt kho | ✓ | ✓ | – |
| Phân công nhân viên vào kho | ✓ | – | – |
| Lọc theo kho (Đang làm, Cần xử lý, Duyệt lương) | ✓ | ✓ | – |
| Lọc báo cáo theo kho | – | ✓ | – |
| Xem kho của mình + khoảng cách | – | – | ✓ |

#### 2.17.12. GPS và log

GPS nghiệp vụ lưu trong DB. KHÔNG ghi tọa độ vào application log. Chính sách retention: việc tương lai.

### 2.18. Lịch sử đơn giá

Trạng thái: **ĐÃ CHỐT – đóng băng trước khi code.** Mọi thay đổi phải sửa `docs/spec/2.18_don_gia.md` trước.
Liên quan: 2.5 (tính tiền), 2.10 (duyệt lương), 2.11 (quản lý nhân viên), 2.17 (điểm làm việc).

#### 2.18.0. Ba quy tắc gốc

**R-RATE – Lịch sử đơn giá.** Mỗi nhân viên có lịch sử đơn giá theo thời điểm. Đơn giá có hiệu lực tại thời điểm T là bản ghi chưa bị hủy có `effective_from` lớn nhất nhưng không vượt quá T. Hệ thống không cho tạo thay đổi đơn giá có hiệu lực trong quá khứ.

**R-SNAPSHOT – Snapshot phiên.** Khi check-in, hệ thống lấy đơn giá đang có hiệu lực và lưu cố định vào `rate_snapshot`. Mọi thay đổi đơn giá sau đó không ảnh hưởng phiên đang mở hoặc phiên lịch sử.

**R-ADJUST – Không sửa ngược lương.** Phiên và đợt thanh toán đã khóa không được sửa ngược dữ liệu gốc (phiên, đợt, lịch sử đơn giá). Hệ thống KHÔNG có chức năng khoản điều chỉnh lương (đã bỏ SPEC 2.19 – quyết định 29/09/2026); sai lệch sau khi đã duyệt được xử lý ngoài hệ thống.

Hệ quả tính tiền (không đổi so với 2.5): tiền phiên theo `rate_snapshot`; tổng các phiên trong ngày của một nhân viên được cộng trước và làm tròn lên 1.000đ MỘT lần, không tách theo đơn giá hay điểm làm việc.

#### 2.18.1. Mô hình dữ liệu – nâng cấp bảng `rate_history` hiện có (mô hình bậc thang)

| Cột | Thay đổi |
|---|---|
| id, employee_id, hourly_rate | giữ |
| effective_from | `date` → **`timestamptz`** |
| reason | THÊM, bắt buộc (bản ghi migrate: "Dữ liệu trước nâng cấp") |
| created_by, created_at | giữ |
| cancelled_at, cancelled_by, cancel_reason | THÊM – chỉ cho mức ĐÃ HẸN chưa có hiệu lực |

- KHÔNG có `effective_to` → không thể chồng thời gian.
- Ràng buộc: `hourly_rate > 0`; partial unique `(employee_id, effective_from) WHERE cancelled_at IS NULL`; partial unique `(employee_id) WHERE cancelled_at IS NULL AND effective_from > now()` KHÔNG làm được bằng index (now() không immutable) → kiểm tra ở service trong transaction có khóa nhân viên (xem mục 2).
- Không DELETE, không UPDATE giá trị/thời điểm của bản ghi. Chỉ được ghi các cột hủy của mức chưa hiệu lực.

#### 2.18.2. Thay đổi đơn giá (chỉ QUẢN LÝ; giám đốc chỉ xem – giữ SPEC 2.2)

UI chỉ có 2 chế độ (không cho chọn giờ phút):

1. **● Từ lần vào ca tiếp theo** (mặc định) → `effective_from = now()` lúc xác nhận. Phiên đang mở giữ đơn giá cũ; mọi phiên check-in sau thời điểm đó dùng mức mới.
2. **○ Từ ngày …** → chọn NGÀY từ ngày mai trở đi → `effective_from = 00:00:00 +07:00` ngày đó. UI ghi: "Có hiệu lực với các phiên bắt đầu từ ngày DD/MM/YYYY."

- `effective_from < now()` → `RATE_IN_PAST`.
- **Tối đa 1 mức hẹn trước chưa có hiệu lực** cho mỗi nhân viên. Đã có mức hẹn → phải hủy trước khi hẹn mức khác (`RATE_PENDING_EXISTS`). Chế độ "Từ lần vào ca tiếp theo" khi đang có mức hẹn: vẫn cho phép, mức hẹn giữ nguyên (sẽ thay thế khi tới ngày).
- Lý do bắt buộc 5–200 ký tự. UI có chọn nhanh: "Tăng theo năng lực", "Điều chỉnh nhiệm vụ", "Thay đổi công việc", "Điều chỉnh tạm thời", "Khác" – lưu nguyên văn chữ.
- Lệch > 50% so với mức hiện hành → KHÔNG chặn, bắt xác nhận lần 2: "Đơn giá giảm 62,5%: 40.000đ → 15.000đ/giờ. Vui lòng xác nhận đây là thay đổi chủ động." (tăng thì ghi "tăng").
- Giới hạn cứng cấu hình được: `RULES__MIN_HOURLY_RATE` (mặc định 1.000), `RULES__MAX_HOURLY_RATE` (mặc định 1.000.000) → `RATE_OUT_OF_RANGE`. Không hard-code.
- Hủy mức hẹn: chỉ khi `effective_from > now()`, bắt buộc lý do; mức đã hiệu lực KHÔNG hủy được – muốn đổi thì tạo mức mới.
- Audit: `rate_changed` (cũ → mới, chế độ, effective_from, lý do), `rate_cancelled`.
- Thao tác đổi/hủy khóa bản ghi nhân viên (FOR UPDATE) – cùng thứ tự khóa với 2.17 mục 5.
- Nhân viên mới: đơn giá ban đầu dùng cùng 2 chế độ, lý do mặc định "Đơn giá ban đầu".

#### 2.18.3. Vào ca và thao tác phiên

- Check-in tra đơn giá theo **thời điểm check-in** (không theo ngày) → `rate_snapshot`. Không có đơn giá → `NO_RATE` ("Chưa có đơn giá, liên hệ quản lý").
- `rate_snapshot` BẤT BIẾN: sửa giờ phiên, đóng phiên quên ra ca, đổi kho, đổi/hủy đơn giá đều không đổi nó.
- Đơn giá và điểm làm việc là hai miền độc lập (V1 không có đơn giá theo kho).

#### 2.18.4. Tính tiền

Như 2.5: phiên = phút × rate_snapshot / 60; ngày = Σ phiên (mọi đơn giá, mọi kho) → làm tròn 1 lần.
Ví dụ: 08:00–10:00 @30k = 60.000; 13:00–17:00 @40k = 160.000 → 220.000đ.

#### 2.18.5. Hiển thị

**Màn Chấm công (nhân viên)** – tách rõ 2 khái niệm:

- "Tạm tính hôm nay: X đ" (cả ngày, số lớn).
- "Ca này: 43 phút × 30.000đ/giờ" (ca đang mở, dùng rate_snapshot). Không bao giờ đặt công thức ca này ngay dưới số cả ngày như thể là một.
- Có mức hẹn áp dụng cho mình → dòng nhỏ "Từ 01/11/2026: 40.000đ/giờ".

**Duyệt lương – dòng nhân viên**: 1 đơn giá → "Đơn giá 30.000đ/giờ". Nhiều đơn giá trong ngày → "2 phiên · 6 giờ · 2 mức đơn giá (30.000 → 40.000đ/giờ)" + "Tạm tính ngày 220.000đ". KHÔNG hiện một đơn giá duy nhất.

**Duyệt lương – chi tiết**: mỗi phiên hiện giờ, đơn giá, tiền phiên (chưa làm tròn) để quản lý hiểu tổng.

**Hồ sơ nhân viên** (quản lý; giám đốc chỉ xem): Đơn giá hiện tại + "Hiệu lực từ DD/MM/YYYY · HH:MM"; mức hẹn (nếu có) + nút Hủy; bảng Lịch sử đơn giá (hiệu lực, đơn giá, lý do, người đổi, trạng thái Đã hủy).

**Màn Điều chỉnh đơn giá**: đơn giá hiện tại, ô mức mới, 2 chế độ hiệu lực, lý do (chọn nhanh + ô chữ), câu "Phiên đang làm hiện tại không bị thay đổi đơn giá.", Hủy / Xác nhận.

#### 2.18.6. Thông báo bot (riêng nhân viên, chống trùng bằng dedupe_key; KHÔNG gửi lý do nội bộ)

- Hiệu lực ngay: "Đơn giá của bạn đã được cập nhật.\nMức mới: 40.000đ/giờ\nÁp dụng từ lần vào ca tiếp theo."
- Hẹn ngày: "Đơn giá của bạn sẽ được cập nhật.\nMức mới: 40.000đ/giờ\nCó hiệu lực từ 01/11/2026."
- Hủy mức hẹn: "Thay đổi đơn giá dự kiến từ 01/11/2026 đã được hủy. Đơn giá hiện tại của bạn vẫn là 30.000đ/giờ."

#### 2.18.7. Migration

- `effective_from` date → timestamptz 00:00 giờ VN của ngày cũ; `reason = "Dữ liệu trước nâng cấp"`.
- Không đụng `rate_snapshot` phiên cũ. Số bản ghi trước/sau bằng nhau.

#### 2.18.8. Ngoài phạm vi 2.18

Khoản điều chỉnh lương (SPEC 2.19 cũ) đã BỎ – không triển khai. Sửa lương phiên đã qua / đợt đã duyệt: không làm trong hệ thống.

### 2.20. Danh mục sản phẩm

Trạng thái: **ĐÃ CHỐT (bản 2, 29/09/2026) – đóng băng trước khi code.** Mọi thay đổi phải sửa `docs/spec/2.20_san_pham.md` trước.
Liên quan: 2.6 (sản lượng), 2.12 (báo cáo), 2.14 (Lark), 2.17 (điểm làm việc).
**Phụ thuộc:** triển khai bằng migration riêng (0008), KHÔNG gộp với 2.17; nhưng phạm vi theo kho yêu cầu 2.17 (`work_locations`, `work_sessions.work_location_id`) đã có.

#### 2.20.0. Quy tắc gốc

**R-CATALOG.** Danh mục sản phẩm là dữ liệu có vòng đời và không được dùng trạng thái hiện tại để diễn giải lại sản lượng lịch sử. Khi một phiên kết thúc và cửa sổ khai sản lượng được mở, hệ thống xác định tập sản phẩm áp dụng cho phiên đó. Mỗi dòng sản lượng lưu snapshot mã, tên, đơn vị, quy cách kg/đơn vị, thứ tự và tổng khối lượng. Mọi thay đổi tên, quy cách, thứ tự, phạm vi hoặc trạng thái sản phẩm sau đó không được làm thay đổi dữ liệu lịch sử của phiên.

**R-REPORT.** Sản phẩm ngừng sản xuất không xuất hiện trong các phiên mới nhưng vẫn xuất hiện trong lịch sử và báo cáo khi kỳ được xem có dữ liệu của sản phẩm đó. Nếu một sản phẩm có nhiều quy cách trong cùng kỳ báo cáo, hệ thống phải tính tổng kg từ snapshot từng dòng và không được suy ngược tổng kg từ quy cách hiện tại.

**R-SUBMIT.** "Đã chốt danh mục" (dòng quantity = 0 được tạo sẵn) KHÁC "đã khai sản lượng". Chỉ bản khai có trạng thái `submitted` mới là số liệu nhân viên xác nhận; báo cáo phải phân biệt "0 túi đã xác nhận" với "chưa khai".

Nhất quán kiến trúc: kho snapshot theo phiên (2.17) · đơn giá snapshot theo phiên (2.18) · sản phẩm snapshot theo dòng sản lượng (2.20).

#### 2.20.1. Mô hình dữ liệu

##### 2.20.1.1 `products` (nâng cấp bảng hiện có)

| Cột | Ghi chú |
|---|---|
| id | |
| code | UNIQUE trên toàn bảng (kể cả đã ngừng / đã xóa), BẤT BIẾN, KHÔNG tái sử dụng. Chỉ chữ HOA, số, gạch dưới |
| name | trim, không rỗng; unique trong các sản phẩm chưa xóa |
| unit_code / unit_label | mặc định `BAG` / `Túi` |
| kg_per_unit | NUMERIC(10,3) > 0, giới hạn 0,001–1.000. Không dùng float |
| sort_order | integer, KHÔNG cần unique; sắp theo sort_order → code |
| is_active | `false` = Ngừng sản xuất |
| scope | `all` (Chung – MẶC ĐỊNH khi tạo) \| `restricted` |
| deleted_at, deleted_by | soft-delete "tạo nhầm" – ẩn khỏi giao diện nghiệp vụ, vẫn giữ để audit |
| created_by, created_at, updated_at | |

Đổi tên cột hiện có `kg_per_bag` → `kg_per_unit`.

**Đơn vị:** V1 chỉ hỗ trợ đơn vị ĐẾM NGUYÊN (BAG; về sau BOX, PCS dùng được ngay). Đơn vị có phần lẻ như KG cần đổi `quantity` sang NUMERIC ở phiên bản sau – chưa hỗ trợ.

##### 2.20.1.2 Phạm vi áp dụng (khi scope = restricted)

- `product_location_scopes` (product_id, location_id; unique) – mọi nhân viên có PHIÊN tại kho đó.
- `product_employee_scopes` (product_id, employee_id; unique; chỉ nhân viên role employee).
- Là **HỢP** (OR), không phải giao: áp dụng nếu kho của phiên nằm trong các kho được chọn HOẶC nhân viên nằm trong danh sách riêng.
- restricted không chọn ai → không ai thấy; UI cảnh báo "Sản phẩm chưa áp dụng cho ai" (vẫn cho lưu).
- Kho ngừng dùng / nhân viên bị khóa vẫn giữ trong phạm vi (không tự xóa); UI ghi "(ngừng dùng)" / "(đã khóa)".
- Đổi phạm vi: audit `product_scope_changed` (cũ → mới).

##### 2.20.1.3 `output_logs` – thêm trạng thái

| Cột | Ghi chú |
|---|---|
| status | `pending` (vừa chốt danh mục, chưa gửi) · `submitted` (nhân viên đã bấm Xác nhận ít nhất 1 lần) · `locked_unsubmitted` (hết 10 phút mà chưa gửi) |
| opened_at | = thời điểm phiên đóng |
| submitted_at | lần gửi cuối cùng (sửa trong 10 phút cập nhật lại) |
| locked_at | giữ nguyên |

- `pending` + `locked_at <= now` được coi là `locked_unsubmitted`: API đọc trả trạng thái hiệu dụng; worker định kỳ ghi hẳn `locked_unsubmitted` (không bắt buộc tức thời).

##### 2.20.1.4 `output_items` – snapshot (BẤT BIẾN về catalog)

| Cột | Ghi chú |
|---|---|
| product_id | giữ FK |
| product_code_snapshot, product_name_snapshot | |
| unit_code_snapshot, unit_label_snapshot | |
| kg_per_unit_snapshot | NUMERIC(10,3) |
| sort_order_snapshot | INTEGER NOT NULL |
| quantity | đổi tên từ `bags`, INTEGER ≥ 0 |
| total_kg | **GENERATED ALWAYS AS (quantity × kg_per_unit_snapshot) STORED** – DB đảm bảo không lệch |

Không bao giờ tính lại total_kg lịch sử từ `products`.

#### 2.20.2. Chốt danh mục cho phiên

- Tại thời điểm phiên ĐÓNG (ra ca HOẶC quản lý đóng phiên quên – cùng transaction tạo output_log `pending`), tạo sẵn 1 `output_item` quantity = 0 cho mỗi sản phẩm áp dụng, kèm đủ snapshot (gồm sort_order_snapshot).
- Sản phẩm áp dụng = chưa xóa VÀ is_active VÀ (scope = all HOẶC `work_location_id` CỦA PHIÊN thuộc product_location_scopes HOẶC nhân viên thuộc product_employee_scopes), xét tại thời điểm phiên đóng. Kho hiện tại của nhân viên KHÔNG được dùng.
- Không có sản phẩm nào áp dụng → không tạo dòng; output_log vẫn tạo; form hiện "Không có sản phẩm cần khai cho ca này" (không cần gửi, trạng thái giữ pending rồi hết hạn – báo cáo không tính là "chưa khai").
- Trong 10 phút: nhân viên chỉ CẬP NHẬT quantity các dòng đã tạo và bấm **Xác nhận sản lượng** → `submitted`. Sản phẩm ngoài danh sách chốt → `PRODUCT_NOT_IN_SESSION`.
- Mọi thay đổi catalog (ngừng, đổi tên, đổi quy cách, đổi thứ tự, đổi phạm vi) sau thời điểm phiên đóng KHÔNG ảnh hưởng phiên đó.
- Form hiển thị ORDER BY sort_order_snapshot, product_code_snapshot – KHÔNG đọc products.sort_order.

#### 2.20.3. Thao tác danh mục (QUẢN LÝ + GIÁM ĐỐC)

| Thao tác | Điều kiện | Audit |
|---|---|---|
| Thêm | mã hợp lệ, chưa từng tồn tại (kể cả đã xóa) | `product_created` |
| Sửa tên / quy cách / thứ tự | mã không đổi được. Đổi quy cách → cảnh báo "Chỉ áp dụng cho các phiên kết thúc từ bây giờ." | `product_updated` (old → new từng trường) |
| Sửa phạm vi | | `product_scope_changed` |
| Ngừng sản xuất | không điều kiện (cho phép 0 sản phẩm đang sản xuất) | `product_deactivated` |
| Kích hoạt lại | | `product_reactivated` |
| Xóa sản phẩm tạo nhầm | chỉ khi CHƯA từng xuất hiện trong output_items – không phụ thuộc quantity hay bản khai đã gửi hay chưa (`PRODUCT_IN_USE`). Soft-delete | `product_deleted` |

- Đã bỏ `LAST_ACTIVE_PRODUCT`.
- "Đã sử dụng" = đã có ít nhất 1 dòng output_items (kể cả quantity 0 tạo sẵn). Sản phẩm đã sử dụng chỉ được Ngừng sản xuất.

#### 2.20.4. Giao thức khóa

| Thao tác | Khóa |
|---|---|
| Sửa / ngừng / kích hoạt / xóa / sửa phạm vi sản phẩm | `products` FOR UPDATE (1 sản phẩm) trước khi ghi `products` hoặc bảng scope |
| Đóng phiên (ra ca / đóng phiên quên) | sau khi khóa phiên như hiện có: `SELECT … FROM products WHERE chưa xóa AND is_active ORDER BY id FOR SHARE`, rồi mới đọc bảng scope và tạo dòng |

- Hai phía cùng khóa bản ghi `products` → phiên nhận TRỌN catalog cũ hoặc TRỌN catalog mới, không lẫn.
- Luôn khóa theo `id ASC` để tránh deadlock khi nhiều phiên đóng đồng thời. Không thao tác catalog nào khóa `work_sessions` → không tạo vòng chờ với 2.17/2.18.

#### 2.20.5. Báo cáo và hiển thị

- Gom theo `product_code_snapshot` (khóa nhóm lịch sử). Tên hiện hành chỉ là nhãn nhận diện ở bảng tổng hợp; chi tiết phiên và lịch sử luôn dùng `product_name_snapshot`. Nếu trong kỳ có tên snapshot khác tên hiện hành → ghi "tên trong kỳ: …".
- Dòng hiển thị:
  | Bộ lọc | Sản phẩm hiện |
  |---|---|
  | Không lọc | mọi sản phẩm đang sản xuất (kể cả 0) + mọi sản phẩm có dữ liệu trong kỳ (ngừng SX → nhãn "Ngừng SX") |
  | Theo kho K | sản phẩm đang sản xuất hiện áp dụng cho K (scope all hoặc có K) + mọi sản phẩm có dữ liệu ở phiên thuộc K trong kỳ |
  | Theo nhân viên E | sản phẩm hiện áp dụng cho E (all / kho hiện tại của E / riêng E) + mọi sản phẩm E có dữ liệu trong kỳ |
  Sản phẩm đã xóa không bao giờ hiện.
- Chỉ cộng dòng của output_log `submitted`. Thêm chỉ số "Phiên chưa khai sản lượng: N" (locked_unsubmitted có ≥ 1 sản phẩm áp dụng).
- Quy cách:
  - Mọi dòng cùng 1 kg_per_unit_snapshot → "Bột · 1,2 kg/Túi · 200 Túi · 240 kg".
  - Nhiều mức → "Bột · 200 Túi · 270 kg · ⚠ 2 quy cách trong kỳ"; chi tiết từng mức. Không hiện một quy cách duy nhất.
- Lịch sử nhân viên / chi tiết lương: hiển thị snapshot; phiên chưa khai ghi "Chưa khai sản lượng". Đơn vị lấy từ unit_label_snapshot, không hard-code "túi".

#### 2.20.6. Lark / outbox

`output_submitted` (chỉ phát khi submitted) mỗi dòng gửi snapshot:

```json
{"product_id": 1, "product_code": "BOT", "product_name": "Bột", "unit": "Túi",
 "quantity": 20, "kg_per_unit": 1.2, "total_kg": 24.0, "sort_order": 1}
```

`schema_version` = 3. `event_id` vẫn là khóa idempotency duy nhất.

#### 2.20.7. Quyền và giao diện

- Giám đốc được quản lý danh mục nhưng KHÔNG có quyền nhân viên. Thêm `GET /api/catalog/employee-options` (quản lý + giám đốc) chỉ trả: id, code, name, location_id, location_name (không đơn giá, không Telegram, không link mời, không trạng thái khóa ngoài cờ is_active). Không mở `/api/employees` cho giám đốc.
- Quản lý: tab "Quản lý" → tab con "Nhân viên | Kho | Sản phẩm" (kiểm 360px).
- Giám đốc: mục "Danh mục" (Kho, Sản phẩm) trong header/menu Báo cáo.
- Danh sách sản phẩm: mã, tên, "1,2 kg/Túi", chip Đang sản xuất / Ngừng SX, chip phạm vi ("Chung" / "2 kho · 3 nhân viên" / "Chưa áp dụng cho ai"), nút lên/xuống đổi thứ tự, lọc theo phạm vi.
- Form thêm/sửa: mã khóa sau khi tạo; mục "Áp dụng cho": ● Tất cả nhân viên (mặc định) / ○ Chỉ kho và nhân viên được chọn; câu giải thích "Sản phẩm áp dụng nếu nhân viên làm tại một trong các kho được chọn HOẶC nằm trong danh sách nhân viên được chọn riêng."; chọn kho (chip) + tìm chọn nhân viên; "Hiện áp dụng cho N nhân viên".
- Chi tiết nhân viên (quản lý): "Sản phẩm được khai" (chung / qua kho / riêng) – chỉ xem.
- Form khai sản lượng: nút **Xác nhận sản lượng**; sau khi gửi hiện "Đã xác nhận lúc HH:MM"; hết giờ mà chưa gửi hiện "Đã khóa – chưa khai".
- "Xóa sản phẩm tạo nhầm" chỉ hiện khi chưa từng dùng. Số kg dùng dấu phẩy thập phân.

#### 2.20.8. Migration 0008

- products: đổi tên kg_per_bag → kg_per_unit, NUMERIC(10,3), thêm unit_*, scope = 'all', is_active = true, deleted_*.
- Tạo product_location_scopes, product_employee_scopes.
- output_logs: thêm status, opened_at; backfill: có submitted_at → `submitted`; không có và locked_at <= now → `locked_unsubmitted`; còn lại → `pending`.
- output_items: đổi tên bags → quantity; thêm snapshot + sort_order_snapshot, backfill từ products hiện tại.
- total_kg: TRƯỚC khi đổi sang cột generated, kiểm tra mọi dòng cũ `kg = bags × kg_per_bag`; có dòng lệch → DỪNG migration và in danh sách (không tự sửa). Không lệch → đổi `kg` thành `total_kg` GENERATED STORED.
- Phiên cũ thiếu dòng cho một số sản phẩm: KHÔNG tạo thêm.
- Seed: chỉ tạo 7 sản phẩm mặc định khi bảng rỗng; không ghi đè.
- Đếm số dòng output_items / output_logs trước và sau bằng nhau; downgrade chạy được.

### 2.21. Thông báo và tin nhắn riêng

Trạng thái: **ĐÃ CHỐT – đóng băng trước khi code.** Đây là nguồn quy tắc duy nhất cho tính năng thông báo và tin nhắn riêng. Liên quan: 2.2 (vai trò), 2.7 (bot), 2.17 (lọc người nhận theo kho).

#### 2.21.0. Quy tắc gốc

Mọi tin đi qua bot dưới dạng chat 1-1 giữa từng người và bot; không dùng nhóm hay kênh. Một người chỉ đọc được tin mà quyền bên dưới cho phép; không có đường nào để tin của một nhân viên đến nhân viên khác. Mọi thông báo và tin nhắn được lưu vĩnh viễn trong DB, không đồng bộ Lark.

#### 2.21.1. Ai gửi thông báo cho ai

| Người gửi | Đối tượng |
|---|---|
| Giám đốc | Tất cả · Chỉ quản lý · Chỉ nhân viên · Theo kho · Chọn từng người |
| Quản lý | Chỉ nhân viên: Tất cả nhân viên · Theo kho · Chọn từng người |

Chỉ gửi tới người đang hoạt động và đã liên kết Telegram. Màn soạn hiển thị “Sẽ gửi tới N người (bỏ qua M: chưa liên kết / bị khóa)”. Tin phải ghi rõ người gửi: “📢 THÔNG BÁO TỪ GIÁM ĐỐC” hoặc “📢 THÔNG BÁO TỪ QUẢN LÝ [tên]”. Nút dưới tin: “✅ Đã nhận” và “📱 Mở ứng dụng”. Gửi qua `notification_outbox`, chống trùng và xử lý 403/429 như các tin bot hiện có.

#### 2.21.2. Trả lời và tin nhắn tự do

Trả lời thông báo của giám đốc chỉ đến giám đốc. Trả lời thông báo của quản lý X đến X và giám đốc. Tin nhắn tự do của nhân viên hỏi “Gửi tới: 👔 Quản lý / 🏢 Giám đốc”; quản lý chỉ có lựa chọn Giám đốc. Lựa chọn hết hạn sau 10 phút thì hủy và báo gửi lại. Người nhận Reply tin chuyển tiếp chỉ gửi lại đúng người gửi gốc. Chỉ hỗ trợ tin chữ tối đa 2.000 ký tự; ảnh/tệp/sticker trả “Hiện chỉ hỗ trợ tin nhắn chữ”. Người chưa liên kết không được chuyển tiếp.

#### 2.21.3. Quyền xem hội thoại

Hội thoại được xác định theo cặp (nhân viên, kênh) với kênh Quản lý hoặc Giám đốc. Nhân viên chỉ thấy tin của chính mình. Quản lý xem và trả lời kênh Quản lý, không xem kênh Giám đốc. Giám đốc xem và trả lời kênh Giám đốc; xem **chỉ đọc** mọi hội thoại kênh Quản lý và mọi thông báo của quản lý.

#### 2.21.4. Đã nhận

Bấm “✅ Đã nhận” nhiều lần chỉ ghi lần đầu. Nút đổi thành “✅ Đã nhận lúc HH:MM”. Người gửi xem được số đã gửi/đã nhận/chưa nhận và danh sách tương ứng.

#### 2.21.5. Mô hình dữ liệu

Migration 0007 tạo:

- `announcements(id, sender_id, sender_role, audience_type, location_id, body, created_at)`;
- `announcement_recipients(announcement_id, employee_id, telegram_message_id, delivered_at, acknowledged_at)` với unique `(announcement_id, employee_id)`;
- `conversations(id, employee_id, channel)` với unique `(employee_id, channel)`;
- `messages(id, conversation_id, sender_id, direction, body, announcement_id, created_at, read_by)`;
- `message_relays(message_id, chat_id, telegram_message_id)` với unique `(chat_id, telegram_message_id)`;
- `pending_free_messages(employee_id, text, telegram_message_id, expires_at)`.

#### 2.21.6. Giao diện

Quản lý và giám đốc có tab “Tin nhắn” với badge chưa đọc. Quản lý có “Thông báo” (soạn chỉ cho nhân viên) và “Hộp thư” kênh Quản lý. Giám đốc có thông báo của mình và của quản lý, hộp thư kênh Giám đốc, cùng mục Quản lý chỉ đọc. Soạn thông báo có chọn đối tượng, nội dung tối đa 2.000 ký tự, xem trước số người nhận và hộp xác nhận. Chi tiết hiển thị người gửi, thời gian, nội dung và “Đã nhận N/M”. Hội thoại hiển thị bong bóng, trích dẫn thông báo, ô trả lời; dùng `lib/keyboard.ts`. Nếu 5 tab chật ở 360px, đưa Tin nhắn thành biểu tượng phong bì trên header.

Nút bàn phím cố định “💬 Nhắn quản lý” (nhân viên) và “📢 Gửi thông báo” (quản lý, giám đốc) mở đúng luồng thay vì câu tạm.

#### 2.21.7. Quyền

| API | Nhân viên | Quản lý | Giám đốc |
|---|---|---|---|
| Gửi thông báo tới nhân viên | – | ✓ | ✓ |
| Gửi thông báo tới quản lý | – | – | ✓ |
| Xem thông báo của người khác | – | chỉ của mình | ✓ tất cả |
| Hộp thư kênh Quản lý (đọc / trả lời) | – | ✓ / ✓ | ✓ / – |
| Hộp thư kênh Giám đốc (đọc / trả lời) | – | – | ✓ / ✓ |
