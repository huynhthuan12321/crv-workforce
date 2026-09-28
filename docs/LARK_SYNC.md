# Đồng bộ Lark qua sync_outbox

Mỗi payload trong `sync_outbox.payload` có `event_id` UUID để n8n/Lark chống ghi trùng. Backend ghi outbox trong cùng transaction với thay đổi nghiệp vụ; nếu transaction rollback thì không có sự kiện được gửi. Từ SPEC 2.17, payload dùng `schema_version = 2` và đưa thông tin nhân viên/kho/phiên vào cấu trúc lồng.

Khi gửi webhook, worker gửi thêm:

- Header `X-CRV-Event-Id`: chính là `event_id` của payload, giữ nguyên qua mọi lần retry.
- Trường `outbox_id` trong body: ID bản ghi `sync_outbox` để truy vết vận hành.

## Idempotency – BẮT BUỘC ở GĐ8

n8n phải ghi Lark theo cơ chế idempotent. Khóa khuyến nghị:

1. Ưu tiên `event_id` cho mọi bảng log/sự kiện.
2. Với bảng trạng thái nghiệp vụ có khóa tự nhiên, dùng upsert theo:
   - `session_closed` / `session_updated`: `event_type + session_id` hoặc cột unique `session_id`.
   - `batch_paid`: `event_type + batch_id`.
   - `output_submitted`: `event_type + session_id + ma_mat_hang`.

Kịch bản test bắt buộc ở GĐ8:

```text
worker gửi event E tới n8n
→ n8n ghi Lark thành công
→ response về worker bị timeout
→ worker retry lại cùng event_id E và cùng outbox_id
→ Lark không có bản ghi trùng, chỉ cập nhật/upsert bản ghi cũ
```

## Payload sự kiện

### `session_closed` (`schema_version = 2`)

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "event_type": "session_closed",
  "occurred_at": "2026-09-26T11:35:00+07:00",
  "employee": {"id": 1, "code": "NV001", "name": "Nguyễn Văn A"},
  "location": {"id": 1, "code": "KHO01", "name": "Xưởng chính"},
  "session": {
    "id": 123,
    "work_date": "2026-09-26",
    "check_in_at": "2026-09-26T06:12:00+07:00",
    "check_out_at": "2026-09-26T11:35:00+07:00",
    "minutes": 323,
    "rate_snapshot": 30000,
    "amount_raw": "161500.0000",
    "flags": [],
    "flag_source": null,
    "closed_by": 1,
    "paid": false,
    "output": []
  }
}
```

### `session_updated`

Giống `session_closed`, bổ sung thông tin thay đổi:

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "event_type": "session_updated",
  "occurred_at": "2026-09-26T11:40:00+07:00",
  "employee": {"id": 1, "code": "NV001", "name": "Nguyễn Văn A"},
  "location": {"id": 1, "code": "KHO01", "name": "Xưởng chính"},
  "session": {"id": 123},
  "old": {
    "check_in_at": "2026-09-26T06:12:00+07:00",
    "check_out_at": "2026-09-26T11:35:00+07:00",
    "minutes": 323,
    "amount_raw": "161500.0000"
  },
  "new": {
    "check_in_at": "2026-09-26T06:10:00+07:00",
    "check_out_at": "2026-09-26T11:35:00+07:00",
    "minutes": 325,
    "amount_raw": "162500.0000"
  },
  "reason": "Sửa theo xác nhận quản lý"
}
```

### `batch_paid`

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "event_type": "batch_paid",
  "occurred_at": "2026-09-26T12:00:00+07:00",
  "employee": {"id": 1, "code": "NV001", "name": "Nguyễn Văn A"},
  "locations": [{"id": 1, "code": "KHO01", "name": "Xưởng chính"}],
  "batch": {
    "id": 10,
    "work_date": "2026-09-26",
    "batch_no": 1,
    "amount": 162000,
    "approved_by": 2,
    "approved_at": "2026-09-26T12:00:00+07:00"
  },
  "sessions": [{"id": 123, "location_id": 1}]
}
```

### `output_submitted`

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "event_type": "output_submitted",
  "occurred_at": "2026-09-26T11:40:00+07:00",
  "employee": {"id": 1, "code": "NV001", "name": "Nguyễn Văn A"},
  "location": {"id": 1, "code": "KHO01", "name": "Xưởng chính"},
  "session": {"id": 123},
  "items": {
    "BOT": 5,
    "XUC_XICH": 3,
    "PHO_MAI": 2,
    "CHA_BONG": 1,
    "SOT_CAM": 1,
    "SOT_TRANG": 0,
    "BO": 0
  }
}
```

## Cột đề xuất cho Lark Base

### `Phien_lam`

| Cột | Kiểu gợi ý | Ghi chú |
|---|---|---|
| `session_id` | Text/Number, unique | Khóa upsert |
| `ma_nv` | Text | Mã nhân viên |
| `ho_ten` | Text | Tên nhân viên |
| `ngay` | Date | Ngày làm |
| `gio_vao` | DateTime | Giờ vào |
| `gio_ra` | DateTime | Giờ ra |
| `so_phut` | Number | Phút làm |
| `don_gia` | Currency/Number | VND/giờ |
| `tien_tho` | Currency/Number | Chưa làm tròn |
| `co_gps` | Multi-select/Text | Danh sách cờ GPS |
| `nguoi_dong` | Text/Number | ID hoặc tên người đóng |
| `da_tra` | Checkbox | Đã thuộc đợt thanh toán |
| `batch_id` | Text/Number | Đợt thanh toán liên quan |
| `updated_at` | DateTime | Thời điểm sync cuối |

### `Dot_thanh_toan`

| Cột | Kiểu gợi ý | Ghi chú |
|---|---|---|
| `batch_id` | Text/Number, unique | Khóa chính |
| `ma_nv` | Text | Mã nhân viên |
| `ho_ten` | Text | Tên nhân viên |
| `ngay` | Date | Ngày làm |
| `dot_so` | Number | Số đợt trong ngày |
| `so_tien` | Currency/Number | VND |
| `nguoi_duyet` | Text/Number | Người duyệt |
| `duyet_luc` | DateTime | Thời điểm duyệt |
| `session_ids` | Text | Danh sách session_id |

### `San_luong`

| Cột | Kiểu gợi ý | Ghi chú |
|---|---|---|
| `session_id` | Text/Number | Một phiên có nhiều dòng mặt hàng |
| `mat_hang` | Single select/Text | Bột, Xúc xích, ... |
| `ma_mat_hang` | Text | Code nội bộ |
| `so_tui` | Number | Số túi |
| `kg_moi_tui` | Number | Hệ số quy đổi |
| `tong_kg` | Number | Tổng kg |
| `submitted_at` | DateTime | Thời điểm khai/sửa |

Khuyến nghị khóa chống trùng cho `San_luong`: `session_id + ma_mat_hang`.
