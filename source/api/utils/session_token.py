import base64
import hashlib
import hmac
import json
from datetime import datetime, time

from source.config import settings
from source.domain.workforce_errors import fail
from source.utils.clock import VIETNAM_TZ


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_session_token(employee_id: int, now: datetime | None = None) -> str:
    now = now or datetime.now(VIETNAM_TZ)
    expires = datetime.combine(now.date(), time(23, 59, 59), VIETNAM_TZ)
    header = _b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64(json.dumps({"sub": employee_id, "exp": int(expires.timestamp())}, separators=(",", ":")).encode())
    body = f"{header}.{payload}"
    signature = hmac.new(settings.auth.session_secret.get_secret_value().encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def decode_session_token(token: str, now: datetime | None = None) -> int:
    try:
        header, payload, signature = token.split(".")
        body = f"{header}.{payload}"
        expected = hmac.new(settings.auth.session_secret.get_secret_value().encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            raise ValueError
        data = json.loads(_unb64(payload))
        current = int((now or datetime.now(VIETNAM_TZ)).timestamp())
        if int(data["exp"]) < current:
            raise fail("SESSION_EXPIRED", 401)
        return int(data["sub"])
    except Exception as exc:
        if getattr(exc, "code", None):
            raise
        raise fail("SESSION_EXPIRED", 401) from exc
