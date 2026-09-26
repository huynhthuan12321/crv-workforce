# Mini Apps Frontend Guide

## Overview
The Mini App frontend lives in `webapp/` and is built with React 18, TypeScript, Vite, i18next, and Zustand. The current app renders a single `ProfilePage` and uses the Telegram WebApp SDK to read theme and `initData`.

## Quick Links
- [Mini Apps Overview](README.md)
- [Authentication](authentication.md)
- [Adding Features](adding-features.md)

## Entry Points

- `webapp/src/main.tsx` boots React and loads i18n.
- `webapp/src/App.tsx` renders the root layout and `ProfilePage`.

```tsx
// webapp/src/App.tsx
const App: FC = () => {
  const { colorScheme } = useTelegram();
  return (
    <div className={`app app--${colorScheme}`}>
      <ProfilePage />
    </div>
  );
};
```

## Telegram WebApp SDK Hook

`useTelegram` wraps the SDK and exposes helpers:

```ts
const { isReady, themeParams, hapticFeedback, sendData } = useTelegram();
```

It also applies Telegram theme variables to CSS custom properties.

## State Management (Zustand)

User data is stored in `useUserStore`:

```ts
const { user, isLoading, error, setUser } = useUserStore();
```

## API Client

The API client automatically injects `initData`:

```ts
const response = await authApi.validate();
```

The base URL comes from `VITE_API_URL` or falls back to `/api`.

## i18n
Translations live in `webapp/public/locales/` and are loaded with i18next:

```ts
import { useTranslation } from "react-i18next";

const { t } = useTranslation();
```

Supported languages are configured in `webapp/src/i18n.ts`.

## Styling
CSS lives in `webapp/src/styles/` and uses Telegram theme variables:

```css
:root {
  --tg-theme-bg-color: #ffffff;
  --tg-theme-text-color: #111827;
}
```

## Adding a New Page

Create a new page component:

```tsx
// webapp/src/pages/SettingsPage.tsx
export const SettingsPage: FC = () => {
  return <div>Settings</div>;
};
```

Render it from `App.tsx` or add a router (not included by default).

## Common Issues

### App renders blank
**Symptoms:** White screen in Telegram.
**Cause:** JS error or missing `initData`.
**Solution:** Check console logs and open the app inside Telegram.

### Theme colors do not update
**Symptoms:** App uses default colors only.
**Cause:** Telegram WebApp SDK not ready.
**Solution:** Ensure `useTelegram()` is called in `App.tsx`.

## Best Practices

1. DO call `tg.ready()` before accessing SDK features.
2. DO keep API calls in hooks or services, not inside components directly.
3. DO handle `isLoading` and `error` states.
4. DO keep translations up to date for all languages.

## Next Steps
- Add pages in [Adding Features](adding-features.md)
- Learn about [Theming](theming.md)
- Review [API Reference](api-reference.md)
