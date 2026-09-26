# Mini Apps Security

## Overview
Mini Apps rely on Telegram `initData` for authentication. This guide covers the built-in protections and recommended hardening steps.

## Quick Links
- [Authentication](authentication.md)
- [Deployment](deployment.md)
- [REST API Reference](../../reference/rest-api.md)

## Built-In Protections
- HMAC-SHA256 validation of `initData`
- Replay protection via `auth_date` TTL (default 3600 seconds)
- Timing-safe signature comparison with `hmac.compare_digest`
- CORS restricted to Telegram WebApp domains
- API rate limiting (100 requests/min per IP)
- Security headers via nginx

## Recommended Hardening

### 1. Keep Secrets Private
- Store `TG__BOT_TOKEN` only on the backend.
- Do not leak tokens or secrets into frontend builds.

### 2. Enforce HTTPS
Telegram requires HTTPS for production WebApps. Use Lets Encrypt or a managed certificate.

### 3. Use Strong Credentials
- Use strong DB/Redis passwords.
- Rotate credentials regularly.

### 4. Limit Origins
`cors_settings()` allows only Telegram WebApp domains by default. If you need local development, add `http://localhost:3000` explicitly.

### 5. Observe Rate Limits
The API rate limiter is in-memory and per instance. For multi-instance setups, consider a shared limiter in Redis.

## Common Issues

### Invalid authorization data
**Symptoms:** API returns `Invalid authorization data`.
**Cause:** `initData` signature mismatch.
**Solution:** Confirm bot token, ensure the request comes from Telegram.

### Too many requests
**Symptoms:** API returns 429.
**Cause:** Rate limit exceeded.
**Solution:** Reduce request frequency or implement client-side debouncing.

### Mixed content errors
**Symptoms:** Browser blocks requests.
**Cause:** WebApp loaded over HTTPS but API uses HTTP.
**Solution:** Serve API over HTTPS and proxy under the same domain.

## Best Practices

1. DO validate `initData` for every request.
2. DO reject expired `auth_date` values.
3. DO log failed auth attempts with context.
4. DO keep `API__DEBUG=false` in production.
5. DO use HTTPS everywhere.

## Next Steps
- See [Authentication](authentication.md)
- Review [Deployment](deployment.md)
- Check [Troubleshooting](troubleshooting.md)
