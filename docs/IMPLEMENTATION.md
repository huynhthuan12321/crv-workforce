# CRV Workforce – Module Chấm công V1

Tài liệu này mô tả trạng thái triển khai thực tế của toàn bộ ứng dụng tại thời điểm
`2026-09-27`. Đây là tài liệu vận hành và bàn giao, không thay thế đặc tả nghiệp vụ
gốc. Khi có mâu thuẫn, thứ tự ưu tiên là:

1. `docs/SPEC.md`
2. `docs/DESIGN_NOTES.md`
3. `docs/design/crv_ui_v1.png`
4. Tài liệu này chỉ mô tả cách SPEC đã được hiện thực hóa.

## 1. Phạm vi hệ thống

CRV Workforce là Telegram Mini App nội bộ cho xưởng Cờ Rếp Việt:

- Nhân viên vào ca, ra ca và khai sản lượng.
- Quản lý theo dõi người đang làm, xử lý phiên GPS/phiên quên ra ca, duyệt lương và quản lý nhân viên.
- Giám đốc xem báo cáo tổng hợp, xử lý phiên bất thường và duyệt lương thay quản lý.
- PostgreSQL là nguồn dữ liệu gốc.
- Bot Telegram gửi nhắc việc, thông báo xử lý và thông báo lương.
- Lark chỉ nhận bản sao báo cáo thông qua webhook n8n.
- React Mini App là giao diện duy nhất cho ba vai trò.

Múi giờ nghiệp vụ duy nhất là `Asia/Ho_Chi_Minh`. Thời gian lưu trong PostgreSQL
dùng `timestamptz`; các giá trị trả ra API và tin nhắn được quy về giờ Việt Nam.

## 2. Kiến trúc triển khai

```text
Telegram
   │ initData / start_param
   ▼
nginx :80
   ├── /       → webapp :80
   └── /api/*  → api :8000
                    │
                    ├── PostgreSQL :5432
                    └── Redis :6379

bot ── polling + scheduler + notification worker
  │
  ├── PostgreSQL advisory lock: chỉ một bot chạy lịch
  ├── notification_outbox → Telegram
  └── sync_outbox → n8n webhook → Lark Base
```

### 2.1. Các service Docker

| Service | Công nghệ | Trách nhiệm | Chính sách |
|---|---|---|---|
| `api` | FastAPI + SQLAlchemy async | Auth, API và toàn bộ nghiệp vụ | `restart: unless-stopped` |
| `bot` | aiogram 3 | Polling, menu button, scheduler, worker | Một instance nhờ advisory lock |
| `db` | PostgreSQL 15 Alpine | Nguồn dữ liệu gốc | Bind `127.0.0.1:5432` |
| `redis` | Redis 7 Alpine | Rate limit và cache tùy chọn | Không mở port host |
| `webapp` | React/Vite, nginx tĩnh | Mini App frontend | `restart: unless-stopped` |
| `nginx` | nginx Alpine | Reverse proxy và bảo mật HTTP | Chỉ mở port 80 trong compose hiện tại |

`nginx/nginx.conf` dùng Docker DNS:

```nginx
resolver 127.0.0.11 valid=10s;
set $api_upstream http://api:8000;
proxy_pass $api_upstream;
```

Nhờ vậy nginx có thể nhận IP mới khi container `api` hoặc `webapp` được tạo lại mà
không cần restart nginx.

## 3. Vai trò và quyền

| Vai trò | Tab | Quyền |
|---|---|---|
| `employee` | Chấm công, Sản lượng, Lịch sử | Chỉ xem/sửa dữ liệu của chính mình |
| `manager` | Đang làm, Cần xử lý, Duyệt lương, Nhân viên | Xử lý, duyệt lương, quản lý hồ sơ và đơn giá; không chấm công |
| `director` | Báo cáo, Cần xử lý, Duyệt lương | Xem báo cáo; xử lý/duyệt như quản lý; không quản lý nhân viên/đơn giá |

Mọi endpoint nghiệp vụ yêu cầu token phiên. Ngoại lệ:

