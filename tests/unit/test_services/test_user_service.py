import pytest

from source.database.tools.uow import UnitOfWork
from source.services import UserService


@pytest.mark.unit
async def test_register_user_is_idempotent(session_factory):
    service = UserService(UnitOfWork(session_factory))

    user = await service.register_user(123)
    user_again = await service.register_user(123)

    assert user_again is not None
    assert user_again.user_id == user.user_id
    assert user_again.id == user.id
