# Architecture Reference

## Overview
This document describes the logical architecture, data flow, and key components of the template.

## High-Level Diagram

```mermaid
flowchart LR
    U[Telegram User] --> T[Telegram Client];
    T --> B[Bot: aiogram];
    B --> D[(PostgreSQL)];
    B --> R[(Redis)];
    T --> W[Mini App: React];
    W --> A[FastAPI API];
    A --> D;
    A --> R;
    W --> N[nginx];
    N --> A;
```

## Bot Update Flow

```mermaid
sequenceDiagram
    participant Tg as Telegram
    participant Bot as aiogram
    participant MW as Middlewares
    participant H as Handlers
    participant S as Services
    participant U as UnitOfWork
    participant DB as Database

    Tg->>Bot: Update
    Bot->>MW: Middleware pipeline
    MW->>H: Routed handler
    H->>S: Business logic
    S->>U: Transaction
    U->>DB: Query/Write
    DB-->>U: Result
    U-->>S: Entity
    S-->>H: Data
    H-->>Bot: Response
```

## Mini App Flow

```mermaid
sequenceDiagram
    participant User
    participant TG as Telegram Client
    participant UI as WebApp (React)
    participant API as FastAPI
    participant DB as PostgreSQL

    User->>TG: Tap WebApp button
    TG->>UI: Load WebApp + initData
    UI->>API: POST /api/auth/validate
    API->>API: Validate HMAC
    API->>DB: get_or_create_user
    DB-->>API: user
    API-->>UI: ApiResponse(User)
```

## Component Responsibilities

- **Bot (aiogram)**: Processes updates, commands, callbacks, FSM, dialogs.
- **FastAPI API**: Validates `initData`, exposes Mini App REST endpoints.
- **WebApp (React)**: UI, theme integration, API calls.
- **PostgreSQL**: Persistent user data.
- **Redis**: FSM state and caching.
- **nginx**: Reverse proxy and static file server.

## Common Issues

### Updates not reaching handlers
**Symptoms:** No responses to commands.
**Cause:** Router not included or webhook misconfigured.
**Solution:** Check router registration and webhook settings.

### Mini App cannot access API
**Symptoms:** Authorization error or 401.
**Cause:** API not reachable or invalid `initData`.
**Solution:** Verify proxy routes and bot token.

## Best Practices

1. DO keep handlers thin and delegate to services.
2. DO use the Unit of Work for DB writes.
3. DO validate `initData` for every API request.

## Next Steps
- See [Project Structure](project-structure.md)
- Explore [REST API Reference](rest-api.md)
