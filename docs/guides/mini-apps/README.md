# Telegram Mini Apps Guide

## Overview
Telegram Mini Apps are web applications that open inside the Telegram client. This template includes a React frontend and a FastAPI backend that validates Telegram `initData` and returns user data.

## Quick Links
- [Quick Start](quickstart.md)
- [Authentication](authentication.md)
- [API Reference](api-reference.md)
- [Frontend Guide](frontend-guide.md)
- [Adding Features](adding-features.md)
- [Theming](theming.md)
- [Security](security.md)
- [Deployment](deployment.md)
- [Troubleshooting](troubleshooting.md)
- [Examples](examples.md)

## What Are Telegram Mini Apps?
Mini Apps are web apps launched from a bot via a WebApp button. Telegram passes signed `initData` to the frontend so the backend can verify the user without passwords.

## What's Included in This Template
- React 18 + TypeScript frontend (`webapp/`)
- FastAPI backend with REST API (`/api/...`)
- HMAC-SHA256 authentication (Telegram `initData` validation)
- Replay protection via `auth_date` checks
- Theme integration with Telegram WebApp SDK
- i18next localization
- Example Profile page and user API

## Architecture Overview

```mermaid
flowchart LR
    U[User in Telegram] --> T[Telegram Client]
    T --> W[React WebApp]
    W --> A[FastAPI API]
    A --> D[(PostgreSQL)]
    A --> R[(Redis)]
    W -->|initData| A
    B[Bot (aiogram)] -->|/profile command| T
```

## How It Works

### 1. User Opens the Mini App
The bot sends a WebApp button (see `/profile` handler). When clicked, Telegram opens the WebApp URL and attaches `initData`.

### 2. Authentication
The frontend sends `initData` to `POST /api/auth/validate`. The backend validates the signature using your bot token.

### 3. Data Flow
Once authenticated, the frontend calls API endpoints (for example, `/api/users/me`) to load and update user data.

## Directory Structure

```
webapp/
├── src/
│   ├── api/          # API client and endpoints
│   ├── components/   # Reusable UI components
│   ├── hooks/        # useTelegram, useAuth
│   ├── pages/        # Profile page and routes
│   ├── store/        # Zustand state
│   ├── styles/       # CSS
│   ├── types/        # TypeScript types
│   └── utils/        # helpers
└── public/locales/   # i18n translations
```

## Common Issues

### WebApp loads but API calls fail
**Symptoms:** Profile page shows authorization error.
**Cause:** Invalid `initData` or bot token mismatch.
**Solution:** Verify `TG__BOT_TOKEN` matches the bot that launches the WebApp.

### CORS errors in the browser
**Symptoms:** Browser blocks API requests.
**Cause:** API allows only Telegram WebApp domains by default.
**Solution:** Use the Vite proxy or add `http://localhost:3000` to `cors_settings()` for development.

## Best Practices

1. DO validate `initData` on the backend.
2. DO keep `WEBAPP__URL` correct for your environment.
3. DO avoid putting secrets in the frontend.
4. DO handle API errors gracefully.
5. DO use i18n from the start if you target multiple locales.

## Next Steps
- Start with [Quick Start](quickstart.md)
- Learn [Authentication](authentication.md)
- Browse [API Reference](api-reference.md)
