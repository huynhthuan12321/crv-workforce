from datetime import datetime
from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from ..tools import TableNameMixin
from .base import Base
from source.enums import UserRole


class UserOrm(Base, TableNameMixin):
    id: Mapped[int] = mapped_column(primary_key=True, comment="PK записи")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        unique=True,
        comment="Внешний ID пользователя (например, Telegram ID)",
    )
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(UserRole),
        default=UserRole.user,
        server_default="user",
        nullable=False,
        comment="Роль пользователя в системе",
    )
    language_code: Mapped[str | None] = mapped_column(
        String(2),
        default="en",
        server_default="en",
        comment="Язык ('ru', 'en' и т.д.)",
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Биография пользователя",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        comment="Когда зарегистрировался",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Когда профиль в последний раз обновлялся",
    )
