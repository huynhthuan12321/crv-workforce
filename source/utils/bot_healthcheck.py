import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from source.config import settings


async def _main() -> int:
    engine = create_async_engine(settings.db.postgres_connection(), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            healthy = await conn.scalar(text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM bot_heartbeat
                    WHERE id = 1
                      AND beat_at >= now() - interval '2 minutes'
                )
                """
            ))
            return 0 if healthy else 1
    except Exception:
        return 1
    finally:
        await engine.dispose()


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
