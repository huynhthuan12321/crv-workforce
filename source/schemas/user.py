from datetime import datetime

from pydantic import Field

from .base import BaseSchema


class UserBase(BaseSchema):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str = "en"
    bio: str | None = None


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None


class UserUpdate(BaseSchema):
    bio: str | None = Field(None, max_length=500)
    language_code: str | None = Field(None, max_length=10)
