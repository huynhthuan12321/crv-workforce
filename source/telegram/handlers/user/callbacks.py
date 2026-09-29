from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from dishka import FromDishka
from dishka.integrations.aiogram import inject as aiogram_inject

from source.services import UserService
from source.api.dependencies import session_factory
from source.database.models import EmployeeOrm
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole
from source.services.messaging import MessagingService
from source.telegram.keyboards.webapp import app_tab_url
from source.utils.clock import Clock
from source.utils import I18n

user_callbacks_router = Router(name=__name__)


@user_callbacks_router.callback_query(F.data.startswith("announcement_ack:"))
async def announcement_ack(callback: CallbackQuery) -> None:
    announcement_id = int(callback.data.split(":", 1)[1])
    async with session_factory() as session, session.begin():
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == callback.from_user.id))
        if not employee or not employee.is_active:
            await callback.answer("Tài khoản chưa được liên kết.", show_alert=True)
            return
        data = await MessagingService(session).acknowledge(announcement_id, employee)
    acknowledged = data.get("acknowledged_at", "")
    time_text = acknowledged[11:16] if len(acknowledged) >= 16 else ""
    await callback.answer("Đã ghi nhận.")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Đã nhận lúc {time_text}", callback_data=f"announcement_ack:{announcement_id}"),
            InlineKeyboardButton(text="📱 Mở ứng dụng", url=app_tab_url("messages")),
        ]]))


@user_callbacks_router.callback_query(F.data.startswith("free_target:"))
async def free_target(callback: CallbackQuery) -> None:
    _, target_role, pending_id = callback.data.split(":", 2)
    try:
        pending_pk = int(pending_id)
    except (TypeError, ValueError):
        await callback.answer("Tin nhắn đã hết hạn, vui lòng gửi lại.", show_alert=True)
        return
    async with session_factory() as session, session.begin():
        employee = await session.scalar(select(EmployeeOrm).where(EmployeeOrm.telegram_id == callback.from_user.id))
        if not employee or not employee.is_active:
            await callback.answer("Tin nhắn đã hết hạn.", show_alert=True)
            return
        if target_role not in {"manager", "director"}:
            await callback.answer("Người nhận không hợp lệ.", show_alert=True)
            return
        target_enum = EmployeeRole.director if target_role == "director" else EmployeeRole.manager
        try:
            await MessagingService(session, Clock()).send_pending_free_message(
                employee, pending_pk, target_enum,
            )
        except WorkforceError as exc:
            if exc.code == "FREE_MESSAGE_EXPIRED":
                await callback.answer("Tin nhắn đã hết hạn, vui lòng gửi lại.", show_alert=True)
                return
            if exc.code == "RECIPIENT_UNAVAILABLE":
                await callback.answer("Chưa có người nhận phù hợp.", show_alert=True)
                return
            raise
    await callback.answer("Đã gửi.")
    if callback.message:
        await callback.message.edit_text("Đã gửi thành công.")


@user_callbacks_router.callback_query(F.data == "language_ru")
@aiogram_inject
async def language_ru(
    callback: CallbackQuery,
    i18n: FromDishka[I18n],
    user_service: FromDishka[UserService],
) -> None:
    user = callback.from_user

    await callback.answer("")
    await user_service.update_user(user.id, {"language_code": "ru"})
    i18n.invalidate_cache(user.id)

    changed_language = await i18n(user.id, "language-name-ru")
    text = await i18n(user.id, "changed_language", language=changed_language)

    await callback.message.delete()
    await callback.message.answer(text=text)


@user_callbacks_router.callback_query(F.data == "language_en")
@aiogram_inject
async def language_en(
    callback: CallbackQuery,
    i18n: FromDishka[I18n],
    user_service: FromDishka[UserService],
) -> None:
    user = callback.from_user

    await callback.answer("")
    await user_service.update_user(user.id, {"language_code": "en"})
    i18n.invalidate_cache(user.id)

    changed_language = await i18n(user.id, "language-name-en")
    text = await i18n(user.id, "changed_language", language=changed_language)

    await callback.message.delete()
    await callback.message.answer(text=text)
