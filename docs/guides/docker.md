# Docker Guide

## Overview
Docker Compose is the recommended way to run the full stack (bot, API, DB, Redis, WebApp, nginx). A separate development compose file provides DB and Redis only.

## Quick Links
- [Deployment](deployment.md)
- [Configuration](configuration.md)
- [Mini Apps Deployment](mini-apps/deployment.md)

## Development Stack (DB + Redis)

Use `docker-compose.dev.yml` when running the bot locally:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Stop services:

```bash
docker compose -f docker-compose.dev.yml down
```

## Full Stack (Bot + API + WebApp + nginx)

```bash
docker compose up -d --build
```

Services:
- `bot`: aiogram + FastAPI API
- `db`: PostgreSQL 15
- `redis`: Redis 7
- `webapp`: React Mini App
- `nginx`: Reverse proxy and static server

Port mapping note: `WEBHOOK__PORT` controls the bot port (defaults to `8080` if not set).

## Logs

```bash
docker compose logs -f
```

Or a single service:

```bash
docker compose logs -f bot
```

## Useful Commands

```bash
docker compose ps

docker compose exec db psql -U $DB__USER -d $DB__NAME

docker compose exec redis redis-cli -a $REDIS__PASSWORD ping
```

## Environment Variables in Containers
The bot container loads `.env` directly. Keep it up to date with `.env.example`. The WebApp build reads `webapp/.env` (for `VITE_API_URL`) at build time.

## Common Issues

### WebApp does not load
**Symptoms:** `http://localhost` returns 502 or blank page.
**Cause:** `webapp` container not built or nginx not running.
**Solution:** Run `docker compose up -d --build` and check logs.

### API unreachable
**Symptoms:** `http://localhost/api/health` fails.
**Cause:** `bot` container not healthy or nginx not proxying.
**Solution:** Check `docker compose logs -f bot` and nginx logs.

### Database connection errors
**Symptoms:** Bot exits on startup.
**Cause:** DB not ready or wrong credentials.
**Solution:** Verify `DB__*` variables and DB health status.

## Best Practices

1. DO keep `.env` updated for compose.
2. DO rebuild after dependency changes.
3. DO use `docker compose logs -f` to diagnose startup issues.
4. DO run migrations after deploying new versions.

## Next Steps
- Follow [Deployment](deployment.md) for production
- Read [Mini Apps Deployment](mini-apps/deployment.md)
