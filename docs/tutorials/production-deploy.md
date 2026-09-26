# Tutorial: Production Deploy

## Overview
This tutorial walks through a minimal production deployment using Docker and nginx. For full details, see [guides/deployment.md](../guides/deployment.md).

## Step 1: Prepare the Server

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y
```

## Step 2: Clone and Configure

```bash
cd /opt
sudo git clone https://github.com/MrConsoleka/aiogram-miniapp-template.git
cd aiogram-miniapp-template
sudo cp .env.example .env
sudo nano .env
```

Set:

```env
ENVIRONMENT=production
TG__WEBHOOK_USE=True
WEBHOOK__URL=https://your-domain.com
WEBHOOK__PORT=8000
WEBAPP__URL=https://your-domain.com
```

## Step 3: TLS Setup

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d your-domain.com
```

## Step 4: Run the Stack

```bash
docker compose up -d --build
```

## Step 5: Set Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/telegram" \
  -d "secret_token=YOUR_WEBHOOK_SECRET"
```

## Step 6: Verify

```bash
curl https://your-domain.com/api/health
```

Open your bot and run `/profile`.

## Common Issues

### HTTPS not working
**Symptoms:** Browser warns about insecure connection.
**Cause:** TLS certificate missing or expired.
**Solution:** Run `certbot renew` and reload nginx.

### Bot not receiving updates
**Symptoms:** `/start` does nothing.
**Cause:** Webhook not set or wrong URL.
**Solution:** Re-run `setWebhook` and check `getWebhookInfo`.

## Best Practices

1. DO use strong secrets in `.env`.
2. DO run migrations after updates.
3. DO back up Postgres regularly.

## Next Steps
- Full guide: [Deployment](../guides/deployment.md)
- Security: [Mini Apps Security](../guides/mini-apps/security.md)
