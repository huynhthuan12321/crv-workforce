# Getting Started

## Overview
This guide helps you run the bot and the Mini App locally in minutes. It covers setup with Docker and local tooling, plus a quick verification checklist.

## Quick Links
- [Configuration Guide](guides/configuration.md)
- [Mini Apps Overview](guides/mini-apps/README.md)
- [Deployment Guide](guides/deployment.md)

## Requirements
- Python 3.11+ (Docker uses Python 3.12)
- Node.js 18+ (Node 20 is used in the webapp Dockerfile)
- Docker + Docker Compose (optional but recommended)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## 1. Clone the Repository

```bash
git clone https://github.com/MrConsoleka/aiogram-miniapp-template.git
cd aiogram-miniapp-template
cp .env.example .env
cp webapp/.env.example webapp/.env
```

## 2. Configure Environment

Edit `.env` and set the mandatory values:

```env
TG__BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TG__ADMIN_IDS=[YOUR_TELEGRAM_ID]
TG__WEBHOOK_USE=False
WEBAPP__URL=http://localhost:3000
```

Notes:
- `TG__WEBHOOK_USE=False` enables polling for local development.
- `WEBAPP__URL` is used to build the WebApp button in `/profile`.
- Use `http://localhost` if you run the full Docker stack with nginx.
- `webapp/.env` controls frontend API base URL (`VITE_API_URL`).

For full configuration details, see [guides/configuration.md](guides/configuration.md).

## 3. Start with Docker (Recommended)

```bash
docker compose up -d --build
```

Verify:
- Bot responds to `/start`
- Mini App loads at `http://localhost`
- API responds at `http://localhost/api/health`

## 4. Run Locally (Without Docker)

### Backend + Bot

```bash
make venv
make install
make run
```

This starts:
- Bot polling loop
- FastAPI Mini App backend on `API__PORT` (default `8000`)

### WebApp

```bash
cd webapp
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:3000` and proxies `/api` to `http://localhost:8000`.

## 5. Test the Mini App

1. Open your bot in Telegram.
2. Run `/profile` to open the Mini App.
3. Check the Profile page loads and your data is displayed.

## 6. Optional: Enable API Docs

In `.env`, set:

```env
API__DEBUG=true
```

FastAPI Swagger UI becomes available at:
- `http://localhost:8000/api/docs`

## Common Issues

### Bot does not respond
**Symptoms:** No reply to `/start`.
**Cause:** Missing or invalid bot token.
**Solution:** Check `TG__BOT_TOKEN` and restart the bot.

### WebApp button opens a blank page
**Symptoms:** `/profile` opens but shows a blank screen.
**Cause:** `WEBAPP__URL` is wrong or webapp is not running.
**Solution:** Set `WEBAPP__URL` to your webapp domain or `http://localhost` for Docker.

### API requests fail with 401
**Symptoms:** Profile page shows authorization error.
**Cause:** Invalid `initData` or wrong bot token.
**Solution:** Confirm bot token matches the bot opening the Mini App.

### CORS error in the browser
**Symptoms:** Browser blocks requests to `/api`.
**Cause:** API only allows Telegram WebApp domains by default.
**Solution:** Use the Vite proxy (`/api`) or add `http://localhost:3000` to `cors_settings()` for development.

## Best Practices

1. DO keep `.env` out of version control.
2. DO use Docker for production-like testing.
3. DO run `make migration` and `alembic upgrade head` after schema changes.
4. DO use `WEBAPP__URL` to match your deployment domain.
5. DO keep `API__DEBUG=false` in production.

## Next Steps
- Explore [Handlers](guides/handlers.md) for bot logic
- Learn the [Mini Apps Overview](guides/mini-apps/README.md)
- Read [Deployment](guides/deployment.md) for production setup