- `GET /api/health`
- `POST /api/auth/session`
- `POST /api/auth/redeem-invite`

Kiểm tra quyền nằm ở dependency `employee_only`, `manager_only`,
`manager_or_director` và `require_roles`.

## 4. Xác thực và phiên đăng nhập

### 4.1. Telegram initData

`source/api/utils/telegram_auth.py` kiểm tra chữ ký theo thuật toán Telegram
WebApp:

1. Parse các trường initData.
2. Tạo `data-check-string`.
3. Dẫn xuất secret bằng `WebAppData` và bot token.
4. So sánh HMAC an toàn.
5. Kiểm tra `auth_date`.

Mã lỗi:

| Tình huống | Mã | HTTP |
|---|---|---:|
| Sai hash, thiếu trường, auth_date tương lai quá 60 giây | `INITDATA_INVALID` | 401 |
| initData quá tuổi | `INITDATA_EXPIRED` | 401 |
| Không có hồ sơ nhân viên | `NOT_REGISTERED` | 403 |
| Tài khoản bị khóa | `ACCOUNT_LOCKED` | 403 |
| Invite không hợp lệ | `INVITE_INVALID` | 422 |
| Invite đã dùng | `INVITE_USED` | 422 |
| Invite hết hạn | `INVITE_EXPIRED` | 422 |
| Telegram đã gắn với người khác | `TELEGRAM_ALREADY_LINKED` | 409 |

### 4.2. Token phiên

Sau khi xác thực thành công, backend cấp token ký bằng
`AUTH__SESSION_SECRET`. Token hết hạn vào cuối ngày theo giờ Việt Nam.
Mỗi request vẫn đọc lại employee từ database để tài khoản vừa bị khóa bị chặn ngay,
không phải chờ token hết hạn.

Frontend lưu token trong `sessionStorage`. Khi gặp lỗi phiên, client xóa token và
thử đăng nhập lại bằng initData hiện có; nếu initData cũng hết hạn thì hiển thị
màn hình yêu cầu mở lại Mini App.

### 4.3. Link mời

Link có dạng:

```text
https://t.me/<TG__BOT_USERNAME>/<TG__MINIAPP_SHORT_NAME>?startapp=<invite_code>
```

Invite dùng một lần, mặc định hết hạn sau 7 ngày. Khi tạo link mới cho người chưa
liên kết, các link cũ chưa dùng bị vô hiệu. Mở lại link cũ của chính employee đã
liên kết là idempotent; mở bằng Telegram đã liên kết với employee khác bị từ chối.

`start_param` dạng `tab_*` không đi qua redeem invite; nó chỉ chọn tab sau khi đăng
nhập thành công.

## 5. Quy tắc thời gian, tiền và vị trí

### 5.1. Thời gian

- Server là nguồn thời gian duy nhất.
- `Clock` là abstraction; test dùng `FakeClock`.
- `to_vn()` từ chối datetime không có timezone bằng `INVALID_DATETIME`.
- Datetime có timezone được chuyển bằng `astimezone(Asia/Ho_Chi_Minh)`.
- API serialize ISO 8601 có offset `+07:00`.
- Bot dùng `fmt_time_vn()`, `fmt_date_vn()` và `fmt_money_vn()`.

### 5.2. Vào/ra ca

- Cutoff mặc định: `18:00` giờ Việt Nam.
- Một nhân viên không có hai phiên `open`; database có partial unique index hỗ trợ bảo vệ đồng thời.
- Phiên `needs_review` của ngày trước không chặn vào ca mới.
- GPS cách xưởng trên 100 m: vẫn cho phép nhưng gắn `gps_out_of_range`.
- GPS accuracy trên 100 m: vẫn cho phép nhưng gắn `gps_low_accuracy`.
- Không ghi tọa độ, token, initData hoặc số điện thoại vào log.
- Rate limit check-in/check-out: tối đa một yêu cầu mỗi 3 giây cho mỗi nhân viên và hành động.
  Redis dùng client dùng chung với timeout 0,2 giây; Redis lỗi thì fallback bộ nhớ,
  có cảnh báo giới hạn tần suất.

