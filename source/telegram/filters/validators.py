import re

from aiogram.filters import Filter
from aiogram.types import Message


class AgeValidator(Filter):
    def __init__(self, min_age: int = 1, max_age: int = 120) -> None:
        self._min_age = min_age
        self._max_age = max_age

    async def __call__(self, message: Message) -> bool:
        text = message.text or ""
        if not text.isdigit():
            return False
        age = int(text)
        return self._min_age <= age <= self._max_age


class PhoneValidator(Filter):
    _pattern = re.compile(r"^\+?[1-9]\d{1,14}$")

    async def __call__(self, message: Message) -> bool:
        text = message.text or ""
        return bool(text and self._pattern.match(text))
