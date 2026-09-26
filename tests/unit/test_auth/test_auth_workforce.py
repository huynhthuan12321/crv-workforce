import hashlib
import hmac
import json
import time
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from source.api.routes.auth import me as me_route
from source.api.utils.session_token import create_session_token, decode_session_token
from source.api.utils.telegram_auth import validate_init_payload
from source.api.workforce_auth import (
    employee_only,
    get_current_employee,
    manager_only,
    manager_or_director,
)
from source.config import settings
from source.config.config_reader import Settings
from source.database.models import (
    ConsentTextOrm,
    EmployeeOrm,
    InviteCodeOrm,
    LocationConsentOrm,
    NotificationOutboxOrm,
)
from source.domain.workforce_errors import WorkforceError
from source.enums import EmployeeRole
from source.services.workforce import AuthService, ConsentService, employee_payload
from source.utils.clock import Clock, VIETNAM_TZ


BOT_TOKEN = "123:test-token"


def sign_init_data(user: dict, auth_date: int | None = None, start_param: str | None = None, token: str = BOT_TOKEN) -> str:
    data = {"user": json.dumps(user, separators=(",", ":")), "auth_date": str(auth_date or int(time.time()))}
    if start_param:
        data["start_param"] = start_param
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def assert_code(exc_info, code: str):
    assert isinstance(exc_info.value, WorkforceError)
    assert exc_info.value.code == code


async def add_employee(session, code="NV001", telegram_id=1001, role=EmployeeRole.employee, active=True):
    employee = EmployeeOrm(code=code, full_name=code, role=role, telegram_id=telegram_id, is_active=active)
    session.add(employee)
    await session.flush()
    return employee


def request_with_header(value: str | None = None) -> Request:
    headers = []
    if value is not None:
        headers.append((b"x-dev-telegram-id", value.encode()))
    return Request({"type": "http", "headers": headers})


@pytest.mark.unit
def test_init_data_valid_invalid_expired_and_future():
    payload = validate_init_payload(sign_init_data({"id": 1001, "username": "a"}, start_param="abc"), BOT_TOKEN, 3600)
    assert payload["user"]["id"] == 1001
    assert payload["start_param"] == "abc"

    bad = sign_init_data({"id": 1001}) + "x"
    with pytest.raises(WorkforceError) as exc:
        validate_init_payload(bad, BOT_TOKEN, 3600)
    assert_code(exc, "INITDATA_INVALID")

    with pytest.raises(WorkforceError) as exc:
        validate_init_payload(sign_init_data({"id": 1001}, int(time.time()) - 3601), BOT_TOKEN, 3600)
    assert_code(exc, "INITDATA_EXPIRED")

    with pytest.raises(WorkforceError) as exc:
        validate_init_payload(sign_init_data({"id": 1001}, int(time.time()) + 61), BOT_TOKEN, 3600)
    assert_code(exc, "INITDATA_INVALID")


@pytest.mark.unit
def test_session_token_valid_expired_tampered_and_bad_signature(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_secret", SecretStr("test-session-secret-change-me-32chars"))
    now = datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ)
    token = create_session_token(123, now)
    assert decode_session_token(token, now + timedelta(hours=1)) == 123
    with pytest.raises(WorkforceError) as exc:
        decode_session_token(token, datetime(2026, 4, 25, 0, 0, tzinfo=VIETNAM_TZ))
    assert_code(exc, "SESSION_EXPIRED")

    header, payload, signature = token.split(".")
    with pytest.raises(WorkforceError):
        decode_session_token(f"{header}.{payload[:-1]}x.{signature}", now)
    with pytest.raises(WorkforceError):
        decode_session_token(f"{header}.{payload}.{signature[:-1]}x", now)


