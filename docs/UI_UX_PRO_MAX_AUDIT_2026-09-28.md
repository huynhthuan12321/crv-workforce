# CRV Workforce — UI/UX Pro Max Audit 2026-09-28

Audit này áp dụng checklist từ skill `ui-ux-pro-max-skill` do người dùng cung cấp, tập trung vào: responsive mobile-first, dark/light theme, token/theme consistency, component states, accessibility, visual hierarchy, touch target, screenshot QA và mức độ khớp SPEC/DESIGN.

Phạm vi kiểm tra: `webapp/src`, `docs/SPEC.md`, `docs/design/DESIGN_NOTES.md`, `docs/design/crv_ui_v1.png`, `docs/IMPLEMENTATION.md`, ảnh trong `docs/screenshots/gd7ab`, `gd7c`, `gd7d`.

Không sửa source app trong audit này.

## A. Executive Summary

Kết luận: **GO WITH CONDITIONS** cho việc tiếp tục kiểm thử UI, nhưng **chưa nên coi UI là hoàn tất** vì còn 2 lỗi P1 ảnh hưởng báo cáo giám đốc / production bundle.

| Mức | Số lỗi | Ghi chú |
|---|---:|---|
| P0 | 0 | Chưa thấy lỗi UI trực tiếp gây sai tiền hoặc sai quyền qua kiểm tra hiện tại. |
| P1 | 2 | Báo cáo hard-code ngày; production bundle còn logic/dữ liệu mock qua `scenario`. |
| P2 | 5 | Touch target 360px, accessibility/focus/motion, chart interaction, input sản lượng, overflow automation timeout. |
| P3 | 2 | Screenshot artifact/tài liệu ảnh stale, tooling lint thiếu config. |

Kết quả lệnh:

| Lệnh | Kết quả |
|---|---|
| `cd webapp && npm test -- --run` | Pass: 11 test files, 31 tests. |
| `cd webapp && npm run build` | Pass: bundle JS 205.42 kB, gzip 63.72 kB; CSS 19.01 kB, gzip 4.54 kB. |
| `cd webapp && npm run test:overflow` | Fail do Puppeteer timeout 30s, không kết luận được overflow toàn bộ. |
| `cd webapp && npm run lint` | Fail do thiếu cấu hình ESLint. |

## B. Source-of-truth mismatches / điểm cần chú ý

| ID | Hạng mục | SPEC / DESIGN | IMPLEMENTATION / CODE | Kết luận |
|---|---|---|---|---|
| UXP-P1-001 | Báo cáo giám đốc theo kỳ hiện tại | SPEC 2.12: báo cáo lọc ngày/tuần/tháng theo kỳ thực tế, không được dùng ngày minh họa. | `ReportsScreen` khởi tạo `date` cố định `"2026-09-27"` và chặn next bằng `"2026-09-27"` tại `webapp/src/features/director/ReportsScreen.tsx:54`, `:83`. | Sai sau ngày 27/09/2026; hôm nay 28/09/2026 app vẫn mặc định Chủ Nhật 27/09. |
| UXP-P1-002 | Mock không lọt production | GĐ7 yêu cầu mock chỉ bật khi `DEV && VITE_MOCK=1`, production bundle không chứa dữ liệu mock. | `ReportsScreen` đọc `?scenario=` ngoài DEV và hard-code `Nguyễn Văn A`, `NV001` tại `webapp/src/features/director/ReportsScreen.tsx:51-56`. Build production grep thấy chuỗi demo/scenario trong `dist/assets/index-*.js`. | Production vẫn chứa dữ liệu/logic mock giám đốc. |
| UXP-P2-003 | Touch target VÀO CA | Thiết kế thực tế yêu cầu vùng bấm tròn tối thiểu 160px. | `.round-action` 176px ở desktop/mobile thường, nhưng media `max-width: 380px` giảm còn 150px tại `webapp/src/styles/globals.css:1211-1215`. | Sai ở 360px; cần giữ ≥160px. |
| UXP-P2-004 | Theme token nhất quán | Skill khuyến nghị dùng token/theme biến CSS, hạn chế hard-code màu ở component. | CSS vẫn có màu hard-code như avatar gradient `#2481cc/#1f9d72`, text `#fff`, active border `#2481cc`, border input stepper `#d8e2ea` tại `webapp/src/styles/globals.css:123-127`, `:634-666`. | Không vỡ UI, nhưng design token chưa sạch; dễ lệch dark/light. |
| UXP-P2-005 | Accessibility states | Skill yêu cầu focus visible, reduced motion, keyboard access, label input. | `Select-String` không thấy `focus-visible` hoặc `prefers-reduced-motion` trong CSS; button reset chỉ có cursor/disabled tại `webapp/src/styles/globals.css:84-93`. | Keyboard/assistive tech chưa đạt. |
| UXP-P3-006 | Screenshot QA | `SO_SANH.md` phải phản ánh ảnh/code mới nhất, tiếng Việt đúng encoding. | `docs/screenshots/gd7c/SO_SANH.md:10` bị mojibake; `:14` còn nói “Cần xử lý GPS” trong khi code hiện đã đổi “Cần xem lại vị trí”; `:27` ghi 228 ca nhưng script hiện có 39 scenario × 2 theme × 3 width = 234 ca. | Tài liệu ảnh bị stale; cần chụp/lưu lại sau fix gần nhất. |

