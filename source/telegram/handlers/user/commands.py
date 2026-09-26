from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from source.api.dependencies import session_factory
from source.config import settings
from source.database.models import EmployeeOrm
from source.telegram.keyboards import get_webapp_keyboard

user_commands_router = Router(name=__name__)


@user_commands_router.message(CommandStart())
async def start(message: Message) -> None:
    async with session_factory() as session:
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == message.from_user.id))
    if employee and employee.is_active:
        text = f"Xin chào {employee.full_name}. Mở ứng dụng để chấm công."
    else:
        text = "Bạn chưa được liên kết. Hãy mở link mời do quản lý gửi."
    await message.answer(text, reply_markup=get_webapp_keyboard(settings.webapp.url, "Mở ứng dụng chấm công"))


@user_commands_router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer("Dùng nút Mở ứng dụng chấm công để vào Mini App CRV Workforce.")


@user_commands_router.message(Command("profile"))
async def profile(message: Message) -> None:
    await message.answer("Mở ứng dụng:", reply_markup=get_webapp_keyboard(settings.webapp.url, "Mở ứng dụng chấm công"))