### 5.3. Tính phút và tiền

```text
minutes = floor((check_out_at - check_in_at) / 60 giây)
amount_raw = minutes × rate_snapshot / 60
day_total = ceil(sum(amount_raw của các phiên đã đóng trong ngày), 1.000đ)
```

Đơn giá được chụp vào `rate_snapshot` tại thời điểm vào ca. Thay đổi đơn giá từ
ngày mai không ảnh hưởng phiên hôm nay.

### 5.4. Sản lượng

Mỗi phiên có bảy mặt hàng:

| Mã | Tên | kg/túi |
|---|---|---:|
| `BOT` | Bột | 1,2 |
| `XUC_XICH` | Xúc xích | 1 |
| `PHO_MAI` | Phô mai | 1 |
| `CHA_BONG` | Chà bông | 1 |
| `SOT_CAM` | Sốt cam | 2 |
| `SOT_TRANG` | Sốt trắng | 2 |
| `BO` | Bơ | 2 |

Bản khai được sửa trong 10 phút từ lúc phiên đóng. Phiên do quản lý đóng bắt đầu
đếm 10 phút từ thời điểm quản lý xử lý. Hết thời hạn, bản khai bị khóa vĩnh viễn.

## 6. Duyệt lương

Phiên đủ điều kiện:

- đã đóng;
- không còn cờ GPS chưa xem;
- không ở `needs_review`;
- chưa thuộc đợt nào.

Phiên `open` không chặn duyệt. Công thức đợt:

```text
day_total_rounded = ceil(tổng thô mọi phiên đã đóng trong ngày, 1.000đ)
batch_amount = max(0, day_total_rounded - tổng các đợt đã trả)
```

Nếu còn phiên đủ điều kiện nhưng `batch_amount = 0`, hệ thống vẫn tạo đợt 0đ,
gắn và khóa phiên. Bot gửi:

```text
Đợt N: 0đ (đã được làm tròn ở đợt trước)
```

Hai người duyệt đồng thời cùng employee chỉ tạo một đợt nhờ `FOR UPDATE` và khóa
transaction. Người còn lại nhận `NO_ELIGIBLE_SESSIONS`.

## 7. Outbox và audit

### 7.1. `sync_outbox`

Thay đổi nghiệp vụ và outbox được ghi cùng transaction:

| Event | Khi ghi |
|---|---|
| `session_closed` | Nhân viên ra ca |
| `session_updated` | Quản lý/giám đốc sửa giờ |
| `output_submitted` | Gửi sản lượng |
| `batch_paid` | Tạo đợt lương |

Worker bot gửi payload đến webhook n8n bằng HMAC
`LARK__SYNC_SECRET`, retry theo trạng thái outbox.

### 7.2. `notification_outbox`

Không có bảng `notification_log` riêng. Chống gửi trùng bằng
`notification_outbox.dedupe_key` unique. Mỗi tin commit riêng để lỗi một tin không
làm mất trạng thái các tin trước.

Telegram 429 tạo `paused_until` toàn cục; worker không gửi tin mới cho tới thời điểm
đó. Telegram 403 đánh dấu `bot_blocked`, không retry.

### 7.3. Audit

Các thao tác quan trọng ghi `audit_log`, gồm:

- sửa giờ phiên;
- đánh dấu cờ đã xem;
- đóng phiên quên ra ca;
- tạo/khóa/mở nhân viên;
- thêm đơn giá;
- liên kết employee với Telegram;
- tạo lại invite;
- duyệt đợt lương.

## 8. Scheduler và bot

Scheduler chỉ chạy trong service `bot`:

- `18:00`: nhắc từng employee còn phiên mở;
- `18:30`: chuyển phiên mở hôm nay sang `needs_review`, báo manager và director;
- `00:05`: quét phiên cũ còn `open`;
- khi khởi động: chạy sweep trước, sau đó chạy reminder/escalate tùy giờ hiện tại.

Các thông báo có nút mở Mini App:

| Loại | Tab |
|---|---|
| Nhắc ra ca | `tab_attendance` |
| Cần xử lý / phiên tồn | `tab_review` |
| Sau khi đóng phiên quên | `tab_outputs` |
| Duyệt lương | `tab_history` |

