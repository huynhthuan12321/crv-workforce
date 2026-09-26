from typing import Any

from dishka.integrations.fastapi import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi import Depends

from source.api.middlewares import get_current_user
from source.api.utils import build_user_read
from source.schemas.responses import ApiResponse
from source.schemas.user import UserRead
from source.services.user_service import UserService

router = APIRouter()


@router.post("/validate")
@inject
async def validate_auth(
    user_service: FromDishka[UserService],
    user_data: dict[str, Any] = Depends(get_current_user),
) -> ApiResponse[UserRead]:
    """Validate auth data and get/create user."""
    user = await user_service.get_or_create_user(
        telegram_id=user_data["id"],
        language_code=user_data.get("language_code"),
    )
    return ApiResponse(data=build_user_read(user, user_data))
