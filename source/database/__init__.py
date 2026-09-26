from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine

from .models import *
from .repositories import *
from .tools.uow import AbstractUnitOfWork as AbstractUnitOfWork
from .tools.uow import UnitOfWork as UnitOfWork

__all__ = [
    "AbstractUnitOfWork",
    "UnitOfWork",
    "create_tables",
    "drop_tables",
]


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully")


async def drop_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Tables dropped successfully")
