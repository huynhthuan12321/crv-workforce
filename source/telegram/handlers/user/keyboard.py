from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from source.api.dependencies import session_factory
from source.database.models import EmployeeOrm
from source.enums import EmployeeRole
from source.telegram.keyboards.webapp import app_tab_url

user_keyboard_router = Router(name=__name__)

_BUTTONS = {
    "📋 Lịch sử": ("Mở Lịch sử", "history"),
    "⚠️ Cần xử lý": ("Mở Cần xử lý", "review"),
    "💰 Duyệt lương": ("Mở Duyệt lương", "payroll"),
    "📊 Báo cáo": ("Mở Báo cáo", "reports"),
}


@user_keyboard_router.message(F.text.in_(_BUTTONS))
async def open_tab_from_reply(message: Message) -> None:
    async with session_factory() as session:
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == message.from_user.id))
    if not employee or not employee.is_active:
        await message.answer("Tài khoản chưa được liên kết. Vui lòng xin quản lý gửi link mời.")
        return
    label, tab = _BUTTONS[message.text]
    if tab in {"review", "payroll"} and employee.role not in {EmployeeRole.manager, EmployeeRole.director}:
        await message.answer("Bạn không có quyền mở màn này.")
        return
    if tab == "reports" and employee.role != EmployeeRole.director:
        await message.answer("Bạn không có quyền mở màn này.")
        return
    await message.answer(
        f"{label}.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📱 Mở ứng dụng", url=app_tab_url(tab))
        ]]),
    )


@user_keyboard_router.message(F.text == "💬 Nhắn quản lý")
async def contact_manager(message: Message) -> None:
    await message.answer("Hãy gửi nội dung cần nhắn; bot sẽ hỏi người nhận.")


@user_keyboard_router.message(F.text == "📢 Gửi thông báo")
async def send_announcement_hint(message: Message) -> None:
    await message.answer(
        "Mở tab Tin nhắn để soạn thông báo.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📱 Mở Tin nhắn", url=app_tab_url("messages"))
        ]]),
    )
