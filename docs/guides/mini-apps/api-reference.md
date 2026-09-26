# Mini Apps API Reference (Guide)

## Overview
This is the guide-level API reference for the Mini App endpoints. For full schemas and multi-language examples, see [docs/reference/rest-api.md](../../reference/rest-api.md).

## Base URL
- Local (polling): `http://localhost:8000/api`
- Docker + nginx: `http://localhost/api`
- Production: `https://your-domain.com/api`

## Authentication
All endpoints (except health) require Telegram `initData` in the `Authorization` header:

```http
Authorization: Bearer <initData>
```

## Response Format

Success:

```json
{
  "success": true,
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "error": "Error message"
}
```

## Endpoints

### GET /api/health
Health check.

```bash
curl http://localhost:8000/api/health
```

### POST /api/auth/validate
Validate `initData` and return user data.

```bash
curl -X POST http://localhost:8000/api/auth/validate \
  -H "Authorization: Bearer <initData>"
```

### GET /api/users/me
Get the current user profile.

```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <initData>"
```

### PATCH /api/users/me
Update the current user profile.

```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <initData>" \
  -H "Content-Type: application/json" \
  -d '{"bio": "New bio", "language_code": "ru"}'
```

### GET /api/users/{telegram_id}
Get another user profile by Telegram ID.

```bash
curl http://localhost:8000/api/users/123456789 \
  -H "Authorization: Bearer <initData>"
```

## Rate Limiting
The API uses in-memory rate limiting with a default of 100 requests per minute per IP. The response is:

```json
{
  "error": "Too many requests",
  "retry_after": 60
}
```

## Common Issues

### 401 Unauthorized
**Symptoms:** `Invalid authorization data`.
**Cause:** Invalid or missing `initData`.
**Solution:** Open the WebApp inside Telegram and confirm the bot token.

### 429 Too Many Requests
**Symptoms:** API responds with rate limit error.
**Cause:** High request volume per IP.
**Solution:** Reduce request frequency or batch requests.

## Best Practices

1. DO reuse the same `initData` for a short session.
2. DO handle `success=false` responses in the UI.
3. DO avoid calling `/auth/validate` on every render.

## Next Steps
- Full reference in [docs/reference/rest-api.md](../../reference/rest-api.md)
- Learn [Frontend Guide](frontend-guide.md)
