## PHẦN 2 – ĐẶC TẢ NGHIỆP VỤ (SPEC)

> Phần này sẽ được AI chép nguyên vào `docs/SPEC.md` ở Giai đoạn 1.

### 2.1. Bối cảnh

- Xưởng sản xuất thực phẩm Cờ Rếp Việt, có thể có nhiều **điểm làm việc**; giao diện V1 gọi điểm làm việc là **Kho** (xem 2.17).
- Nhân viên sản xuất làm **bán thời gian**, không có ca cố định, trả lương **theo giờ thực tế, tính theo ngày, trả ngay trong ngày**.
- Múi giờ duy nhất: **Asia/Ho_Chi_Minh**.

### 2.2. Vai trò

| Vai trò | Mã | Tab trong app | Quyền |
|---|---|---|---|
| Nhân viên | `employee` | Chấm công · Sản lượng · Lịch sử | Vào/ra ca, khai sản lượng, xem dữ liệu **của chính mình**, xem kho được phân công và khoảng cách tại thời điểm chấm công |
| Quản lý | `manager` | Đang làm · Cần xử lý · Duyệt lương · Nhân viên | Xử lý phiên bất thường, sửa giờ công, duyệt lương, quản lý nhân viên, đơn giá, kho và phân công kho. **Không chấm công, không có lương trong app** |
| Giám đốc | `director` | Báo cáo · Cần xử lý · Duyệt lương | Xem báo cáo (chỉ xem). Xử lý phiên bất thường và duyệt lương **giống quản lý** (làm thay khi quản lý vắng, luôn có quyền). Được xem/thêm/sửa/ngừng dùng/kích hoạt kho, lọc báo cáo theo kho. **Không** quản lý nhân viên, **không** cài đơn giá, **không** phân công nhân viên vào kho |

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
- Mọi job thông báo đều chống gửi trùng bằng `notification_outbox.dedupe_key` (unique).

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
- Nếu không còn phiên nào đủ điều kiện → báo "Không có dữ liệu để duyệt".
- Duyệt xong, bot nhắn cho nhân viên số tiền của đợt.
- Hai người cùng duyệt một nhân viên cùng lúc → chỉ một đợt được tạo.

### 2.11. Quản lý nhân viên (chỉ quản lý)

- Thêm nhân viên: họ tên, mã NV, đơn giá giờ, ngày hiệu lực và **kho được phân công ban đầu**. Hệ thống tạo **link mời dùng một lần** (dạng `https://t.me/<bot>/<app>?startapp=<mã_mời>`). Nhân viên mở link → hệ thống gắn Telegram ID vào hồ sơ. Link **dùng một lần, hết hạn sau 7 ngày**; quản lý tạo lại được.
- Khóa / mở khóa nhân viên. Không khóa được người đang có phiên mở.
- Đơn giá: thêm mức mới kèm "hiệu lực từ ngày" (không được trước ngày hôm nay). Giữ lịch sử đơn giá. Phiên đã tạo giữ nguyên `rate_snapshot` của nó.
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
  - Một kho cụ thể: giờ công, túi, kg tính chính xác theo phiên thuộc kho đó; lương hiển thị là **Chi phí theo phiên (chưa làm tròn)** = tổng `amount_raw` của các phiên tại kho đó, kèm ghi chú rằng lương làm tròn theo ngày nên tổng các kho có thể lệch vài nghìn đồng so với "Tất cả kho".
- Chỉ số: tổng giờ công, tổng lương (đã trả + chờ duyệt + cần xử lý trước), tổng túi, tổng kg.
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
- Payload outbox/Lark dùng `schema_version = 2`, cấu trúc lồng có `employee`, `location`/`locations`, `session`/`sessions`; `event_id` là khóa idempotency duy nhất và phải giữ nguyên khi retry.
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
