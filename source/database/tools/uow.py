import abc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSessionTransaction
from sqlalchemy.ext.asyncio import async_sessionmaker
from types import TracebackType
from typing import Self

from ..repositories import UserRepository


class AbstractUnitOfWork(abc.ABC):
    users: UserRepository

    @abc.abstractmethod
    async def __aenter__(self) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._transaction: AsyncSessionTransaction | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._transaction = await self._session.begin()
        self.users = UserRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session:
            if exc_type:
                await self.rollback()
            else:
                try:
                    await self.commit()
                except Exception:
                    await self.rollback()
                    raise
            await self._session.close()
            self._session = None
            self._transaction = None

    async def commit(self) -> None:
        if self._transaction:
            await self._transaction.commit()

    async def rollback(self) -> None:
        if self._transaction:
            await self._transaction.rollback()
