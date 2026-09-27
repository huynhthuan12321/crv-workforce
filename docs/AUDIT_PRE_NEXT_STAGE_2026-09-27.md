# CRV WORKFORCE — PRE-NEXT-STAGE AUDIT

Ngày audit: 27/09/2026  
Nhánh kiểm tra: `gd7d-giao-dien-giam-doc`  
Phạm vi: đọc/đối chiếu/chạy kiểm tra an toàn; không sửa source, không migration, không deploy.

## A. Executive Summary

Kết luận phát hành: **NO-GO**.

Lý do chính:

1. PostgreSQL integration chưa được xác minh: `python -m pytest -q` có **103 test skip** do thiếu `TEST_DATABASE_URL`; các kiểm tra concurrency, advisory lock, migration trên PostgreSQL và HTTP transaction vì vậy chưa được chứng minh.
2. `alembic check` không chạy được trên môi trường audit vì hostname `db` không resolve.
3. Idempotency end-to-end của n8n/Lark chưa được chứng minh. Backend chỉ gửi `event_id`; repo không chứa workflow n8n/upsert Lark để xác nhận retry sau timeout không tạo bản ghi trùng.
4. Báo cáo `pending` có nguy cơ tính cả phiên `closed` còn cờ GPS chưa được review, khác với tập phiên đủ điều kiện của payroll.

Kết quả lệnh:

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q` | **34 passed, 103 skipped, 1 warning in 5.96s** |
| `npm test` | **6 test files passed, 16 tests passed** |
| `npm run build` | Pass; 61 modules, JS khoảng 198.12 kB, CSS khoảng 17.45 kB |
| `npm run test:overflow` | Pass; 148 cases, không tràn ngang ở 360/390 px |
| `alembic check` | **Không chạy được**: `socket.gaierror`, hostname `db` không resolve |
| Docker hiện trạng | api/db/redis/bot healthy; webapp/nginx running |
| `GET http://localhost/health` | HTTP 200 |
| `GET http://localhost/api/health` | HTTP 200, `{"status":"ok"}` |

Đếm phát hiện trong báo cáo: **P0: 0 đã chứng minh**, **P1: 4**, **P2: 5**, **P3: 2**. Có các rủi ro chưa kiểm chứng được xếp P1 vì ảnh hưởng trực tiếp đến release gate.

## B. Source-of-truth mismatches

| ID | SPEC | DESIGN | IMPLEMENTATION | CODE | Kết luận |
|---|---|---|---|---|---|
| SOT-001 | SPEC 2.10 yêu cầu đợt chỉ gắn các phiên đủ điều kiện, loại cờ GPS chưa review | Không thay đổi | `IMPLEMENTATION.md` mô tả payroll theo SPEC | `PayrollService.eligible_sessions()` lọc cờ; `ReportService._salary_for_days()` không lọc cờ | **Sai lệch ở tầng báo cáo**; pending có thể khác payroll |
| SOT-002 | SPEC 2.14 yêu cầu outbox cùng transaction và chống gửi trùng | DESIGN không quy định chi tiết cơ chế n8n | `docs/LARK_SYNC.md` nói dùng `event_id` để chống trùng | Backend tạo `event_id`, nhưng không có outbox id/transaction id; n8n/Lark không nằm trong repo | **Chưa kiểm chứng end-to-end** |
| SOT-003 | DESIGN yêu cầu các màn theo vai trò và trạng thái | Ảnh có bố cục minh họa | `IMPLEMENTATION.md` ghi các giai đoạn đã làm | UI test chỉ chạy local/mock, chưa chạy Telegram thật và chưa có 430 px | **Chưa đủ bằng chứng thiết bị thật** |
| SOT-004 | SPEC dùng giờ server Asia/Ho_Chi_Minh cho nghiệp vụ | DESIGN hiển thị giờ VN | Backend quy đổi datetime API | Một số countdown/cutoff UI dùng `new Date()` thiết bị | **Rủi ro nhất quán thời gian UI** |

## C. UI/UX Findings

