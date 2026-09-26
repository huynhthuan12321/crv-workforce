from collections.abc import Sequence
from typing import Any

from source.database import AbstractUnitOfWork
from source.database import UserOrm

from .base import BaseService


class UserService(BaseService[UserOrm]):
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        super().__init__(uow)

    async def register_user(
        self,
        user_id: int,
    ) -> UserOrm:
        try:
            async with self._uow:
                user_data = {
                    "user_id": user_id,
                }

                user = await self._uow.users.get(user_id)

                if not user:
                    try:
                        user = await self._uow.users.add(user_data)
                        self.log_operation("user_registered", user_id=user_id)
                    except ValueError:
                        await self._uow.rollback()
                        user = await self._uow.users.get(user_id)

                return user
        except Exception as e:
            self.log_error("register_user", e, user_id=user_id)
            raise

    async def add_user(self, data: dict[str, Any]) -> UserOrm:
        async with self._uow:
            user = await self._uow.users.add(data)
            return user

    async def get_user(self, user_id: int) -> UserOrm | None:
        async with self._uow:
            user = await self._uow.users.get(user_id)
            return user

    async def update_user(self, user_id: int, data: dict[str, Any]) -> UserOrm | None:
        try:
            async with self._uow:
                updated_user = await self._uow.users.update(user_id, data)
                self.log_operation(
                    "user_updated",
                    user_id=user_id,
                    fields=list(data.keys()),
                )
                return updated_user
        except Exception as e:
            self.log_error(
                "update_user",
                e,
                user_id=user_id,
                fields=list(data.keys()),
            )
            raise

    async def delete_user(self, user_id: int) -> None:
        try:
            async with self._uow:
                await self._uow.users.delete(user_id=user_id)
                self.log_operation("user_deleted", user_id=user_id)
        except Exception as e:
            self.log_error("delete_user", e, user_id=user_id)
            raise

    async def add_user_by_filters(self, data: dict[str, Any]) -> UserOrm:
        return await self.add_user(data)

    async def get_user_by_filters(self, **filters: Any) -> UserOrm | None:
        async with self._uow:
            return await self._uow.users.get_by_filters(**filters)

    async def update_users_by_filters(
        self,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> Sequence[UserOrm]:
        async with self._uow:
            updated_users = await self._uow.users.update_by_filters(filters, data)
            return updated_users

    async def delete_users_by_filters(self, **filters: Any) -> None:
        async with self._uow:
            await self._uow.users.delete_by_filters(**filters)

    async def list_users_by_filters(self, **filters: Any) -> Sequence[UserOrm]:
        async with self._uow:
            users = await self._uow.users.list_by_filters(**filters)
            return users

    async def get_by_telegram_id(self, telegram_id: int) -> UserOrm | None:
        return await self.get_user(telegram_id)

    async def get_or_create_user(
        self,
        telegram_id: int,
        language_code: str | None = None,
    ) -> UserOrm:
        try:
            async with self._uow:
                user = await self._uow.users.get(telegram_id)
                if user:
                    if language_code and user.language_code != language_code:
                        user = await self._uow.users.update(
                            telegram_id,
                            {"language_code": language_code},
                        )
                    return user

                user_data: dict[str, Any] = {"user_id": telegram_id}
                if language_code:
                    user_data["language_code"] = language_code
                user = await self._uow.users.add(user_data)
                self.log_operation("user_registered", user_id=telegram_id)
                return user
        except Exception as e:
            self.log_error("get_or_create_user", e, user_id=telegram_id)
            raise

    async def update_bio(self, telegram_id: int, bio: str | None) -> UserOrm | None:
        return await self.update_user(telegram_id, {"bio": bio})