Bot lấy PostgreSQL advisory lock với isolation level `AUTOCOMMIT`. Kết nối lock
được giữ suốt vòng đời. Worker kiểm tra `SELECT 1` mỗi 60 giây; mất kết nối thì
dừng tiến trình để Docker restart. `bot_healthcheck.py` kiểm tra heartbeat gần đây
trong bảng `bot_heartbeat`.

Khi khởi động bot:

- gọi `set_chat_menu_button` với nút “Chấm công”;
- `/start` của người đã liên kết có nút Mini App;
- người chưa liên kết chỉ nhận hướng dẫn dùng link mời;
- chỉ giữ lệnh `/start`, không còn `/profile` và `/help`.

## 9. API thực tế

Prefix API là `/api`.

### 9.1. Health và auth

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/api/health` | Công khai |
| `POST` | `/api/auth/session` | initData hợp lệ |
| `POST` | `/api/auth/redeem-invite` | initData + invite |
| `GET` | `/api/auth/me` | Token |

### 9.2. Nhân viên

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/api/attendance/today` | employee |
| `POST` | `/api/attendance/check-in` | employee |
| `POST` | `/api/attendance/check-out` | employee |
| `GET` | `/api/outputs/{session_id}` | employee, chính chủ |
| `PUT` | `/api/outputs/{session_id}` | employee, chính chủ |
| `GET` | `/api/history` | employee, chính chủ |
| `GET` | `/api/consent/current` | employee |
| `POST` | `/api/consent` | employee |
| `POST` | `/api/consent/withdraw` | employee |

### 9.3. Quản lý và giám đốc xử lý phiên/lương

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/api/review/pending` | manager/director |
| `GET` | `/api/review/resolved` | manager/director |
| `POST` | `/api/review/{id}/flags-reviewed` | manager/director |
| `POST` | `/api/review/{id}/close` | manager/director |
| `PATCH` | `/api/review/{id}` | manager/director |
| `GET` | `/api/payroll?date=...` | manager/director |
| `GET` | `/api/payroll/{employee_id}?date=...` | manager/director |
| `POST` | `/api/payroll/approve` | manager/director |

Endpoint sửa giờ thực tế là `PATCH /api/review/{id}`, dù prompt gốc từng gọi là
`PUT /api/sessions/{id}`.

### 9.4. Chức năng riêng quản lý

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/api/working-now` | manager |
| `GET` | `/api/employees` | manager |
| `POST` | `/api/employees` | manager |
| `POST` | `/api/employees/{id}/lock` | manager |
| `POST` | `/api/employees/{id}/unlock` | manager |
| `POST` | `/api/employees/{id}/invite` | manager |
| `GET` | `/api/employees/{id}/rates` | manager |
| `POST` | `/api/employees/{id}/rates` | manager |

### 9.5. Chức năng riêng giám đốc

| Method | Path | Vai trò |
|---|---|---|
| `GET` | `/api/reports/employees` | director |
| `GET` | `/api/reports/summary` | director |
| `GET` | `/api/reports/products` | director |
| `GET` | `/api/reports/timeseries` | director |

Báo cáo hỗ trợ `day`, `week`, `month`, lọc `employee_id`; tuần bắt đầu thứ Hai,
tháng theo lịch dương và trả `from`/`to`.

## 10. Mã lỗi nghiệp vụ chính

