# Mini Apps Troubleshooting

## Overview
This guide lists common issues when running the Mini App and how to resolve them.

## Quick Links
- [Authentication](authentication.md)
- [API Reference](api-reference.md)
- [Deployment](deployment.md)

## Common Issues

### WebApp opens to a blank screen
**Symptoms:** White screen or no UI.
**Cause:** JavaScript error, missing assets, or incorrect build.
**Solution:** Check browser console, rebuild the WebApp, and verify nginx/static serving.

### Authorization failed
**Symptoms:** UI shows authorization error.
**Cause:** Invalid or missing `initData`.
**Solution:** Ensure the app is opened via Telegram and `TG__BOT_TOKEN` is correct.

### API returns 401
**Symptoms:** `Invalid authorization data`.
**Cause:** Missing `Authorization` header.
**Solution:** Use the built-in API client which injects `initData`.

### CORS error in browser
**Symptoms:** CORS blocked requests.
**Cause:** API allows only Telegram domains.
**Solution:** Use Vite proxy or add `http://localhost:3000` in `cors_settings()` for development.

### 429 Too Many Requests
**Symptoms:** `Too many requests` from API.
**Cause:** Rate limit exceeded.
**Solution:** Debounce API calls and avoid revalidating on every render.

### WebApp does not open from bot
**Symptoms:** Button does nothing or shows an error.
**Cause:** `WEBAPP__URL` incorrect or domain not set in BotFather.
**Solution:** Update `WEBAPP__URL` and set the domain in BotFather.

### Profile shows outdated data
**Symptoms:** UI does not reflect updates.
**Cause:** Missing store update or API error.
**Solution:** Ensure `useUserStore.updateBio` runs after successful PATCH.

## Best Practices

1. DO test in Telegram, not in a standalone browser tab.
2. DO log API errors in the frontend for quick diagnosis.
3. DO keep translations in sync across locales.
4. DO verify your reverse proxy routes `/api` correctly.

## Next Steps
- Review [Authentication](authentication.md)
- See [Frontend Guide](frontend-guide.md)
- Read [Security](security.md)