## C. UI/UX Findings

| ID | Screen | Issue | Expected | Actual | Severity |
|---|---|---|---|---|---|
| UXP-P1-001 | Giám đốc → Báo cáo | Ngày báo cáo mặc định và giới hạn “kỳ sau” bị hard-code. | Dùng ngày hiện tại theo giờ Việt Nam hoặc giá trị server; không dùng ngày minh họa. | `useState("2026-09-27")`, `bounds.to < "2026-09-27"`. | P1 |
| UXP-P1-002 | Giám đốc → Báo cáo | Production chịu ảnh hưởng query `?scenario=` và chứa dữ liệu demo. | Scenario/mock chỉ hoạt động trong DEV + `VITE_MOCK=1`. | `ReportsScreen` đọc `scenario` trực tiếp và gán NV001/Nguyễn Văn A trong source production. | P1 |
| UXP-P2-003 | Nhân viên → Chấm công 360px | Nút tròn VÀO CA bị thu còn 150px. | Touch target tròn ≥160px. | Media query `max-width:380px` đặt 150px. | P2 |
| UXP-P2-004 | Toàn app | Focus state keyboard không rõ. | Có `:focus-visible`/ring trên button, tab, input, picker. | Không có rule focus-visible trong CSS. | P2 |
| UXP-P2-005 | Toàn app | Chưa tôn trọng `prefers-reduced-motion`. | Animation/spinner/pulse/transition giảm khi user bật reduced motion. | Không có media query `prefers-reduced-motion`; spinner/pulse luôn chạy. | P2 |
| UXP-P2-006 | Giám đốc → Biểu đồ | Cột SVG có `onClick` + `window.alert`, không keyboard accessible. | Tooltip/selection accessible, có role/focus hoặc nút riêng, không dùng alert thô. | `ReportsScreen.tsx:31` gắn onClick trực tiếp lên `<rect>`. | P2 |
| UXP-P2-007 | Nhân viên → Sản lượng | Input số từng sản phẩm không có label/aria-label. | Mỗi input đọc được “Số túi Bột”, “Số túi Xúc xích”… | `OutputsScreen.tsx:133-142` render `input type=number` không label/aria-label. | P2 |
| UXP-P3-008 | Screenshot docs | So sánh ảnh quản lý bị lỗi encoding/stale. | Tài liệu ảnh phản ánh đúng UI mới nhất. | `SO_SANH.md` có mojibake và text “GPS” cũ. | P3 |
| UXP-P3-009 | Tooling | `npm run lint` không chạy được. | Có ESLint config hoặc bỏ script lint khỏi package nếu không dùng. | ESLint báo không tìm thấy config. | P3 |

## D. Vai trò và màn hình đã kiểm tra

| Vai trò | Màn | Trạng thái audit |
|---|---|---|
| Nhân viên | Chấm công chưa vào ca / đang lấy vị trí / trong ca / sau 18:00 | Ảnh hiện tại tốt ở 390px; phát hiện touch target 360px cần sửa. |
| Nhân viên | Sản lượng | Luồng chính đúng; input thiếu label accessibility; đang hiển thị mã sản phẩm nội bộ (`BOT`, `XUC_XICH`...) dưới tên sản phẩm, chấp nhận được nhưng nên cân nhắc ẩn nếu muốn hoàn toàn “ngôn ngữ người dùng”. |
| Nhân viên | Lịch sử / consent / access errors | Không thấy lỗi lớn qua code và test; AccessScreen đã có test cho INVITE/NOT_REGISTERED. |
| Quản lý | Đang làm / Cần xử lý / Duyệt lương / Nhân viên | Code hiện đã đổi nhãn “Cần xem lại vị trí”; screenshot gd7c vẫn stale ở một số dòng/từ. |
| Giám đốc | Báo cáo / Cần xử lý / Duyệt lương | Báo cáo có lỗi hard-code ngày và mock scenario production; cần sửa trước khi nghiệm thu. |

## E. Design-system / token audit

Điểm tốt:

- Có biến theme `--crv-*`, light/dark riêng trong `webapp/src/styles/globals.css:16-58`.
- Telegram `themeParams` và `themeChanged` được xử lý trong `webapp/src/hooks/useTelegram.ts:16-31`.
- Layout đã có `box-sizing`, `min-width:0`, `overflow-wrap`, grid `minmax(0,1fr)` ở nhiều chỗ.
- Bottom tab dùng nền đặc theo theme tại `webapp/src/styles/globals.css:1091-1105`.

Điểm cần cải thiện:

