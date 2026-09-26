# Tutorial: Adding a Mini App

## Overview
This tutorial walks through adding a new Mini App page and wiring it to the backend.

## Quick Links
- [Mini Apps Overview](../guides/mini-apps/README.md)
- [Frontend Guide](../guides/mini-apps/frontend-guide.md)

## Step 1: Add an API Endpoint

Create a route file:

```python
# source/api/routes/status.py
from fastapi import APIRouter, Depends
from dishka.integrations.fastapi import FromDishka, inject

from source.api.middlewares import get_current_user
from source.schemas.responses import ApiResponse

router = APIRouter()

@router.get("/status")
@inject
async def status(user_data: dict = Depends(get_current_user)) -> ApiResponse[dict]:
    return ApiResponse(data={"telegram_id": user_data["id"]})
```

Register it in `source/api/app.py`.

## Step 2: Add an API Client Method

```ts
// webapp/src/api/endpoints.ts
export const statusApi = {
  get: () => api.get<ApiResponse<{ telegram_id: number }>>("/status")
};
```

## Step 3: Create a Page

```tsx
// webapp/src/pages/StatusPage.tsx
import { FC, useEffect, useState } from "react";
import { statusApi } from "../api/endpoints";

export const StatusPage: FC = () => {
  const [id, setId] = useState<number | null>(null);

  useEffect(() => {
    statusApi.get().then((res) => setId(res.data.telegram_id));
  }, []);

  return <div>Your Telegram ID: {id}</div>;
};
```

## Step 4: Render the Page

```tsx
// webapp/src/App.tsx
return (
  <div className={`app app--${colorScheme}`}>
    <StatusPage />
  </div>
);
```

## Step 5: Open from the Bot

```python
from source.telegram.keyboards import get_webapp_keyboard

@user_commands_router.message(Command("status"))
async def status_command(message: Message) -> None:
    await message.answer(
        "Open Status",
        reply_markup=get_webapp_keyboard("https://your-domain.com/status"),
    )
```

## Common Issues

### New endpoint returns 404
**Symptoms:** `GET /api/status` is missing.
**Cause:** Router not included in `setup_api()`.
**Solution:** Add `app.include_router(status.router, prefix=API_PREFIX)`.

### WebApp loads without data
**Symptoms:** `id` stays `null`.
**Cause:** API request failed.
**Solution:** Check network logs and ensure `Authorization` header is sent.

## Best Practices

1. DO use the shared API client.
2. DO keep endpoints authenticated.
3. DO update the bot domain in BotFather when changing WebApp URL.

## Next Steps
- Read [Mini Apps Deployment](../guides/mini-apps/deployment.md)
- Explore [Security](../guides/mini-apps/security.md)
