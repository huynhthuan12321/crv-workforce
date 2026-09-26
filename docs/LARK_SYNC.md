# Đồng bộ Lark qua sync_outbox

Mỗi payload trong `sync_outbox.payload` có `event_id` UUID để n8n/Lark chống ghi trùng. Backend ghi outbox trong cùng transaction với thay đổi nghiệp vụ; nếu transaction rollback thì không có sự kiện được gửi.

## Payload sự kiện

### `session_closed`

```json
{
  "event_id": "uuid",
  "session_id": 123,
  "employee_id": 1,
  "employee_code": "NV001",
  "employee_name": "Nguyễn Văn A",
  "work_date": "2026-09-26",
  "check_in_at": "2026-09-26T06:12:00+07:00",
  "check_out_at": "2026-09-26T11:35:00+07:00",
  "minutes": 323,
  "rate_snapshot": 30000,
  "amount_raw": "161500.0000",
  "flags": [],
  "closed_by": 1,
  "paid": false,
  "output": []
}
```

### `session_updated`

Giống `session_closed`, bổ sung thông tin thay đổi:

```json
{
  "event_id": "uuid",
  "session_id": 123,
  "employee_id": 1,
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
  "event_id": "uuid",
  "batch_id": 10,
  "employee_id": 1,
  "employee_code": "NV001",
  "employee_name": "Nguyễn Văn A",
  "work_date": "2026-09-26",
  "batch_no": 1,
  "amount": 162000,
  "approved_by": 2,
  "approved_at": "2026-09-26T12:00:00+07:00",
  "session_ids": [123]
}
```

### `output_submitted`

```json
{
  "event_id": "uuid",
  "session_id": 123,
  "items": {
    "bot": 5,
    "xuc_xich": 3,
    "pho_mai": 2,
    "cha_bong": 1,
    "sot_cam": 1,
    "sot_trang": 0,
    "bo": 0
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
