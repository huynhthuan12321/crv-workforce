from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from source.enums import EmployeeRole


def role_reply_keyboard(role: EmployeeRole | str) -> ReplyKeyboardMarkup:
    role_value = role.value if isinstance(role, EmployeeRole) else str(role)
    # KHÔNG dùng web_app ở ReplyKeyboard: Telegram không gửi initData cho Mini App mở từ nút này
    # → API không xác thực được. Nút chữ → bot trả nút inline (có initData) – xem handlers/user/keyboard.py.
    app_button = KeyboardButton(text="📱 Chấm công" if role_value == EmployeeRole.employee.value else "📱 Mở app")
    if role_value == EmployeeRole.employee.value:
        rows = [[app_button, KeyboardButton(text="📋 Lịch sử")],
                [KeyboardButton(text="💬 Nhắn quản lý")]]
    elif role_value == EmployeeRole.manager.value:
        rows = [[app_button, KeyboardButton(text="⚠️ Cần xử lý")],
                [KeyboardButton(text="💰 Duyệt lương"), KeyboardButton(text="📢 Gửi thông báo")]]
    else:
        rows = [[app_button, KeyboardButton(text="📊 Báo cáo")],
                [KeyboardButton(text="📢 Gửi thông báo")]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


reply_language_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]],
    resize_keyboard=True,
)
