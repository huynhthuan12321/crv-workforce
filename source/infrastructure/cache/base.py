from typing import Protocol


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None:
        ...

    async def set(self, key: str, value: str, ttl: int) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...
