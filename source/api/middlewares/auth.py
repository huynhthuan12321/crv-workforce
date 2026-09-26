from typing import Any

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from source.api.utils import validate_init_data
from source.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """
    Extract and validate a user from Telegram initData.

    initData is passed as Authorization: Bearer <initData>
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization required")

    init_data = credentials.credentials
    user_data = validate_init_data(
        init_data, settings.tg.bot_token.get_secret_value()
    )

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authorization data")

    return user_data
