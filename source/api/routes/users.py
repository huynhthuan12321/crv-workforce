from typing import Any

from dishka.integrations.fastapi import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from source.api.middlewares import get_current_user
from source.api.utils import build_user_read
from source.schemas.responses import ApiResponse
from source.schemas.user import UserRead
from source.schemas.user import UserUpdate
from source.services.user_service import UserService

router = APIRouter()


@router.get("/me")
@inject
async def get_me(
    user_service: FromDishka[UserService],
    user_data: dict[str, Any] = Depends(get_current_user),
) -> ApiResponse[UserRead]:
    """Get current user profile."""
    user = await user_service.get_by_telegram_id(user_data["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiResponse(data=build_user_read(user, user_data))


@router.patch("/me")
@inject
async def update_me(
    update_data: UserUpdate,
    user_service: FromDishka[UserService],
    user_data: dict[str, Any] = Depends(get_current_user),
) -> ApiResponse[UserRead]:
    """Update profile (bio, language)."""
    payload = update_data.model_dump(exclude_unset=True)
    user = await user_service.update_user(user_data["id"], payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiResponse(data=build_user_read(user, user_data))


@router.get("/{telegram_id}")
@inject
async def get_user(
    telegram_id: int,
    user_service: FromDishka[UserService],
    user_data: dict[str, Any] = Depends(get_current_user),
) -> ApiResponse[UserRead]:
    """Get user profile by telegram_id."""
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiResponse(data=build_user_read(user))
