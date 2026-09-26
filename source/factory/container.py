from collections.abc import AsyncGenerator

from dishka import FromDishka
from dishka import Provider
from dishka import Scope
from dishka import make_async_container
from dishka import provide
from dishka.integrations.aiogram import AiogramProvider
from dishka.integrations.fastapi import FastapiProvider
from fluentogram import TranslatorHub
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from source.config import Settings
from source.config import settings
from source.database import AbstractUnitOfWork
from source.database import UnitOfWork
from source.infrastructure.cache import RedisCache
from source.services import CacheService
from source.services import UserService
from source.utils import I18n
from source.utils import create_translator_hub


class AppProvider(Provider):
    scope = Scope.APP

    @provide
    def provide_settings(self) -> Settings:
        return settings

    @provide
    async def provide_engine(
        self, settings: FromDishka[Settings]
    ) -> AsyncGenerator[AsyncEngine, None]:
        db_url = settings.db.postgres_connection()
        engine_kwargs: dict[str, object] = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
        if db_url.startswith("postgresql"):
            engine_kwargs.update(
                {
                    "pool_size": 20,
                    "max_overflow": 10,
                }
            )
        engine = create_async_engine(db_url, **engine_kwargs)
        yield engine
        await engine.dispose()

    @provide
    def provide_session_factory(
        self, engine: FromDishka[AsyncEngine]
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.APP)
    def provide_translator_hub(self) -> TranslatorHub:
        return create_translator_hub()

    @provide(scope=Scope.REQUEST)
    def provide_i18n(
        self,
        hub: FromDishka[TranslatorHub],
        user_service: FromDishka[UserService],
    ) -> I18n:
        return I18n(hub=hub, user_service=user_service)

    @provide(scope=Scope.APP)
    async def provide_redis(
        self, settings: FromDishka[Settings]
    ) -> AsyncGenerator[Redis, None]:
        redis = settings.redis.redis_connection()
        yield redis
        await redis.aclose()

    @provide(scope=Scope.APP)
    def provide_cache_backend(self, redis: FromDishka[Redis]) -> RedisCache:
        return RedisCache(redis=redis)

    @provide(scope=Scope.APP)
    def provide_cache_service(self, cache: FromDishka[RedisCache]) -> CacheService:
        return CacheService(cache=cache)

    @provide(scope=Scope.REQUEST)
    def provide_uow(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AbstractUnitOfWork:
        return UnitOfWork(session_factory)

    @provide(scope=Scope.REQUEST)
    def provide_user_service(self, uow: AbstractUnitOfWork) -> UserService:
        return UserService(uow=uow)


def create_container():
    return make_async_container(AppProvider(), AiogramProvider(), FastapiProvider())
