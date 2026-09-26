from source.dto.base import BaseDTO
from source.enums import UserRole


class UserCreateDTO(BaseDTO):
    user_id: int
    language_code: str = "en"


class UserResponseDTO(BaseDTO):
    id: int
    user_id: int
    role: UserRole
    language_code: str | None