| ID | Screen | Issue | Expected | Actual | Severity |
|---|---|---|---|---|---|
| UI-001 | Sản lượng | Countdown dùng đồng hồ thiết bị | Hiển thị nhất quán với `locked_at` server | `webapp/src/features/outputs/OutputsScreen.tsx:22,52` tính bằng `new Date()` hiện tại của thiết bị | P2 |
| UI-002 | Chấm công | Nút vào ca tự khóa theo đồng hồ thiết bị | Server là nguồn quyết định; UI chỉ phản ánh trạng thái | `AttendanceScreen.tsx:61`; `date-vn.ts:77-85` dùng `new Date()` production | P2 |
| UI-003 | Toàn app | Chưa kiểm chứng Telegram Android/iOS/Desktop | Phải xác nhận safe-area, keyboard, BackButton, LocationManager, haptic | Chỉ có local browser/mock; không có thiết bị Telegram thật | P1 release evidence gap |
| UI-004 | Build asset | Locale template còn trong production bundle | Chỉ phát hành asset được sử dụng | `webapp/dist/locales/en/translation.json` và `ru/translation.json` còn tồn tại sau build | P3 |
| UI-005 | Responsive | Chưa có bằng chứng ở 430 px | Không tràn và bố cục đúng ở 360/390/430 | `npm run test:overflow` hiện kiểm 360/390, 148 cases | P2 |
| UI-006 | UX native | Không dùng `@telegram-apps/telegram-ui` | Không bắt buộc nếu UI hiện tại đạt tiêu chí | `webapp/package.json` không có package này | Không phải lỗi; chỉ là optional improvement |

Các quan sát screenshot `gd7ab`, `gd7c`, `gd7d`: light/dark, tab bar nền đặc, định dạng VND/kg và hierarchy card nhìn nhất quán. Chưa thể xác nhận gesture/back/safe-area trên thiết bị thật.

## D. Business Logic Findings

| ID | Logic | Case | Expected | Actual/evidence | Severity |
|---|---|---|---|---|---|
| BL-001 | Báo cáo lương pending | Có phiên eligible 100.000đ và phiên GPS chưa review 40.000đ | Pending chỉ gồm phiên đủ điều kiện: 100.000đ (sau làm tròn theo ngày) | `source/services/workforce.py:820-825` cộng mọi `closed amount_raw`; không lọc `pay_batch_id`/`_has_unreviewed_flags`. `PayrollService.eligible_sessions()` tại `567-577` có lọc cờ | **P1** |
| BL-002 | Rate snapshot | Đổi rate sau khi check-in rồi checkout | Phiên cũ giữ rate lúc check-in | Có trường `rate_snapshot` và phép tính service dùng trường này; chưa có integration PostgreSQL chạy thật | P2 evidence gap |
| BL-003 | Attendance concurrency | Hai check-in đồng thời | Một open session | Có partial unique index trong model; chưa có test PostgreSQL chạy vì skip | P1 evidence gap |
| BL-004 | Review concurrency | Hai quản lý cùng close | Một thành công, người sau `ALREADY_HANDLED` | Có test `tests/integration/test_postgres_workforce.py`, nhưng bị skip nếu thiếu `TEST_DATABASE_URL` | P1 evidence gap |
| BL-005 | Payroll concurrency | Hai quản lý approve cùng nhân viên | Một batch, request kia `NO_ELIGIBLE_SESSIONS` | Có test integration tương ứng, nhưng chưa chạy PostgreSQL thật trong audit | P1 evidence gap |
| BL-006 | Output/payroll ordering | Checkout, approve, sau đó submit output | Phải đối chiếu SPEC về cửa sổ 10 phút và khóa sau paid | Có service/test unit cho lock boundary; chưa có test end-to-end qua PostgreSQL/HTTP cho thứ tự này | P2 |
| BL-007 | Scheduler restart | 18:05/18:31/00:05 restart | Không bỏ sót, không gửi trùng | Worker có job và dedupe key; integration/Telegram thật chưa chạy | P2 |

## E. Payroll Audit

### E.1 Công thức và tập phiên

`PayrollService.approve_one()` tại `source/services/workforce.py:663-681`:

- lấy `eligible_sessions(..., lock=True)`;
- cộng raw đã trả và raw của phiên eligible;
- làm tròn bằng `ceil_money`;
- amount = `max(0, rounded - paid)`;
- vẫn tạo batch 0đ khi còn phiên eligible.

Phần này phù hợp với SPEC 2.10 về nhiều đợt và batch 0đ ở mức service. Tuy nhiên báo cáo dùng logic khác:

```text
source/services/workforce.py:820-825
raw = SUM(amount_raw) của mọi WorkSession status=closed
pending = ceil(raw) - paid
```

Không có điều kiện loại `flags` chưa review. Vì vậy tình huống A:

```text
Session A: eligible, 100.000đ
Session B: closed, GPS chưa review, 40.000đ
```

