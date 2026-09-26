# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email the maintainer directly: mrconsoleka.work@gmail.com
3. Include detailed steps to reproduce
4. Allow reasonable time for a fix before public disclosure

## Security Features

### Telegram Mini Apps Authentication

| Feature | Status | Description |
|---------|--------|-------------|
| HMAC-SHA256 Validation | ✅ | Validates initData signature |
| Replay Attack Protection | ✅ | 1 hour token expiration |
| CORS Restrictions | ✅ | Only Telegram domains allowed |
| Rate Limiting | ✅ | 100 requests/minute per IP |

### API Security

| Feature | Status | Description |
|---------|--------|-------------|
| SQL Injection Protection | ✅ | SQLAlchemy ORM with parameterized queries |
| XSS Protection | ✅ | React auto-escaping + CSP headers |
| Security Headers | ✅ | X-Frame-Options, CSP, etc. via nginx |

### Infrastructure

| Feature | Status | Description |
|---------|--------|-------------|
| Non-root Container | ✅ | App runs as unprivileged user |
| Secrets Management | ✅ | Environment variables, not in code |
| Health Checks | ✅ | Docker health checks for all services |

## Best Practices for Deployment

1. **Always use HTTPS** in production
2. **Rotate bot tokens** periodically
3. **Keep dependencies updated** - run `npm audit` and `pip-audit` regularly
4. **Monitor logs** for suspicious activity
5. **Use strong passwords** for database and Redis
