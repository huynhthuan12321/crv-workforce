# Configuration Guide

## Overview
Configuration is managed with Pydantic settings in `source/config/config_reader.py`. Values are loaded from `.env` using `__` as a nested delimiter (for example, `TG__BOT_TOKEN`).

## Quick Links
- [Getting Started](../getting-started.md)
- [Deployment](deployment.md)
- [Mini Apps Overview](mini-apps/README.md)

## How Settings Load
The root settings object looks like this:

```python
from source.config import settings

settings.environment
settings.tg.bot_token
settings.webhook.port
settings.db.postgres_connection()
settings.redis.redis_connection()
```

Settings are read from `.env` with these rules:
- Case-insensitive
- Nested fields split by `__`
- Defaults are defined in code

## Required Variables
Minimum required values to run the bot:

```env
TG__BOT_TOKEN=YOUR_BOT_TOKEN
TG__ADMIN_IDS=[123456789]
TG__WEBHOOK_USE=False
TG__WEBHOOK_PATH=/telegram

WEBHOOK__URL=https://your-domain.example
WEBHOOK__HOST=0.0.0.0
WEBHOOK__PORT=8000
WEBHOOK__SECRET=long_random_secret

DB__HOST=db
DB__PORT=5432
DB__USER=botuser
DB__PASSWORD=strong_password
DB__NAME=telegram_bot

REDIS__HOST=redis
REDIS__PORT=6379
REDIS__USER=default
REDIS__PASSWORD=strong_password
REDIS__DB=0

API__HOST=0.0.0.0
API__PORT=8000
API__DEBUG=false

WEBAPP__URL=https://your-webapp.example
```

## Environment
`ENVIRONMENT` changes startup behavior:
- `development` (default in `.env.example`): creates tables on startup
- `production`: does not auto-create tables, assumes Alembic migrations

```env
ENVIRONMENT=development
```

## Telegram Settings

```env
TG__BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
TG__ADMIN_IDS=[5252216460]
TG__WEBHOOK_USE=False
TG__WEBHOOK_PATH=/telegram
```

Notes:
- `TG__ADMIN_IDS` must be a non-empty list of unique, positive IDs.
- `TG__WEBHOOK_USE=True` switches to webhook mode.

## Webhook Settings

```env
WEBHOOK__URL=https://your-domain.example
WEBHOOK__HOST=0.0.0.0
WEBHOOK__PORT=8000
WEBHOOK__SECRET=long_random_secret
```

Notes:
- `WEBHOOK__URL` must be public and accessible from Telegram.
- `WEBHOOK__SECRET` is validated against the `X-Telegram-Bot-Api-Secret-Token` header.
- Keep `WEBHOOK__PORT` aligned with your reverse proxy.
- The webhook path used by the server is `TG__WEBHOOK_PATH`.

## Database Settings

```env
DB__HOST=db
DB__PORT=5432
DB__USER=botuser
DB__PASSWORD=strong_password
DB__NAME=telegram_bot
```

Use `settings.db.postgres_connection()` for SQLAlchemy async DSN.

## Redis Settings

```env
REDIS__HOST=redis
REDIS__PORT=6379
REDIS__USER=default
REDIS__PASSWORD=strong_password
REDIS__DB=0
```

Redis is used for FSM state and caching. The Redis connection is created via `settings.redis.redis_connection()`.

## API Settings

```env
API__HOST=0.0.0.0
API__PORT=8000
API__DEBUG=false
```

Notes:
- `API__DEBUG=true` enables `/api/docs` and `/api/redoc`.
- Rate limiting is enforced by `RateLimitMiddleware` (100 req/min per IP).

## WebApp Settings

```env
WEBAPP__URL=https://your-webapp.example
```

This URL is used to generate the WebApp button in `/profile`.
Use `http://localhost:3000` when running the Vite dev server.

## Example Configurations

### Local Development (Polling)

```env
ENVIRONMENT=development
TG__WEBHOOK_USE=False
WEBAPP__URL=http://localhost
API__DEBUG=true
```

### Production (Webhook)

```env
ENVIRONMENT=production
TG__WEBHOOK_USE=True
WEBHOOK__URL=https://bot.example.com
WEBHOOK__PORT=8000
WEBHOOK__SECRET=long_random_secret
WEBAPP__URL=https://bot.example.com
API__DEBUG=false
```

## Common Issues

### Invalid admin IDs
**Symptoms:** Startup fails with validation error.
**Cause:** Empty list, duplicates, or non-positive values.
**Solution:** Use a unique list of positive IDs.

### Webhook does not receive updates
**Symptoms:** Telegram updates are missing.
**Cause:** `WEBHOOK__URL` or `TG__WEBHOOK_PATH` mismatch.
**Solution:** Verify the final URL equals `WEBHOOK__URL + TG__WEBHOOK_PATH`.

### API docs not available
**Symptoms:** `/api/docs` returns 404.
**Cause:** `API__DEBUG` is false.
**Solution:** Set `API__DEBUG=true` and restart.

## Best Practices

1. DO store secrets in `.env` and never commit them.
2. DO use strong, unique passwords for DB and Redis.
3. DO keep `WEBHOOK__SECRET` long and random.
4. DO use `ENVIRONMENT=production` in production.
5. DO keep `API__DEBUG=false` outside development.

## Next Steps
- Configure [Deployment](deployment.md)
- Build handlers with [Handlers](handlers.md)
- Explore [Mini Apps](mini-apps/README.md)