có nguy cơ UI/report hiển thị pending theo 140.000đ, trong khi approve chỉ attach Session A. Đây là **P1 business logic risk** cho số tiền hiển thị; cần test regression trước khi chuyển giai đoạn.

### E.2 Multiple batch

Unit test hiện có các ca:

- `tests/unit/test_services/test_workforce_services.py:501` — Phụ lục B/eligibility;
- `:545` — open session không chặn;
- `:577` — batch 0đ khóa phiên;
- `:604` — notification batch 0đ.

Các test này chưa thay thế kiểm chứng PostgreSQL lock thật. Hai test concurrency PostgreSQL nằm ở `tests/integration/test_postgres_workforce.py`, nhưng thuộc 103 test skip.

### E.3 Output window vs payroll

Backend có `OutputLogOrm.locked_at` và service kiểm tra cửa sổ 10 phút; UI countdown chỉ là hiển thị. Chưa có test integration chứng minh đầy đủ chuỗi:

```text
checkout → approve → submit output sau approve
```

Nếu SPEC không quy định rõ approve có khóa output ngay hay chỉ `locked_at` quyết định, đây là **SPEC/evidence gap**, không tự suy diễn kết quả.

## F. Concurrency Audit

| Luồng | Cơ chế đọc được | Test | Trạng thái |
|---|---|---|---|
| Hai check-in | partial unique index `uq_work_sessions_employee_open` trong model/migration | Không thấy test integration tương ứng chạy thật | Chưa chứng minh |
| Hai checkout | row lock/service transaction | Unit rollback có; không có PostgreSQL race chạy trong audit | Chưa chứng minh |
| Hai approve | `with_for_update()` trong eligible sessions | Có integration test, bị skip | Chưa chứng minh |
| Hai close forgotten | lock trạng thái review | Có integration test, bị skip | Chưa chứng minh |
| Hai bot | `acquire_bot_lock()` advisory lock | Có integration test, bị skip | Chưa chứng minh |

## G. Auth/Security Audit

Điểm đã đọc:

- `source/api/utils/telegram_auth.py`: HMAC dùng `WebAppData` + bot token; phân biệt invalid/expired/future; trả `user` và `start_param`.
- `source/api/utils/session_token.py`: token HMAC, hết hạn lúc 23:59:59 giờ VN; payload bị sửa/chữ ký sai bị từ chối.
- `source/api/workforce_auth.py`: kiểm tra `is_active`, role và dev bypass chỉ khi `APP__ENV=development` + `AUTH__DEV_BYPASS`.
- `webapp/src/api/client.ts`: token ở `sessionStorage`; tự login lại một lần khi `SESSION_EXPIRED`; không redeem `tab_*`.

Các giới hạn bằng chứng:

1. Không có Telegram thật để xác minh initData thực tế, reopen link, session expiry sau reload, hoặc role/deep-link trên client thật.
2. Chưa chạy scan runtime production để chứng minh log không chứa token/initData/GPS; source không thấy log payload nhạy cảm trong phần đã rà, nhưng đây là kết luận tĩnh.
3. `X-Dev-Telegram-Id` được log khi bypass (`source/api/workforce_auth.py`), ID không phải token/GPS nhưng vẫn là thông tin định danh cần xem xét trong log retention.
4. IDOR cần chạy integration với DB thật cho các endpoint review/payroll/outputs/history; unit coverage không chứng minh toàn bộ HTTP authorization matrix.

## H. n8n/Lark Idempotency Audit

Backend:

- `source/services/workforce.py:46-47`: `_event()` tạo `event_id` UUID trong payload.
- `source/workers.py:220-232`: worker gửi `{event_type, **row.payload}`; chỉ đánh dấu `sent` sau HTTP 2xx; lỗi sẽ retry.
- `docs/LARK_SYNC.md:3`: tài liệu yêu cầu n8n/Lark chống trùng bằng `event_id`.

Rủi ro:

```text
HTTP POST đến n8n
→ n8n ghi Lark thành công
→ response timeout
→ worker coi là lỗi và retry cùng event
```

Repo không có workflow n8n hoặc mã upsert Lark để chứng minh `event_id` là khóa idempotent. Không có `sync_outbox.id`/transaction id trong payload theo code hiện tại. Vì vậy đây là **P1 integration risk** (có thể thành P0 nếu production không upsert idempotent).

## I. Telegram Real-device Risks

