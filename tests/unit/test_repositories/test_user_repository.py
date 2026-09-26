import pytest

from source.database.repositories import UserRepository


@pytest.mark.unit
async def test_add_and_get_user(session):
    repo = UserRepository(session)
    await repo.add({"user_id": 123})
    await session.commit()

    fetched = await repo.get(123)
    assert fetched is not None
    assert fetched.user_id == 123


@pytest.mark.unit
async def test_update_user(session):
    repo = UserRepository(session)
    await repo.add({"user_id": 456})
    await session.commit()

    updated = await repo.update(456, {"language_code": "ru"})
    await session.commit()

    assert updated is not None
    assert updated.language_code == "ru"


@pytest.mark.unit
async def test_add_duplicate_user_raises(session):
    repo = UserRepository(session)
    await repo.add({"user_id": 789})
    await session.commit()

    with pytest.raises(ValueError):
        await repo.add({"user_id": 789})
