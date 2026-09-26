# Mini Apps Examples

## Overview
This guide provides practical examples for common Mini App features.

## Quick Links
- [Frontend Guide](frontend-guide.md)
- [API Reference](api-reference.md)
- [Authentication](authentication.md)

## Example 1: Update Profile Bio

### Frontend

```tsx
import { usersApi } from "../api/endpoints";
import { useUserStore } from "../store/useUserStore";

const { updateBio } = useUserStore.getState();

const saveBio = async (bio: string) => {
  const response = await usersApi.updateMe({ bio });
  if (response.data) {
    updateBio(response.data.bio || "");
  }
};
```

### Backend
`PATCH /api/users/me` already supports `bio` updates.

## Example 2: Change Language

```tsx
const updateLanguage = async (language_code: "en" | "ru") => {
  await usersApi.updateMe({ language_code });
};
```

## Example 3: Send Data to Bot

```ts
import { useTelegram } from "../hooks/useTelegram";

const { sendData } = useTelegram();

sendData({ action: "purchase", sku: "premium" });
```

On the bot side:

```python
@webapp_callbacks_router.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    await message.answer(f"Received: {message.web_app_data.data}")
```

## Example 4: Haptic Feedback

```ts
const { hapticFeedback } = useTelegram();

hapticFeedback("success");
```

## Example 5: Theme-aware Styling

```css
.card {
  background: var(--tg-theme-secondary-bg-color);
  color: var(--tg-theme-text-color);
}
```

## Common Issues

### sendData does not work
**Symptoms:** Bot does not receive data.
**Cause:** Handler missing for `web_app_data`.
**Solution:** Add `F.web_app_data` handler in `source/telegram/handlers/webapp/`.

### Haptics not firing
**Symptoms:** No vibration on mobile.
**Cause:** Haptic API unsupported in some clients.
**Solution:** Test on a Telegram mobile app.

## Best Practices

1. DO keep API responses in sync with Zustand store.
2. DO debounce frequent updates (e.g., typing).
3. DO handle API errors in the UI.

## Next Steps
- Add new pages with [Adding Features](adding-features.md)
- Review [Security](security.md)
