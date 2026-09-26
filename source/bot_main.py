import asyncio

from dishka.integrations.aiogram import setup_dishka
from loguru import logger

from source.factory import create_bot, create_container, create_dispatcher
from source.utils import set_default_commands, setup_logger
from source.api.dependencies import session_factory
from source.workers import build_scheduler, sweep_job, worker_loop


async def run() -> None:
    container = create_container()
    bot = create_bot()
    dispatcher = create_dispatcher()
    setup_dishka(container=container, router=dispatcher, auto_inject=True)
    dispatcher.shutdown.register(container.close)
    await set_default_commands(bot)
    scheduler = build_scheduler(session_factory)
    scheduler.start()
    await sweep_job(session_factory)
    worker_task = asyncio.create_task(worker_loop(bot, session_factory))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("CRV bot polling started")
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        worker_task.cancel()
        await bot.session.close()


def main() -> None:
    setup_logger()
    asyncio.run(run())


if __name__ == "__main__":
    main()
