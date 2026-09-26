"""Check database and Redis connectivity."""
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from source.config import settings


async def check_postgres() -> tuple[bool, str]:
    try:
        engine = create_async_engine(settings.db.postgres_connection())
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True, "PostgreSQL: OK"
    except Exception as exc:
        return False, f"PostgreSQL: FAIL - {exc}"


async def check_redis() -> tuple[bool, str]:
    try:
        redis = settings.redis.redis_connection()
        await redis.ping()
        await redis.aclose()
        return True, "Redis: OK"
    except Exception as exc:
        return False, f"Redis: FAIL - {exc}"


async def main() -> None:
    results = await asyncio.gather(check_postgres(), check_redis())
    all_ok = all(result[0] for result in results)
    for _, message in results:
        print(message)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