@pytest.mark.unit
async def test_get_current_employee_locked_not_registered_and_dev_bypass(session, monkeypatch):
    monkeypatch.setattr(settings.auth, "session_secret", SecretStr("test-session-secret-change-me-32chars"))
    locked = await add_employee(session, "NV001", 1001, active=False)
    token = create_session_token(locked.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(WorkforceError) as exc:
        await get_current_employee(request_with_header(), credentials, session)
    assert_code(exc, "ACCOUNT_LOCKED")

    token = create_session_token(99999)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(WorkforceError) as exc:
        await get_current_employee(request_with_header(), credentials, session)
    assert_code(exc, "NOT_REGISTERED")

    locked.is_active = True
    monkeypatch.setattr(settings.app, "env", "development")
    monkeypatch.setattr(settings.auth, "dev_bypass", True)
    assert await get_current_employee(request_with_header("1001"), None, session) == locked

    monkeypatch.setattr(settings.auth, "dev_bypass", False)
    with pytest.raises(WorkforceError) as exc:
        await get_current_employee(request_with_header("1001"), None, session)
    assert_code(exc, "SESSION_EXPIRED")


@pytest.mark.unit
def test_settings_rejects_dev_bypass_in_production(monkeypatch):
    monkeypatch.setenv("APP__ENV", "production")
    monkeypatch.setenv("AUTH__DEV_BYPASS", "true")
    monkeypatch.setenv("TG__BOT_TOKEN", "123:test")
    monkeypatch.setenv("WORKSHOP__LAT", "10")
    monkeypatch.setenv("WORKSHOP__LNG", "106")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.unit
async def test_consent_state_and_withdraw_two_managers(session):
    employee = await add_employee(session, "NV001", 1001)
    manager1 = await add_employee(session, "QL001", 2001, EmployeeRole.manager)
    manager2 = await add_employee(session, "QL002", 2002, EmployeeRole.manager)
    now = datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ)
    session.add(ConsentTextOrm(version=1, content="v1", effective_at=now - timedelta(days=1)))
    session.add(LocationConsentOrm(employee_id=employee.id, consent_version=1, consented_at=now))
    await session.flush()
    assert (await me_route(employee, session))["data"]["has_location_consent"] is True

    session.add(ConsentTextOrm(version=2, content="v2", effective_at=now))
    await session.flush()
    assert (await employee_payload(session, employee, now + timedelta(minutes=1)))["has_location_consent"] is False

    session.add(LocationConsentOrm(employee_id=employee.id, consent_version=2, consented_at=now + timedelta(minutes=2)))
    await session.flush()
    await ConsentService(session).withdraw(employee)
    await session.flush()
    assert (await employee_payload(session, employee, now + timedelta(minutes=3)))["has_location_consent"] is False
    notices = (await session.scalars(select(NotificationOutboxOrm))).all()
    assert len(notices) == 2
    assert {notice.chat_id for notice in notices} == {manager1.telegram_id, manager2.telegram_id}


@pytest.mark.unit
async def test_role_permissions():
    employee = EmployeeOrm(role=EmployeeRole.employee)
    manager = EmployeeOrm(role=EmployeeRole.manager)
    director = EmployeeOrm(role=EmployeeRole.director)

    with pytest.raises(WorkforceError) as exc:
        await manager_or_director(employee)
    assert_code(exc, "FORBIDDEN")
    with pytest.raises(WorkforceError) as exc:
        await manager_only(director)
    assert_code(exc, "FORBIDDEN")
    with pytest.raises(WorkforceError) as exc:
        await employee_only(manager)
    assert_code(exc, "FORBIDDEN")


async def make_invite(session, employee, code="invite", expires=None, used_at=None):
    now = Clock().now()
    row = InviteCodeOrm(
        employee_id=employee.id,
        code=code,
        expires_at=expires or now + timedelta(days=1),
        used_at=used_at,
    )
    session.add(row)
    await session.flush()
    return row


@pytest.mark.unit
async def test_redeem_invite_cases(session):
    employee = await add_employee(session, "NV001", None)
    invite = await make_invite(session, employee, "ok")
    data = {"start_param": "ok", "user": {"id": 1001, "username": "nv1"}}
    redeemed = await AuthService(session).redeem_invite(data)
    assert redeemed.telegram_id == 1001
    assert invite.used_at is not None

    reopened = await AuthService(session).redeem_invite(data)
    assert reopened.id == employee.id

    used_employee = await add_employee(session, "NV002", None)
    await make_invite(session, used_employee, "used", used_at=datetime(2026, 4, 24, 8, 0, tzinfo=VIETNAM_TZ))
    with pytest.raises(WorkforceError) as exc:
        await AuthService(session).redeem_invite({"start_param": "used", "user": {"id": 1002}})
    assert_code(exc, "INVITE_USED")

    expired_employee = await add_employee(session, "NV003", None)
    await make_invite(session, expired_employee, "expired", expires=Clock().now() - timedelta(days=1))
    with pytest.raises(WorkforceError) as exc:
        await AuthService(session).redeem_invite({"start_param": "expired", "user": {"id": 1003}})
    assert_code(exc, "INVITE_EXPIRED")

    other = await add_employee(session, "NV004", None)
    await make_invite(session, other, "other")
    with pytest.raises(WorkforceError) as exc:
        await AuthService(session).redeem_invite({"start_param": "other", "user": {"id": 1001}})
    assert_code(exc, "TELEGRAM_ALREADY_LINKED")
