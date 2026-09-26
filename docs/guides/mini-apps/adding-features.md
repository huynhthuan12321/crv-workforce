# Adding Mini App Features

## Overview
This guide shows how to add a new page to the Mini App and a new backend API endpoint to support it.

## Quick Links
- [Frontend Guide](frontend-guide.md)
- [API Reference](api-reference.md)
- [Services](../services.md)

## 1. Add a New API Endpoint

Create a new route module:

```python
# source/api/routes/settings.py
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from source.api.middlewares import get_current_user
from source.schemas.responses import ApiResponse
from source.services.user_service import UserService

router = APIRouter()

@router.get("/settings")
@inject
async def get_settings(
    user_service: FromDishka[UserService],
    user_data: dict = Depends(get_current_user),
) -> ApiResponse[dict]:
    user = await user_service.get_by_telegram_id(user_data["id"])
    return ApiResponse(data={"language_code": user.language_code})
```

Register the router:

```python
# source/api/app.py
from source.api.routes import settings

app.include_router(settings.router, prefix=f"{API_PREFIX}", tags=["Settings"])
```

## 2. Add Frontend API Client

```ts
// webapp/src/api/endpoints.ts
export const settingsApi = {
  get: () => api.get<ApiResponse<{ language_code: string }>>("/settings")
};
```

## 3. Create a New Page

```tsx
// webapp/src/pages/SettingsPage.tsx
import { FC, useEffect, useState } from "react";
import { settingsApi } from "../api/endpoints";

export const SettingsPage: FC = () => {
  const [lang, setLang] = useState("en");

  useEffect(() => {
    settingsApi.get().then((res) => setLang(res.data.language_code));
  }, []);

  return <div>Language: {lang}</div>;
};
```

## 4. Render the Page

Replace the `ProfilePage` in `App.tsx`, or introduce routing:

```tsx
// webapp/src/App.tsx
return (
  <div className={`app app--${colorScheme}`}>
    <SettingsPage />
  </div>
);
```

## 5. Add a Bot Command (Optional)

If this page should open from the bot, add a command:

```python
# source/telegram/handlers/user/commands.py
from source.telegram.keyboards import get_webapp_keyboard

@user_commands_router.message(Command("settings"))
async def settings_command(message: Message) -> None:
    await message.answer(
        "Open settings",
        reply_markup=get_webapp_keyboard("https://your-domain.com/settings"),
    )
```

## Common Issues

### 404 on new API endpoint
**Symptoms:** `GET /api/settings` returns 404.
**Cause:** Router not included in `setup_api()`.
**Solution:** Import and include the router in `source/api/app.py`.

### Frontend cannot access new endpoint
**Symptoms:** API calls fail from the browser.
**Cause:** Missing `Authorization` header or wrong base URL.
**Solution:** Use the shared API client (`api`) and check `VITE_API_URL`.

## Best Practices

1. DO keep endpoints small and focused.
2. DO reuse services for business logic.
3. DO add Pydantic schemas for request/response validation.
4. DO update translations when new UI strings are added.

## Next Steps
- Review [Authentication](authentication.md)
- See [Frontend Guide](frontend-guide.md)
- Read [REST API Reference](../../reference/rest-api.md)
