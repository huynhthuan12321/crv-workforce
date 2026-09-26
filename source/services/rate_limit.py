from collections.abc import Callable
from time import monotonic

from loguru import logger
from redis.asyncio import Redis

from source.config import settings
from source.domain.workforce_errors import fail


class AttendanceRateLimiter:
    def __init__(self, now: Callable[[], float] = monotonic):
        self._redis: Redis | None = None
        self._memory: dict[tuple[int, str], float] = {}
        self._now = now
        self._redis_disabled_until = 0.0
        self._last_warning_at = 0.0

    async def start(self) -> None:
        if self._redis is not None:
            return
        self._redis = Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            username=settings.redis.user,
            password=settings.redis.password.get_secret_value(),
            db=settings.redis.db,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def reset_memory(self) -> None:
        self._memory.clear()

    def _warn_redis_once_per_minute(self, exc: Exception) -> None:
        now = self._now()
        self._redis_disabled_until = now + 60
        if now - self._last_warning_at >= 60:
            self._last_warning_at = now
            logger.warning("Redis rate limit unavailable; falling back to memory limiter: {}", type(exc).__name__)

    async def check(self, employee_id: int, action: str) -> None:
        now = self._now()
        key = f"rl:attendance:{employee_id}:{action}"
        if self._redis is not None and now >= self._redis_disabled_until:
            try:
                ok = await self._redis.set(key, "1", ex=3, nx=True)
                if not ok:
                    raise fail("TOO_FAST", 429)
                return
            except Exception as exc:
                if getattr(exc, "code", None) == "TOO_FAST":
                    raise
                self._warn_redis_once_per_minute(exc)

        mem_key = (employee_id, action)
        previous = self._memory.get(mem_key, 0)
        if now - previous < 3:
            raise fail("TOO_FAST", 429)
        self._memory[mem_key] = now


attendance_rate_limiter = AttendanceRateLimiter()
