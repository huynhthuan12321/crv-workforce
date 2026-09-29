from aiogram import F
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from source.api.dependencies import session_factory
from source.database.models import (
    AnnouncementOrm,
    AnnouncementRecipientOrm,
    EmployeeOrm,
    MessageOrm,
    MessageRelayOrm,
)
from source.enums import EmployeeRole
from source.services.messaging import MessagingService

user_messages_router = Router(name=__name__)

_REPLY_KEYBOARD_TEXTS = {
    "📱 Chấm công", "📱 Mở app", "📋 Lịch sử", "💬 Nhắn quản lý",
    "⚠️ Cần xử lý", "💰 Duyệt lương", "📊 Báo cáo", "📢 Gửi thông báo",
}


@user_messages_router.message((F.photo | F.document | F.sticker), StateFilter(None))
async def unsupported_message(message: Message) -> None:
    await message.answer("Hiện chỉ hỗ trợ tin nhắn chữ.")


@user_messages_router.message(F.text, StateFilter(None))
async def echo(message: Message) -> None:
    async with session_factory() as session, session.begin():
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == message.from_user.id))
        if not employee or not employee.is_active:
            await message.answer("Tài khoản chưa được liên kết. Vui lòng xin quản lý gửi link mời.")
            return
        if len(message.text or "") > 2000:
            await message.answer("Tin nhắn tối đa 2.000 ký tự.")
            return
        if message.text in _REPLY_KEYBOARD_TEXTS:
            return
        if message.reply_to_message:
            relay = await session.scalar(select(MessageRelayOrm).where(
                MessageRelayOrm.chat_id == message.chat.id,
                MessageRelayOrm.telegram_message_id == message.reply_to_message.message_id,
            ))
            recipient = None
            announcement_id = None
            if relay:
                original = await session.get(MessageRelayOrm, relay.id)
                linked = await session.get(MessageOrm, relay.message_id)
                recipient = await session.get(EmployeeOrm, linked.sender_id) if linked else None
            if not recipient:
                announcement_recipient = await session.scalar(select(AnnouncementRecipientOrm).where(
                    AnnouncementRecipientOrm.employee_id == employee.id,
                    AnnouncementRecipientOrm.telegram_message_id == message.reply_to_message.message_id,
                ))
                if announcement_recipient:
                    announcement = await session.get(AnnouncementOrm, announcement_recipient.announcement_id)
                    if announcement:
                        recipient = await session.get(EmployeeOrm, announcement.sender_id)
                        announcement_id = announcement.id
            if recipient:
                await MessagingService(session).send_message(
                    employee, recipient, message.text, "director" if recipient.role == EmployeeRole.director else "manager",
                    announcement_id,
                )
                await message.answer("Đã gửi tới người gửi gốc.")
                return
        pending = await MessagingService(session).create_pending_free_message(
            employee, message.text, message.message_id,
        )
        await message.answer(
            "Gửi tới:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="👔 Quản lý", callback_data=f"free_target:manager:{pending.id}"),
                InlineKeyboardButton(text="🏢 Giám đốc", callback_data=f"free_target:director:{pending.id}"),
            ]]) if employee.role == EmployeeRole.employee else InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏢 Giám đốc", callback_data=f"free_target:director:{pending.id}"),
            ]]),
        )
