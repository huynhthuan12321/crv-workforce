import hashlib
import hmac
import json
from datetime import datetime
from datetime import timezone
from typing import Any
from urllib.parse import parse_qs

from source.domain.workforce_errors import fail


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 3600,
) -> dict[str, Any]:
    """
    Validate initData from Telegram WebApp.
    
    Returns parsed user data if valid, None otherwise.
    Includes auth_date check to prevent replay attacks.
    """
    parsed = parse_qs(init_data, keep_blank_values=True)
    received_hash = parsed.get("hash", [None])[0]
    auth_date_str = parsed.get("auth_date", [None])[0]
    user_data = parsed.get("user", [None])[0]
    if not received_hash or not auth_date_str or not user_data:
        raise fail("INITDATA_INVALID", 401)
    try:
        auth_date = int(auth_date_str)
    except ValueError as exc:
        raise fail("INITDATA_INVALID", 401) from exc
    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    if current_timestamp - auth_date > max_age_seconds:
        raise fail("INITDATA_EXPIRED", 401)
    if auth_date > current_timestamp + 60:
        raise fail("INITDATA_INVALID", 401)

    data_check_string = "\n".join(
        f"{key}={parsed[key][0]}" for key in sorted(parsed.keys()) if key != "hash"
    )
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise fail("INITDATA_INVALID", 401)
    try:
        return json.loads(user_data)
    except json.JSONDecodeError as exc:
        raise fail("INITDATA_INVALID", 401) from exc


def validate_init_payload(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> dict[str, Any]:
    """Validate Telegram initData and return user plus trusted start_param."""
    user = validate_init_data(init_data, bot_token, max_age_seconds)
    parsed = parse_qs(init_data)
    return {
        "user": user,
        "start_param": parsed.get("start_param", [None])[0],
        "auth_date": int(parsed["auth_date"][0]),
    }