| Hạng mục | Trạng thái |
|---|---|
| Android Telegram | **NOT VERIFIED** |
| iOS Telegram/safe-area/keyboard | **NOT VERIFIED** |
| Telegram Desktop resize/geolocation | **NOT VERIFIED** |
| `LocationManager` thật | **NOT VERIFIED**; chỉ mock/fallback code |
| Haptic feedback | **NOT VERIFIED** |
| BackButton/swipe back | **NOT VERIFIED** |
| Deep link `tab_*` trên Telegram | **NOT VERIFIED** |
| Light/dark theme event `themeChanged` | **SIMULATED/local only** |
| HTTP 502/network error UX | Có code xử lý và mock/local test; thiết bị thật **NOT VERIFIED** |

## J. Test Coverage Gaps

| Logic | Đã có test | Test đủ? | Thiếu case |
|---|---|---|---|
| Auth/initData/token | Unit `tests/unit/test_auth/test_auth_workforce.py:71-245` | Một phần | Telegram initData thật, replay và HTTP middleware trên PostgreSQL |
| Attendance/cutoff/GPS | Unit `test_workforce_services.py:130-210` | Một phần | Race check-in/checkout PostgreSQL, network/device GPS |
| Review | Unit và PostgreSQL integration | Chưa đủ | Integration bị skip; UI hai manager/ALREADY_HANDLED |
| Outputs | Unit `:221` | Một phần | Keyboard/mobile, expiry giữa request, paid session qua HTTP |
| Payroll/rounding | Unit `:501-604` | Một phần | Pending với GPS unreviewed ở report; PostgreSQL locking thật |
| Reports | `tests/unit/test_reports.py` chỉ kiểm bounds tuần/tháng | Chưa đủ | Tổng paid+pending thực tế, employee filter, dữ liệu lệch tiền, pending eligibility |
| Scheduler/notification | `tests/unit/test_workers.py:67-174` | Một phần | Telegram thật, restart thật, persistence/retry qua process |
| Outbox/Lark | Không có test end-to-end n8n/Lark | **Không đủ** | Retry sau timeout và upsert idempotency |
| Concurrency | Integration tests có nhưng skip | **Không đủ** | Chạy DB thật và xác nhận kết quả SQL |
| Timezone | Unit/frontend tests có | Một phần | API/PostgreSQL timestamptz và thiết bị TZ khác VN |
| Frontend states | Vitest + overflow | Một phần | 430 px, Telegram runtime, accessibility/screen reader |
| Deep links | Có logic client không redeem `tab_*` | Một phần | Role matrix và navigation trên Telegram thật |

## K. Recommended Fix Order

### P0

Chưa có P0 đã chứng minh. Trước release phải chứng minh không có duplicate payment/Lark và không sai tiền.

### P1

1. Chạy toàn bộ integration trên PostgreSQL thật: tạo DB test, đặt `TEST_DATABASE_URL`, chạy migration upgrade/downgrade/check, concurrency payroll/review/advisory lock/HTTP transaction.
2. Sửa và thêm regression test cho `ReportService._salary_for_days()` để pending chỉ tính phiên đủ điều kiện, thống nhất với `PayrollService.eligible_sessions()`.
3. Xác nhận workflow n8n/Lark dùng `event_id` làm khóa upsert idempotent; kiểm tra retry sau timeout.
4. Kiểm tra production logging và auth matrix bằng HTTP thật, đặc biệt IDOR và role/deep-link.

### P2

1. Đồng bộ countdown/cutoff UI với server time hoặc ghi rõ sai số thiết bị; thêm test 430 px.
2. Bổ sung integration cho output window vs approve và các boundary scheduler.
3. Kiểm tra accessibility, keyboard, safe-area và error/retry trên thiết bị Telegram.

### P3

1. Loại asset `locales/en`/`locales/ru` nếu không được sử dụng.
2. Rà polish typography/spacing sau khi các rủi ro nghiệp vụ và bằng chứng release hoàn tất.

## L. Release Gate

**NO-GO**

Chưa đủ điều kiện chuyển giai đoạn vì còn P1 chưa xử lý/chưa chứng minh:

- 103 test PostgreSQL bị skip;
- `alembic check` chưa chạy được;
- pending salary report có nguy cơ tính sai tập phiên;
- Lark/n8n retry idempotency chưa có bằng chứng end-to-end;
- Telegram Android/iOS/Desktop và các hành vi runtime quan trọng chưa được xác minh.

Không có thay đổi source code nào được thực hiện trong audit này. File `docs/IMPLEMENTATION.md` đã tồn tại untracked từ trước và được giữ nguyên.
