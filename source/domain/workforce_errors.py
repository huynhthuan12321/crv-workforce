class WorkforceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


MESSAGES = {
    "NOT_REGISTERED": "Bạn chưa được cấp quyền sử dụng ứng dụng.",
    "ACCOUNT_LOCKED": "Tài khoản đã bị khóa.",
    "FORBIDDEN": "Bạn không có quyền thực hiện thao tác này.",
    "INITDATA_INVALID": "Dữ liệu xác thực Telegram không hợp lệ.",
    "INITDATA_EXPIRED": "Phiên Telegram đã hết hạn. Vui lòng đóng và mở lại ứng dụng.",
    "SESSION_EXPIRED": "Phiên đăng nhập đã hết hạn.",
    "INVITE_INVALID": "Link mời không hợp lệ.",
    "INVITE_USED": "Link mời đã được sử dụng.",
    "INVITE_EXPIRED": "Link mời đã hết hạn.",
    "TELEGRAM_ALREADY_LINKED": "Tài khoản Telegram đã được liên kết.",
    "LOCATION_CONSENT_REQUIRED": "Bạn cần đồng ý thu thập vị trí trước khi vào ca.",
    "CHECKIN_AFTER_CUTOFF": "Không thể vào ca từ 18:00.",
    "SESSION_ALREADY_OPEN": "Bạn đang có một phiên làm việc.",
    "NO_OPEN_SESSION": "Không có phiên làm việc đang mở.",
    "NO_RATE": "Chưa có đơn giá hiệu lực.",
    "OUTPUT_LOCKED": "Bản khai sản lượng đã khóa.",
    "NOT_OWNER": "Phiên làm việc không thuộc tài khoản này.",
    "ALREADY_HANDLED": "Mục này đã được xử lý.",
    "INVALID_CHECKOUT_TIME": "Giờ ra không hợp lệ.",
    "INVALID_DATETIME": "Thời gian phải có múi giờ.",
    "REASON_REQUIRED": "Vui lòng nhập lý do từ 5 đến 200 ký tự.",
    "SESSION_LOCKED_PAID": "Phiên đã thanh toán và bị khóa.",
    "SESSION_OPEN": "Không thể sửa phiên đang mở.",
    "SESSION_OVERLAP": "Khoảng thời gian bị chồng lấn với phiên khác.",
    "NO_ELIGIBLE_SESSIONS": "Không có dữ liệu để duyệt.",
}


def fail(code: str, status_code: int = 409, details=None) -> WorkforceError:
    return WorkforceError(code, MESSAGES.get(code, code), status_code, details)
