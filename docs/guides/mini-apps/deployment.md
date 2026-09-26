# Mini Apps Deployment

## Overview
This guide focuses on deploying the Mini App frontend and its API endpoints. It complements the full production guide in [docs/guides/deployment.md](../deployment.md).

## Quick Links
- [Production Deployment](../deployment.md)
- [Security](security.md)
- [REST API Reference](../../reference/rest-api.md)

## 1. Build the WebApp

```bash
cd webapp
npm install
npm run build
```

The build output is in `webapp/dist` (used by `webapp.Dockerfile`).

## 2. Set the WebApp URL

In `.env`:

```env
WEBAPP__URL=https://your-domain.com
```

This value is used to generate the WebApp button in `/profile`.

## 3. Configure BotFather Domain
Telegram requires a valid domain for Mini Apps. Use BotFather to set the domain for your bot.

## 4. Reverse Proxy
For production, serve the WebApp and API under the same domain:

- `https://your-domain.com/` -> WebApp
- `https://your-domain.com/api` -> API

This avoids CORS issues and keeps authentication simple.

## 5. Set VITE_API_URL (Optional)
The frontend reads `VITE_API_URL` from `webapp/.env`:

```env
VITE_API_URL=/api
```

## 6. Verify Deployment

```bash
curl https://your-domain.com/api/health
```

Open your bot and run `/profile` to load the Mini App.

## Common Issues

### WebApp opens but API fails
**Symptoms:** Authorization error on profile page.
**Cause:** API not reachable or incorrect `VITE_API_URL`.
**Solution:** Ensure `/api` is proxied and `VITE_API_URL=/api`.

### Telegram refuses to open the Mini App
**Symptoms:** Telegram blocks the link.
**Cause:** Domain not set in BotFather or missing HTTPS.
**Solution:** Set the WebApp domain and use HTTPS.

## Best Practices

1. DO serve WebApp and API from the same domain.
2. DO enable HTTPS before setting webhook.
3. DO cache static assets via nginx.
4. DO keep `API__DEBUG=false` in production.

## Next Steps
- Follow [Production Deployment](../deployment.md)
- Review [Security](security.md)
- Explore [Troubleshooting](troubleshooting.md)
