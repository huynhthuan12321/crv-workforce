"""Seed database with sample data."""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from source.config import settings
from source.database import create_tables
from source.database.tools.uow import UnitOfWork


async def seed_database() -> None:
    engine = create_async_engine(settings.db.postgres_connection())
    await create_tables(engine)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    uow = UnitOfWork(session_factory)

    test_users = [
        {"user_id": 111111},
        {"user_id": 222222, "language_code": "ru"},
        {"user_id": 333333},
    ]

    async with uow:
        for user_data in test_users:
            existing = await uow.users.get(user_data["user_id"])
            if not existing:
                await uow.users.add(user_data)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
