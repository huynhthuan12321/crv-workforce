from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import ReplyKeyboardRemove

import source.telegram.handlers.user.commands as commands
from source.database.models import EmployeeOrm


@pytest.mark.asyncio
async def test_start_unlinked_removes_old_reply_keyboard(session_factory, monkeypatch):
    monkeypatch.setattr(commands, "session_factory", session_factory)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=999),
        answer=AsyncMock(),
    )
    await commands.start(message)
    message.answer.assert_awaited_once()
    assert isinstance(message.answer.await_args.kwargs["reply_markup"], ReplyKeyboardRemove)


@pytest.mark.asyncio
async def test_start_locked_removes_old_reply_keyboard(session_factory, monkeypatch):
    async with session_factory() as session, session.begin():
        session.add(EmployeeOrm(code="NVLOCK", full_name="Nhân viên khóa", is_active=False, telegram_id=1001))
    monkeypatch.setattr(commands, "session_factory", session_factory)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1001),
        answer=AsyncMock(),
    )
    await commands.start(message)
    message.answer.assert_awaited_once()
    assert isinstance(message.answer.await_args.kwargs["reply_markup"], ReplyKeyboardRemove)