| Mã | Ý nghĩa |
|---|---|
| `FORBIDDEN` | Không đủ quyền |
| `NOT_REGISTERED` | Chưa có hồ sơ |
| `ACCOUNT_LOCKED` | Employee bị khóa |
| `INITDATA_INVALID` | initData sai hoặc không hợp lệ |
| `INITDATA_EXPIRED` | initData quá hạn |
| `SESSION_EXPIRED` | Token phiên hết hạn |
| `INVALID_DATETIME` | Datetime không có timezone |
| `CHECKIN_AFTER_CUTOFF` | Vào ca từ 18:00 trở đi |
| `SESSION_ALREADY_OPEN` | Đã có phiên mở |
| `NO_OPEN_SESSION` | Không có phiên mở để ra ca |
| `LOCATION_CONSENT_REQUIRED` | Chưa đồng ý vị trí |
| `GPS_FLAG_UNREVIEWED` | Cờ GPS chưa được xem |
| `ALREADY_HANDLED` | Người khác đã xử lý trước |
| `SESSION_OPEN` | Phiên chưa đóng |
| `INVALID_CHECKOUT_TIME` | Giờ ra không hợp lệ |
| `REASON_REQUIRED` | Lý do dưới 5 ký tự |
| `SESSION_LOCKED_PAID` | Phiên đã thuộc đợt trả |
| `SESSION_OVERLAP` | Chồng lấn phiên |
| `OUTPUT_LOCKED` | Sản lượng đã khóa |
| `NOT_OWNER` | Không phải chủ phiên |
| `NO_ELIGIBLE_SESSIONS` | Không còn phiên đủ điều kiện |
| `TOO_FAST` | Vượt rate limit |
| `EMPLOYEE_HAS_OPEN_SESSION` | Không thể khóa người đang trong ca |
| `RATE_DATE_IN_PAST` | Ngày hiệu lực đơn giá đã qua |
| `RATE_DATE_EXISTS` | Đã có đơn giá cùng ngày |

## 11. Giao diện webapp

### 11.1. Nền dùng chung

`webapp/src` được tổ chức theo:

```text
app/                 vòng đời app, routing tab, shell
api/                 HTTP client và chuẩn hóa lỗi
components/          Card, Button, Metric, SearchInput, ErrorBoundary...
features/            màn theo nghiệp vụ
lib/                 date-vn, format, clock, location, haptic, theme
mock/                dữ liệu và toolbar chỉ trong DEV
types/               kiểu API TypeScript
styles/              biến theme và CSS responsive
```

Đã có:

- theme sáng/tối theo Telegram `themeParams` và `themeChanged`;
- fallback `prefers-color-scheme` khi chạy ngoài Telegram;
- `BackButton` cho màn con;
- safe area iPhone;
- haptic khi bấm nút chính/thành công/lỗi nếu Telegram hỗ trợ;
- Error Boundary cấp app/tab với nút tải lại;
- CSS `box-sizing`, grid `minmax(0, 1fr)`, chống tràn ngang;
- tab bar nền đặc theo theme;
- định dạng tiền VND, giờ/ngày Việt Nam;
- LocationManager trước, `navigator.geolocation` fallback với `maximumAge: 0`.

### 11.2. Màn nhân viên

- **Chấm công**: chưa vào ca, đang lấy vị trí, trong ca, GPS ngoài xưởng, sau 18:00,
  ra ca và chuyển thẳng sang Sản lượng.
- **Sản lượng**: stepper và nhập trực tiếp, hiển thị kg/túi, tổng kg, countdown 10 phút,
  tự khóa khi hết thời gian.
- **Lịch sử**: nhóm theo ngày, tổng ngày, đợt đã trả, tiền chờ duyệt, phiên chưa vào
  đợt; không hiển thị tiền cấp phiên.
- **Đồng ý vị trí**: consent version, quyền riêng tư, rút consent.
- **Trạng thái truy cập**: chưa đăng ký, tài khoản khóa, hết phiên, lỗi mạng/502 dễ hiểu.

### 11.3. Màn quản lý

- **Đang làm**: phiên mở hôm nay, mã/tên, giờ vào, phút, cờ GPS.
- **Cần xử lý**: cờ GPS và phiên quên ra ca; khóa cạnh tranh ở backend.
- **Duyệt lương**: chọn tất cả dòng `can_approve`, hộp xác nhận, chi tiết nhân viên,
  sửa phiên, kết quả duyệt.
- **Nhân viên**: danh sách, tìm kiếm, thêm, khóa/mở, link mời, đơn giá và lịch sử đơn giá.

### 11.4. Màn giám đốc

