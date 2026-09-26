# Mini Apps Quick Start

## Overview
This guide focuses on running the Mini App in development and verifying the profile page and API.

## Quick Links
- [Mini Apps Overview](README.md)
- [Authentication](authentication.md)
- [Frontend Guide](frontend-guide.md)

## Step 1: Configure `.env`

```env
TG__BOT_TOKEN=YOUR_BOT_TOKEN
TG__ADMIN_IDS=[YOUR_TELEGRAM_ID]
TG__WEBHOOK_USE=False
WEBAPP__URL=http://localhost:3000
```

Use `http://localhost` when running the full Docker stack with nginx.

Also copy the frontend env file (optional):

```bash
cp webapp/.env.example webapp/.env
```

## Step 2: Start the Backend

```bash
make venv
make install
make run
```

The API runs on `http://localhost:8000/api`.

## Step 3: Start the WebApp

```bash
cd webapp
npm install
npm run dev
```

The WebApp runs at `http://localhost:3000` and proxies `/api` to the backend.

## Step 4: Open the Mini App

1. Open Telegram and talk to your bot.
2. Run `/profile`.
3. Telegram opens the WebApp with signed `initData`.

## Verify API

From the browser console in the WebApp:

```js
window.Telegram?.WebApp?.initData
```

To validate directly via curl:

```bash
curl -X POST http://localhost:8000/api/auth/validate \
  -H "Authorization: Bearer <initData>"
```

## Common Issues

### Profile page shows authorization error
**Symptoms:** Red error message on the page.
**Cause:** `initData` is invalid or missing.
**Solution:** Open the WebApp inside Telegram, not directly in a browser tab.

### API returns 401
**Symptoms:** API responds with `Invalid authorization data`.
**Cause:** Wrong bot token in `.env`.
**Solution:** Verify `TG__BOT_TOKEN` is correct and restart the backend.

## Best Practices

1. DO use the Vite proxy for local requests (`/api`).
2. DO test inside Telegram to get real `initData`.
3. DO keep `API__DEBUG=true` only for development.

## Next Steps
- Deep dive into [Authentication](authentication.md)
- Extend the frontend in [Adding Features](adding-features.md)
- See the full [API Reference](api-reference.md)
