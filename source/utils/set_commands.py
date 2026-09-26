import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BotCommand
from aiogram.types import BotCommandScopeAllGroupChats
from aiogram.types import BotCommandScopeAllPrivateChats
from aiogram.types import BotCommandScopeChat
from aiogram.types import BotCommandScopeDefault

from source.config import settings

logger = logging.getLogger(__name__)


def _is_missing_private_chat_error(err: Exception) -> bool:
    text = str(err).lower()
    needles = [
        "chat not found",
        "forbidden",
        "bot was blocked by the user",
        "user is deactivated",
        "peer_id_invalid",
    ]
    return any(needle in text for needle in needles)


async def _safe_delete_commands(bot: Bot, scope, note: str) -> None:
    try:
        await bot.delete_my_commands(scope=scope)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        if _is_missing_private_chat_error(e):
            logger.warning("Skip delete commands for %s: %s", note, e)
        else:
            raise


async def _safe_set_commands(bot: Bot, scope, commands, note: str) -> None:
    try:
        await bot.set_my_commands(commands, scope=scope)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        if _is_missing_private_chat_error(e):
            logger.warning("Skip set commands for %s: %s", note, e)
        else:
            raise


async def set_default_commands(bot: Bot) -> None:
    admins = [int(x) for x in settings.tg.admin_ids]

    common_commands = [
        BotCommand(command="start", description="Launch bot"),
        BotCommand(command="help", description="Instructions for use"),
        BotCommand(command="profile", description="My profile"),
        BotCommand(command="language", description="Change language"),
        BotCommand(command="dialog", description="Open dialog"),
        BotCommand(command="fsm", description="Start fsm"),
    ]

    admin_commands = common_commands + [
        BotCommand(command="admin", description="Admin command"),
    ]

    await _safe_delete_commands(bot, BotCommandScopeDefault(), "default")
    await _safe_delete_commands(bot, BotCommandScopeAllPrivateChats(), "all_private")
    await _safe_delete_commands(bot, BotCommandScopeAllGroupChats(), "all_groups")

    for admin_id in admins:
        scope = BotCommandScopeChat(chat_id=admin_id)
        await _safe_delete_commands(bot, scope, f"admin_chat:{admin_id}")

    await _safe_set_commands(bot, BotCommandScopeDefault(), common_commands, "default")
    await _safe_set_commands(
        bot, BotCommandScopeAllPrivateChats(), common_commands, "all_private"
    )
    await _safe_set_commands(
        bot, BotCommandScopeAllGroupChats(), common_commands, "all_groups"
    )

    for admin_id in admins:
        scope = BotCommandScopeChat(chat_id=admin_id)
        await _safe_set_commands(bot, scope, admin_commands, f"admin_chat:{admin_id}")

    logger.info("Commands loaded. Admin-specific commands applied where chats exist.")