- **Báo cáo**: ngày/tuần/tháng, mũi tên kỳ trước/sau, lọc nhân viên.
- Bốn nhóm chỉ số: giờ công, tổng lương (`Đã trả`, `Tạm tính`, `Tổng`), tổng túi,
  tổng kg.
- Biểu đồ SVG hai trục: cột giờ công, đường lương; tuần có đủ bảy điểm kể cả ngày 0.
- Bảng bảy mặt hàng theo `sort_order`.
- Tái sử dụng nguyên màn Cần xử lý và Duyệt lương.
- Không hiển thị đường dẫn tới quản lý nhân viên, đơn giá hoặc link mời.

## 12. Mock và chụp ảnh

Mock chỉ bật khi:

```text
import.meta.env.DEV && VITE_MOCK=1
```

Dữ liệu mock không được import tĩnh vào production bundle. Mock toolbar hỗ trợ các
kịch bản nhân viên, quản lý và giám đốc; dùng số liệu Phụ lục B, gồm Nguyễn Văn A,
Lê Thị B, Trần Văn C và Phạm Thị D.

Ảnh kiểm thử nằm tại:

- `docs/screenshots/gd7ab/`
- `docs/screenshots/gd7c/`
- `docs/screenshots/gd7d/`

Các file `SO_SANH.md` ghi ảnh sáng/tối và khác biệt còn lại so với thiết kế.

## 13. Database và migration

Migration CRV chính được đóng băng bằng thao tác Alembic tường minh, không phụ thuộc
`Base.metadata` tại thời điểm chạy migration. Bảo đảm:

- partial unique index phiên `open`;
- index employee/date và status;
- unique/check constraint nghiệp vụ;
- datetime `timestamptz`;
- JSONB trên PostgreSQL;
- downgrade theo thứ tự khóa ngoại.

Bảng `users` của template được giữ lại trong lịch sử migration 0001–0002 nhưng bị
bỏ qua khi Alembic autogenerate/check vì CRV không sử dụng.

Seed:

```powershell
python scripts/db_seed.py
python scripts/db_seed.py --demo
python scripts/db_seed.py --reset-demo   # chỉ APP__ENV=development
```

Seed idempotent cho sản phẩm, consent và nhân sự; link mời được tạo mới theo chính
sách vận hành và link cũ chưa dùng bị vô hiệu.

## 14. Cấu hình môi trường

Các nhóm biến chính:

| Nhóm | Ví dụ |
|---|---|
| App | `APP__ENV`, `APP__DOMAIN`, `TZ` |
| Telegram | `TG__BOT_TOKEN`, `TG__BOT_USERNAME`, `TG__MINIAPP_SHORT_NAME` |
| Database | `DB__HOST`, `DB__PORT`, `DB__USER`, `DB__PASSWORD`, `DB__NAME` |
| Redis | `REDIS__HOST`, `REDIS__PORT`, `REDIS__PASSWORD`, `REDIS__DB` |
| Auth | `AUTH__SESSION_SECRET`, `AUTH__INITDATA_MAX_AGE_SECONDS`, `AUTH__DEV_BYPASS` |
| Webapp | `WEBAPP__URL` |
| Workshop | `WORKSHOP__LAT`, `WORKSHOP__LNG`, `WORKSHOP__RADIUS_M` |
| Rules | `RULES__CHECKIN_CUTOFF`, `RULES__REMINDER_AT`, `RULES__ESCALATE_AT`, `RULES__SWEEP_AT`, `RULES__OUTPUT_EDIT_MINUTES`, `RULES__PAY_ROUND_UNIT`, `RULES__INVITE_EXPIRE_DAYS` |
| Lark | `LARK__SYNC_WEBHOOK_URL`, `LARK__SYNC_SECRET` |
| Seed | `SEED__MANAGER_NAME`, `SEED__DIRECTOR_NAME` |

Production bắt buộc:

- mật khẩu DB/Redis không được là `password`;
- `AUTH__SESSION_SECRET` tối thiểu 32 ký tự và không chứa `change-me`;
- `AUTH__DEV_BYPASS=false`;
- `LARK__SYNC_SECRET` và `WEBHOOK__SECRET` không dùng giá trị `development-*`;
- `WEBAPP__URL` phải bắt đầu bằng `https://`;
- PostgreSQL chỉ bind localhost, không mở `0.0.0.0`.