- Một số màu còn hard-code ở component/token layer, làm design token chưa nhất quán hoàn toàn.
- Chưa có focus ring chuẩn.
- Chưa có reduced-motion.
- `SearchInput` là `<label>` không text, chỉ icon và input placeholder; nên thêm `aria-label` mặc định hoặc label text ẩn.

## F. Screenshot audit

Đã xem trực tiếp:

- `docs/screenshots/gd7ab/01_cham_cong_chua_vao_ca_light.png`: một nút tròn duy nhất, không còn hai vòng tròn xanh ở 390px.
- `docs/screenshots/gd7ab/05_sau_18h_dark.png`: icon trăng trang trí màu nhạt, nút VÀO CA disabled rõ.
- `docs/screenshots/gd7c/06b_duyet_luong_du_lieu_that_light.png`: ảnh vẫn hiển thị “Cần xử lý GPS”, lệch với code hiện tại đã đổi “Cần xem lại vị trí”.
- `docs/screenshots/gd7d/02_bao_cao_tuan_light.png`: biểu đồ và bảng sản lượng có đủ nội dung, nhưng full-page screenshot có tab bar cố định đè lên giữa ảnh làm review trực quan khó hơn.

Khuyến nghị QA ảnh:

1. Chạy lại screenshot sau khi sửa các lỗi P1/P2.
2. Với full-page screenshot, cân nhắc chụp từng scroll position hoặc tạm ẩn/freeze tab bar trong chế độ screenshot để tránh overlay che nội dung.
3. Sửa encoding `SO_SANH.md` gd7c và cập nhật số case overflow thật.

## G. Automated checks

### `npm test -- --run`

```text
Test Files  11 passed (11)
Tests       31 passed (31)
Duration    12.74s
```

### `npm run build`

```text
✓ 63 modules transformed.
dist/index.html                   0.57 kB │ gzip:  0.34 kB
dist/assets/index-BCOoag9c.css   19.01 kB │ gzip:  4.54 kB
dist/assets/index-DU2Jeo9Y.js   205.42 kB │ gzip: 63.72 kB
✓ built in 1.13s
```

### `npm run test:overflow`

```text
TimeoutError: Timed out after waiting 30000ms
```

Mock server `http://127.0.0.1:4175` trả 200, nên lỗi nằm trong automation Puppeteer/script hoặc một scenario không đạt `networkidle0`. Không thể kết luận “không tràn ngang” từ lần chạy này.

### `npm run lint`

```text
ESLint couldn't find a configuration file.
```

## H. Test coverage gaps UI

| Logic/UI | Đã có test | Đủ chưa | Thiếu case |
|---|---|---|---|
| AccessScreen lỗi invite/auth | Có | Khá đủ | Có thể thêm snapshot a11y/role. |
| Date/time VN | Có | Khá | Báo cáo giám đốc current-date không có test nên lọt hard-code. |
| Server clock | Có | Khá | Cần test component dùng server clock, không chỉ lib. |
| Overflow | Có script | Chưa ổn định | Script timeout; cần log scenario hiện hành và timeout per page. |
| Dark/light | Có screenshot | Chưa tự động đo contrast | Thêm contrast/a11y automated nếu có. |
| Accessibility | Ít | Thiếu | Focus-visible, reduced motion, input labels, keyboard chart. |
| Production bundle no mock | Có kiểm thủ công trước đó | Thiếu regression | Thêm test/grep build artifact chặn `scenario`, `Nguyễn Văn A`, `mock-token`. |

## I. Recommended Fix Order

### P1

1. Sửa `ReportsScreen` dùng ngày hiện tại theo giờ Việt Nam/server thay vì hard-code `2026-09-27`; `canNext` so với today thực tế.
2. Gate toàn bộ `scenario`/mock initial state trong `ReportsScreen` bằng `import.meta.env.DEV && VITE_MOCK === "1"`; production bundle không được chứa dữ liệu Phụ lục B/mock scenario.

### P2

3. Giữ `.round-action` ≥160px ở `max-width:380px`.
4. Thêm focus-visible ring cho button/input/picker/tab và `prefers-reduced-motion`.
5. Sửa biểu đồ: bỏ `window.alert`, dùng tooltip/state accessible hoặc nút chi tiết; hỗ trợ keyboard.
6. Thêm label/aria-label cho input sản lượng từng sản phẩm.
7. Làm `test:overflow` ổn định: log scenario trước khi goto, dùng `domcontentloaded` + wait selector thay vì `networkidle0`, tăng timeout hoặc đóng page đúng cách.

### P3

8. Sửa ESLint config hoặc bỏ script lint.
9. Chụp lại screenshot và cập nhật `SO_SANH.md` gd7c/gd7d.

## J. Những gì chưa kiểm chứng được

- Chưa chạy được trên Telegram iOS/Android/Desktop thật trong lượt audit này.
- Chưa kiểm contrast bằng công cụ WCAG/axe.
- Chưa kiểm keyboard-only end-to-end vì app mục tiêu là Telegram mobile, nhưng vẫn nên làm cho accessibility cơ bản.
- Chưa chạy full backend/API trong audit này; báo cáo này tập trung UI theo yêu cầu.

