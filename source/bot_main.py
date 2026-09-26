import asyncio

from aiogram.types import MenuButtonWebApp, WebAppInfo
from dishka.integrations.aiogram import setup_dishka
from loguru import logger
from sqlalchemy import text

from source.factory import create_bot, create_container, create_dispatcher
from source.utils import set_default_commands, setup_logger
from source.api.dependencies import engine, session_factory
from source.config import settings
from source.workers import build_scheduler, run_startup_jobs, worker_loop


BOT_ADVISORY_LOCK_ID = 910202601


async def run() -> None:
    lock_conn = await engine.connect()
    locked = await lock_conn.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": BOT_ADVISORY_LOCK_ID})
    if not locked:
        logger.error("Another bot instance is already running; advisory lock is held")
        await lock_conn.close()
        return
    container = create_container()
    bot = create_bot()
    dispatcher = create_dispatcher()
    setup_dishka(container=container, router=dispatcher, auto_inject=True)
    dispatcher.shutdown.register(container.close)
    await set_default_commands(bot)
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Chấm công", web_app=WebAppInfo(url=settings.webapp.url)))
    scheduler = build_scheduler(session_factory)
    scheduler.start()
    await run_startup_jobs(session_factory)
    worker_task = asyncio.create_task(worker_loop(bot, session_factory))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("CRV bot polling started")
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        worker_task.cancel()
        await bot.session.close()
        await lock_conn.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": BOT_ADVISORY_LOCK_ID})
        await lock_conn.close()


def main() -> None:
    setup_logger()
    asyncio.run(run())


if __name__ == "__main__":
    main()