## 15. Lệnh chạy và vận hành

### Local backend

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn source.api_main:app --host 0.0.0.0 --port 8000 --reload
python -m source.bot_main
```

### Local frontend

```powershell
cd webapp
npm install
npm run dev
```

### Docker

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec api alembic upgrade head
```

### Migration

```powershell
alembic upgrade head
alembic downgrade 0002
alembic upgrade head
alembic check
```

### Test backend

```powershell
docker compose up -d db redis
python -m pytest -q
python -m pytest -m postgres -q
```

### Test frontend

```powershell
cd webapp
npm test
npm run build
npm run test:overflow
npm run screenshots:gd7ab
npm run screenshots:gd7c
npm run screenshots:gd7d
```

## 16. Kết quả kiểm thử đã ghi nhận

Các kết quả gần nhất trong quá trình hoàn thiện:

- Backend: `137 passed, 37 warnings` trong lần chạy đầy đủ trước đó.
- Frontend Vitest: `6 test files passed`, `16 tests passed`.
- Frontend build: thành công bằng TypeScript + Vite.
- Overflow: `No horizontal overflow: 148 cases`.
- Screenshot:
  - GĐ7ab: 74 ảnh;
  - GĐ7c: 30 ảnh;
  - GĐ7d: 18 ảnh.

Các test frontend hiện bao phủ:

- date/time Việt Nam;
- định dạng tiền và kg;
- đồng hồ/lương tạm tính;
- LocationManager cho phép/từ chối/không hỗ trợ;
- kỳ ngày/tuần/tháng;
- không tràn ngang ở 360px và 390px, sáng/tối.

## 17. Commit và nhánh triển khai chính

Các mốc chính đã thực hiện:

- GĐ1 + GĐ4: tài liệu nền, service và unit test.
- GĐ2 + GĐ3: migration, seed, auth, consent, invite, phân quyền.
- GĐ3 fix: transaction per request, HTTP integration, Alembic check.
- GĐ5 + GĐ6: schema, history, reports, bot, scheduler, outbox, lock.
- GĐ7a + GĐ7b: nền giao diện và giao diện nhân viên.
- GĐ7c: giao diện quản lý.
- GĐ7d: giao diện giám đốc.
- GĐ7d fix: chi tiết lương, ảnh fullPage, tìm kiếm dùng component chung,
  tab bar nền đặc và biểu đồ đủ bảy cột.

## 18. Những điểm cần kiểm chứng khi triển khai thật

Các mục sau không nên xem là đã được xác nhận chỉ bằng test local:

1. Mở Mini App trên Telegram iOS, Android và Telegram Desktop với quyền vị trí thật.
2. `Telegram.WebApp.LocationManager` trên các phiên bản client khác nhau.
3. HTTPS/tunnel và CSP trong môi trường domain production.
4. Đường đi end-to-end n8n → Lark Base với secret production.
5. Chạy đồng thời nhiều container bot trên PostgreSQL production.
6. Khôi phục sau restart giữa cửa sổ 18:00–18:30 và sau 18:30.
7. Backup/restore PostgreSQL và chính sách xoay secret.
8. Kiểm thử trực tiếp menu button, inline keyboard và deep link trên điện thoại thật.

## 19. Tài liệu liên quan

- [Đặc tả nghiệp vụ](SPEC.md)
- [Kiến trúc](ARCHITECTURE.md)
- [Quy trình đồng bộ Lark](LARK_SYNC.md)
- [Thông báo consent](consent_v1.md)
- [Báo cáo audit](AUDIT_2026-09-26.md)
- [Ghi chú thiết kế](design/DESIGN_NOTES.md)
- [So sánh ảnh GĐ7ab](screenshots/gd7ab/SO_SANH.md)
- [So sánh ảnh GĐ7c](screenshots/gd7c/SO_SANH.md)
- [So sánh ảnh GĐ7d](screenshots/gd7d/SO_SANH.md)

