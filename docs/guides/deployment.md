# Production Deployment Guide

## Overview
This guide covers deploying the Telegram bot and Mini App to production with Docker, nginx, and HTTPS. It assumes a Linux VPS and a public domain.

## Prerequisites
- Linux VPS (Ubuntu 20.04+/Debian 11+)
- Domain name with DNS pointing to your server
- Docker and Docker Compose installed
- Basic knowledge of nginx and SSL

## Quick Deploy Checklist
- [ ] Bot token from @BotFather
- [ ] Domain points to server IP
- [ ] Firewall allows ports 80 and 443
- [ ] TLS certificate available
- [ ] Strong DB and Redis passwords
- [ ] Webhook URL configured
- [ ] Migrations applied
- [ ] Health checks passing

## 1. Server Setup

### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y
sudo usermod -aG docker $USER
```

### 1.3 Configure Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 2. Clone and Configure

```bash
cd /opt
sudo git clone https://github.com/MrConsoleka/aiogram-miniapp-template.git
cd aiogram-miniapp-template
sudo cp .env.example .env
sudo nano .env
```

Recommended production values:

```env
ENVIRONMENT=production

TG__WEBHOOK_USE=True
TG__WEBHOOK_PATH=/telegram
TG__BOT_TOKEN=YOUR_BOT_TOKEN
TG__ADMIN_IDS=[YOUR_TELEGRAM_ID]

WEBHOOK__URL=https://your-domain.com
WEBHOOK__HOST=0.0.0.0
WEBHOOK__PORT=8000
WEBHOOK__SECRET=GENERATE_LONG_RANDOM_STRING

DB__HOST=db
DB__PORT=5432
DB__USER=botuser
DB__PASSWORD=STRONG_PASSWORD
DB__NAME=telegram_bot

REDIS__HOST=redis
REDIS__PORT=6379
REDIS__USER=default
REDIS__PASSWORD=STRONG_PASSWORD
REDIS__DB=0

API__HOST=0.0.0.0
API__PORT=8000
API__DEBUG=false

WEBAPP__URL=https://your-domain.com
```

Notes:
- `WEBHOOK__PORT=8000` aligns with the default nginx upstream config.
- Keep `API__DEBUG=false` in production.
- The webhook path is taken from `TG__WEBHOOK_PATH`.

## 3. TLS Certificate (Lets Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

## 4. nginx Configuration

The repo ships with a containerized nginx for local and staging. For production TLS you can:

Option A: Terminate TLS in host nginx and proxy to Docker.
Option B: Use a TLS-enabled nginx container.

If you enable webhooks, ensure your reverse proxy forwards `TG__WEBHOOK_PATH` to the bot API.

Below is an example for host nginx:

```nginx
upstream api_backend {
    server 127.0.0.1:8000;
}

upstream webapp_backend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://telegram.org; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.telegram.org; img-src 'self' data: https:; font-src 'self' data:;" always;

    location /webhook {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://webapp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Adjust upstream ports to match your deployment. If you use the `webapp` container behind nginx, expose it or proxy through the container network instead of `127.0.0.1:3000`.

## 5. Database Setup

```bash
docker compose up -d db redis
```

Apply migrations (recommended from a local dev environment):

```bash
uv run alembic upgrade head
```

If you build an image with dev dependencies, you can run it inside the container:

```bash
docker compose exec bot python -m alembic upgrade head
```

## 6. Deploy Application

```bash
docker compose up -d --build
```

Verify health:

```bash
curl https://your-domain.com/api/health
```

## 7. Set Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/telegram" \
  -d "secret_token=YOUR_WEBHOOK_SECRET"
```

Check webhook status:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 8. Monitoring and Logs

Docker logs:

```bash
docker compose logs -f bot
```

Metrics (if Prometheus client is enabled):
- `https://your-domain.com/metrics`

## 9. Backups

Example database backup script:

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/opt/aiogram-miniapp-template/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

docker compose exec -T db pg_dump -U $DB__USER $DB__NAME | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete
```

## 10. Updates

```bash
cd /opt/aiogram-miniapp-template
git pull origin main

docker compose build
docker compose up -d

uv run alembic upgrade head
```

## 11. Security Hardening

- Disable root SSH login and passwords
- Keep TLS certificates renewed
- Use strong credentials in `.env`
- Restrict SSH with Fail2ban

## Common Issues

### Webhook not receiving updates
**Symptoms:** Bot not responding in production.
**Cause:** Wrong webhook URL or secret token.
**Solution:** Verify `WEBHOOK__URL` and `TG__WEBHOOK_PATH` and call `setWebhook` again.

### 502 Bad Gateway
**Symptoms:** nginx returns 502.
**Cause:** `bot` container is down or wrong port mapping.
**Solution:** Check `docker compose ps` and ensure `WEBHOOK__PORT=8000` aligns with nginx.

### SSL certificate errors
**Symptoms:** HTTPS fails or browser warns.
**Cause:** Certificate expired or not installed.
**Solution:** Run `certbot renew` and reload nginx.

## Best Practices

1. DO keep `WEBHOOK__SECRET` long and random.
2. DO keep `API__DEBUG=false` in production.
3. DO set up backups from day one.
4. DO monitor logs after deployments.
5. DO run migrations before restarting services.

## Next Steps
- Read [Mini Apps Deployment](mini-apps/deployment.md)
- Review [Security](mini-apps/security.md)
- Configure monitoring and alerts
