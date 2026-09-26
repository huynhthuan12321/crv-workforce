# REST API Reference

## Overview
This reference documents the Mini App REST API served by FastAPI. All endpoints return a consistent JSON envelope and use Telegram `initData` for authentication.

If `API__DEBUG=true`, interactive API docs are available at `/api/docs` and `/api/redoc`.

## Base URLs
- Local (polling): `http://localhost:8000/api`
- Docker + nginx: `http://localhost/api`
- Production: `https://your-domain.com/api`

## Authentication
All endpoints except `/health` require `initData`:

```http
Authorization: Bearer <initData>
```

The backend validates `initData` using your bot token and rejects expired `auth_date` values.

## Response Envelope

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

## Rate Limiting
The API applies an in-memory rate limit of 100 requests per minute per IP.

Error response:

```json
{
  "error": "Too many requests",
  "retry_after": 60
}
```

Response header:

```http
Retry-After: 60
```

## Headers
- `X-Process-Time`: request duration in seconds

## Endpoints

### GET /api/health
Health check endpoint.

**Auth:** Not required

**curl**

```bash
curl http://localhost:8000/api/health
```

**Response**

```json
{
  "status": "ok"
}
```

---

### POST /api/auth/validate
Validate `initData` and return user data.

**Auth:** Required

**curl**

```bash
curl -X POST http://localhost:8000/api/auth/validate \
  -H "Authorization: Bearer <initData>"
```

**Python**

```python
import requests

resp = requests.post(
    "http://localhost:8000/api/auth/validate",
    headers={"Authorization": f"Bearer {init_data}"},
)
print(resp.json())
```

**JavaScript**

```js
const res = await fetch("/api/auth/validate", {
  method: "POST",
  headers: { Authorization: `Bearer ${initData}` }
});
const data = await res.json();
```

**TypeScript**

```ts
const res = await fetch("/api/auth/validate", {
  method: "POST",
  headers: { Authorization: `Bearer ${initData}` }
});
const data = await res.json();
```

**Response 200**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "language_code": "en",
    "bio": null,
    "created_at": "2025-01-10T12:00:00Z",
    "updated_at": "2025-01-10T12:00:00Z"
  }
}
```

**Response 401**

```json
{
  "success": false,
  "error": "Invalid authorization data"
}
```

---

### GET /api/users/me
Return the current user profile.

**Auth:** Required

**curl**

```bash
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <initData>"
```

**Response 200**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "language_code": "en",
    "bio": "Hello",
    "created_at": "2025-01-10T12:00:00Z",
    "updated_at": "2025-01-10T12:00:00Z"
  }
}
```

**Response 404**

```json
{
  "success": false,
  "error": "User not found"
}
```

---

### PATCH /api/users/me
Update the current user profile.

**Auth:** Required

**Request Body**

```json
{
  "bio": "string (max 500)",
  "language_code": "string (max 10)"
}
```

**curl**

```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <initData>" \
  -H "Content-Type: application/json" \
  -d '{"bio":"New bio","language_code":"ru"}'
```

**Response 200**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "telegram_id": 123456789,
    "language_code": "ru",
    "bio": "New bio",
    "created_at": "2025-01-10T12:00:00Z",
    "updated_at": "2025-01-10T12:05:00Z"
  }
}
```

---

### GET /api/users/{telegram_id}
Get a user profile by Telegram ID.

**Auth:** Required

**curl**

```bash
curl http://localhost:8000/api/users/123456789 \
  -H "Authorization: Bearer <initData>"
```

**Response 200**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "telegram_id": 123456789,
    "language_code": "en",
    "bio": "Hello",
    "created_at": "2025-01-10T12:00:00Z",
    "updated_at": "2025-01-10T12:05:00Z"
  }
}
```

---

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 401 | Unauthorized | Missing or invalid initData |
| 404 | Not Found | User not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unhandled error or validation failure |

## Data Models

### ApiResponse

```ts
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}
```

### UserRead

```ts
interface UserRead {
  id: number;
  telegram_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code: string;
  bio?: string | null;
  created_at: string;
  updated_at?: string | null;
}
```

### UserUpdate

```ts
interface UserUpdate {
  bio?: string | null; // max 500
  language_code?: string | null; // max 10
}
```

## Using the API from React

```ts
import { api } from "../api/client";

const me = await api.get<ApiResponse<UserRead>>("/users/me");
```

## Common Issues

### Missing Authorization header
**Symptoms:** `Authorization required` error.
**Cause:** API client not injecting `initData`.
**Solution:** Use the shared API client or add `Authorization: Bearer <initData>`.

### Rate limit errors
**Symptoms:** `Too many requests`.
**Cause:** Rapid polling or frequent calls.
**Solution:** Batch requests or add client-side throttling.

## Best Practices

1. DO handle `success=false` in the UI.
2. DO reuse `initData` within the session.
3. DO keep API calls minimal on page load.
4. DO validate user input before PATCH requests.

## Next Steps
- See [Mini Apps API Guide](../guides/mini-apps/api-reference.md)
- Review [Authentication](../guides/mini-apps/authentication.md)
