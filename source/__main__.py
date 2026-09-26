import asyncio
from contextlib import suppress

import uvicorn

from dishka.integrations.aiogram import setup_dishka as setup_aiogram_dishka
from dishka.integrations.fastapi import setup_dishka as setup_fastapi_dishka
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine

from source.config import settings
from source.database import create_tables
from source.factory import create_app
from source.factory import create_api
from source.factory import create_bot
from source.factory import create_container
from source.factory import create_dispatcher
from source.utils import set_default_commands
from source.utils import setup_logger


async def start_polling():
    logger.info("Starting polling...")

    container = create_container()
    if settings.environment != "production":
        engine = await container.get(AsyncEngine)
        await create_tables(engine)
    bot = create_bot()
    dp = create_dispatcher()

    await set_default_commands(bot)

    setup_aiogram_dishka(container=container, router=dp, auto_inject=True)

    dp.shutdown.register(container.close)

    api_stop_event = asyncio.Event()
    api_task = asyncio.create_task(start_api(container, api_stop_event))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        api_stop_event.set()
        await api_task
        await bot.session.close()


async def start_api(container, stop_event: asyncio.Event) -> None:
    app = create_api(container)
    config = uvicorn.Config(
        app,
        host=settings.api.host,
        port=settings.api.port,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    stop_task = asyncio.create_task(stop_event.wait())
    done, _ = await asyncio.wait(
        {server_task, stop_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if stop_task in done:
        server.should_exit = True
        await server_task
    else:
        stop_task.cancel()
        with suppress(asyncio.CancelledError):
            await stop_task


def main_webhook():
    logger.info("Starting webhook...")
    container = create_container()
    bot = create_bot()
    dp = create_dispatcher()
    app = create_app(bot=bot, dp=dp, container=container)

    setup_aiogram_dishka(container=container, router=dp)
    setup_fastapi_dishka(container=container, app=app)

    uvicorn.run(
        app,
        host=settings.webhook.host,
        port=settings.webhook.port,
        log_config=None,
    )


if __name__ == "__main__":
    setup_logger()

    if settings.tg.webhook_use:
        main_webhook()
    else:
        asyncio.run(start_polling())
