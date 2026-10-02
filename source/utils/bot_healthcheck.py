import asyncio
import os

import asyncpg


CONNECT_TIMEOUT_SECONDS = 3
QUERY_TIMEOUT_SECONDS = 3


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


async def _main() -> int:
    conn = None
    try:
        conn = await asyncpg.connect(
            host=_env("DB__HOST", "db"),
            port=int(_env("DB__PORT", "5432")),
            user=_env("DB__USER", "default"),
            password=_env("DB__PASSWORD", "password"),
            database=_env("DB__NAME", "crv_workforce"),
            timeout=CONNECT_TIMEOUT_SECONDS,
            command_timeout=QUERY_TIMEOUT_SECONDS,
        )
        healthy = await asyncio.wait_for(
            conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM bot_heartbeat
                    WHERE id = 1
                      AND beat_at >= now() - interval '2 minutes'
                )
                """
            ),
            timeout=QUERY_TIMEOUT_SECONDS,
        )
        return 0 if healthy else 1
    except Exception:
        return 1
    finally:
        if conn is not None:
            await conn.close()


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
