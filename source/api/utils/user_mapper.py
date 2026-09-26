from typing import Any

from source.database import UserOrm
from source.schemas.user import UserRead


def build_user_read(
    user: UserOrm, user_data: dict[str, Any] | None = None
) -> UserRead:
    payload: dict[str, Any] = {
        "id": user.id,
        "telegram_id": user.user_id,
        "language_code": user.language_code
        or (user_data.get("language_code") if user_data else None)
        or "en",
        "bio": user.bio,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    if user_data:
        payload.update(
            {
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
            }
        )

    return UserRead.model_validate(payload)
