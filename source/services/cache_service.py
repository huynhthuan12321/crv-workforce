from source.infrastructure.cache import CacheBackend


class CacheService:
    def __init__(self, cache: CacheBackend):
        self._cache = cache

    async def get_user_language(self, user_id: int) -> str | None:
        return await self._cache.get(self._lang_key(user_id))

    async def set_user_language(self, user_id: int, lang: str, ttl: int = 3600) -> None:
        await self._cache.set(self._lang_key(user_id), lang, ttl)

    async def invalidate_user_language(self, user_id: int) -> None:
        await self._cache.delete(self._lang_key(user_id))

    @staticmethod
    def _lang_key(user_id: int) -> str:
        return f"user:{user_id}:lang"
