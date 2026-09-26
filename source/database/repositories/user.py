from collections.abc import Sequence
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from ..models import UserOrm
from .base import AbstractRepository


class UserRepository(AbstractRepository[UserOrm, int]):
    model = UserOrm

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add(self, data: dict[str, Any]) -> UserOrm:
        user = self.model(**data)
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("User with this user_id already exists") from exc
        return user

    async def get(self, user_id: int) -> UserOrm | None:
        return await self.get_by_filters(user_id=user_id)

    async def update(self, user_id: int, data: dict[str, Any]) -> UserOrm | None:
        user = await self.get(user_id=user_id)

        if user:
            for key, value in data.items():
                if hasattr(user, key) and key not in ["id", "user_id"]:
                    setattr(user, key, value)
            await self.session.flush()
            await self.session.refresh(user)
            return user
        return None

    async def delete(self, **filters: Any) -> None:
        await self.delete_by_filters(**filters)

    async def add_by_filters(self, data: dict[str, Any]) -> UserOrm:
        return await self.add(data)

    async def get_by_filters(self, **filters: Any) -> UserOrm | None:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_by_filters(
        self,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> Sequence[UserOrm]:
        stmt = (
            update(self.model)
            .filter_by(**filters)
            .values(**{k: v for k, v in data.items() if k not in ["id", "user_id"]})
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_filters(self, **filters: Any) -> None:
        stmt = delete(self.model).filter_by(**filters)
        await self.session.execute(stmt)

    async def list_by_filters(self, **filters: Any) -> Sequence[UserOrm]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()
