from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import select

from source.api.dependencies import session_factory
from source.config import settings
from source.database.models import EmployeeOrm
from source.telegram.keyboards import get_webapp_keyboard, role_reply_keyboard

user_commands_router = Router(name=__name__)


@user_commands_router.message(CommandStart())
async def start(message: Message) -> None:
    async with session_factory() as session:
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == message.from_user.id))
    if employee and employee.is_active:
        await message.answer(
            f"Xin chào {employee.full_name}. Mở ứng dụng để chấm công.",
            reply_markup=get_webapp_keyboard(settings.webapp.url, "Mở ứng dụng chấm công"),
        )
        await message.answer("Bạn có thể dùng các nút bên dưới để mở nhanh.", reply_markup=role_reply_keyboard(employee.role))
        return
    await message.answer(
        "Bạn chưa được liên kết. Hãy mở link mời do quản lý gửi.",
        reply_markup=ReplyKeyboardRemove(),
    )
