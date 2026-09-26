# Project Structure

## Overview
This reference explains the major directories and files in the repository.

## Tree (Condensed)

```text
aiogram-miniapp-template/
├── docs/
│   ├── guides/
│   ├── reference/
│   └── tutorials/
├── migrations/
├── nginx/
├── scripts/
├── source/
│   ├── api/
│   ├── config/
│   ├── constants/
│   ├── database/
│   ├── factory/
│   ├── infrastructure/
│   ├── locales/
│   ├── schemas/
│   ├── services/
│   ├── telegram/
│   └── utils/
├── tests/
├── webapp/
│   ├── public/
│   └── src/
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile
├── webapp.Dockerfile
├── pyproject.toml
└── source/__main__.py
```

## Key Directories

- `docs/`: user and developer documentation.
- `source/api/`: FastAPI Mini App backend.
- `source/telegram/`: aiogram handlers, routers, filters, FSM.
- `source/services/`: business logic layer.
- `source/database/`: models, repositories, Unit of Work.
- `source/factory/`: bot, dispatcher, container, API setup.
- `source/utils/`: helpers (logging, i18n, validators).
- `webapp/`: React Mini App frontend.
- `nginx/`: reverse proxy configs.
- `migrations/`: Alembic migration files.

## Key Files

- `.env.example`: example environment variables.
- `docker-compose.yml`: full stack (bot, API, webapp, nginx, db, redis).
- `docker-compose.dev.yml`: db and redis for local dev.
- `Dockerfile`: backend container (non-root, Python 3.12).
- `webapp.Dockerfile`: frontend build container.

## Common Issues

### Unsure where to add code
**Symptoms:** New files placed in the wrong layer.
**Cause:** Unclear structure boundaries.
**Solution:** Add business logic in `services/`, DB queries in `repositories/`, handlers in `telegram/`.

## Best Practices

1. DO keep layers separated (handlers -> services -> repositories).
2. DO update docs when adding new top-level components.

## Next Steps
- See [Architecture](architecture.md)
- Read [Handlers](../guides/handlers.md)
