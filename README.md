<div align="center">

<img width="250" height="250" alt="image" src="https://github.com/user-attachments/assets/a67162ea-bf43-4713-a27e-0581a8534b5b" />

<h1>Aiogram Bot Template with Mini Apps</h1>

<p><strong>Production-ready Telegram Bot + Mini Apps template with FastAPI backend and React frontend</strong></p>

<img alt="Static Badge" src="https://img.shields.io/badge/tag-v1.0-8A2BE2?style=flat&logo=task&logoColor=8A2BE2&labelColor=gray">
<img alt="Static Badge" src="https://img.shields.io/badge/python-v3.12-FBDE02?style=flat&logo=python&logoColor=FBDE02&labelColor=gray">
<img alt="Static Badge" src="https://img.shields.io/badge/react-18-61DAFB?style=flat&logo=react&logoColor=61DAFB&labelColor=gray">
<img alt="Static Badge" src="https://img.shields.io/badge/typescript-5-3178C6?style=flat&logo=typescript&logoColor=3178C6&labelColor=gray">
<img alt="Static Badge" src="https://img.shields.io/badge/license-MIT-12C4C4?style=flat&logo=gitbook&logoColor=12C4C4">
<br>
<img alt="Static Badge" src="https://img.shields.io/badge/Aiogram-v3.22.0-blue?style=flat">
<img alt="Static Badge" src="https://img.shields.io/badge/FastAPI-latest-009688?style=flat&logo=fastapi&logoColor=009688&labelColor=gray">

</div>

## 📌 Description
⠀

**Aiogram Bot Template with Mini Apps** — This template helps you quickly bootstrap Telegram bots with **Mini Apps** on the `aiogram` 3.x stack. It includes a ready project structure, command and message handlers, PostgreSQL/Redis integration, logging with `loguru`, internationalization, `aiogram-dialog`, dependency injection via `dishka`, webhook handling on `FastAPI`, **plus a React Mini App frontend with secure authentication and REST API backend**. The template is designed to remove routine setup and let you focus on your bot's logic and user experience.

⠀
## ✨ Features
⠀

**Telegram Bot Foundation:**
- Built on **aiogram 3.x** with async handlers and modern router setup
- **Dependency Injection** via Dishka for clean architecture
- **PostgreSQL + Redis** with SQLAlchemy ORM and async access
- **Alembic migrations** for database versioning
- **i18n support** with Fluent/Fluentogram
- **aiogram-dialog** for complex multi-step flows
- **FSM support** (Finite State Machine) for forms and wizards

**Mini Apps:**
- **React 18 + TypeScript** frontend with Vite
- **Telegram WebApp SDK** integration (theme, haptics, main button)
- **Secure authentication**: HMAC-SHA256 validation of `initData`
- **Replay attack protection** with 1-hour token expiration
- **Rate limiting**: 100 requests/minute per IP
- **Full i18next localization** (English/Russian)
- **Responsive, mobile-first UI**

**Security Hardened:**
- CORS restricted to Telegram domains
- Security headers via nginx (CSP, X-Frame-Options, etc.)
- Backend runs as non-root user
- SQL injection protection via ORM
- XSS protection via React auto-escaping

**DevOps Ready:**
- **Docker Compose** for one-command deployment
- **Multi-stage Dockerfiles** for optimized images
- **nginx** reverse proxy for API + WebApp
- **Health checks** for bot, PostgreSQL, Redis, webapp, and nginx
- **Pre-commit hooks** (Ruff, Mypy, Black, isort)

⠀
## 🔨 Functions
⠀

*   `/start` - Start the bot
*   `/language` - Change language
*   `/help` - Help
*   `/profile` - **Open your Mini App profile**
*   `/admin` - Command for administrators
*   `/dialog` - Demo dialog using `aiogram-dialog`
*   `/fsm` - Demo finite state machine form

⠀
## 🌐 Mini Apps
⠀

This template includes a **React Mini App** for user profiles:

*   **Frontend:** React 18 + TypeScript + Vite
*   **Backend:** FastAPI REST API with secure Telegram authentication
*   **Features:** User profiles, bio editing, i18n support, Telegram theme integration
*   **Security:** HMAC-SHA256 validation, replay attack protection, CORS restrictions, rate limiting

Try it: Send `/profile` to your bot!

⠀
## 🏗️ Architecture
⠀

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Telegram User  │─────▶│    Your Bot      │─────▶│   PostgreSQL     │
│   (Mobile App)   │      │  (aiogram 3.x)   │      │   + Redis        │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         │                         │
         │ Opens Mini App          │
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  React Mini App  │◀────▶│  FastAPI Backend │
│   (TypeScript)   │      │   (/api/...)     │
└──────────────────┘      └──────────────────┘
         │                         │
         └────────▶ nginx ◀────────┘
              (reverse proxy)
```

⠀
## 🗂️ Template structure
⠀

```
📁 aiogram-miniapp-template/
├── 📂 .github/              # CI/CD workflows, issue templates
├── 📂 docs/                 # Documentation
├── 📂 migrations/           # Alembic database migrations
├── 📂 nginx/                # nginx reverse proxy configs
├── 📂 scripts/              # Helper scripts
├── 📂 source/               # Main Python source code
│   ├── 📂 api/             # FastAPI backend for Mini Apps
│   ├── 📂 config/          # Configuration
│   ├── 📂 database/        # Models, repositories, UoW
│   ├── 📂 schemas/         # Pydantic schemas for API
│   ├── 📂 services/        # Business logic
│   ├── 📂 telegram/        # Bot handlers, keyboards, filters
│   └── 📂 utils/           # Utilities
├── 📂 tests/                # Test suite
├── 📂 webapp/               # React Mini App frontend
│   ├── 📂 public/locales/  # i18n translations
│   └── 📂 src/             # React components, hooks, API client
├── docker-compose.yml
├── Dockerfile
├── webapp.Dockerfile
└── pyproject.toml
```

Full project structure is documented in [docs/reference/project-structure.md](docs/reference/project-structure.md).

⠀
## 📋 About the content
⠀

*   `📁 source/` - Main application source code.
*   `📁 source/api/` - FastAPI backend for Mini Apps (routes, middlewares, utils).
*   `📁 source/config/` - Application configuration settings.
*   `📁 source/constants/` - Project constants.
*   `📁 source/data/` - Data generated by the application (e.g., logs).
*   `📁 source/database/` - Database interaction logic (models, repositories, UoW).
*   `📁 source/schemas/` - Pydantic schemas for API request/response validation.
*   `📁 source/services/` - Business logic layer.
*   `📁 source/telegram/` - Bot components (handlers, keyboards, filters, middlewares, states, dialogs).
*   `📁 source/utils/` - Helper utilities (logger, i18n, validators).
*   `📁 webapp/` - React Mini App frontend with TypeScript.
*   `📁 webapp/src/` - React components, hooks, pages, API client.
*   `📁 webapp/public/locales/` - i18n translation files for Mini App.
*   `📁 nginx/` - nginx configuration for reverse proxy.
*   `📁 docs/` - Development and deployment documentation.
*   `📁 scripts/` - Helper scripts for development tasks.
*   `📁 tests/` - Test suite.

⠀
## 📚 Documentation
⠀

Full documentation is available in the [`docs/`](docs/) folder:

**Getting Started:**
- [Installation & Setup](docs/getting-started.md)
- [Configuration Guide](docs/guides/configuration.md)

**Bot Development:**
- [Handlers](docs/guides/handlers.md)
- [Services](docs/guides/services.md)
- [Database](docs/guides/database.md)

**Mini Apps Development:**
- [Mini Apps Overview](docs/guides/mini-apps/README.md)
- [Quick Start](docs/guides/mini-apps/quickstart.md)
- [Authentication](docs/guides/mini-apps/authentication.md)
- [API Reference](docs/guides/mini-apps/api-reference.md)
- [Frontend Guide](docs/guides/mini-apps/frontend-guide.md)
- [Security](docs/guides/mini-apps/security.md)
- [Troubleshooting](docs/guides/mini-apps/troubleshooting.md)

**Deployment:**
- [Docker Guide](docs/guides/docker.md)
- [Production Deployment](docs/guides/deployment.md)

**Reference:**
- [Architecture](docs/reference/architecture.md)
- [REST API Reference](docs/reference/rest-api.md)

⠀
## 🔓 Environment Variables
⠀

**Backend & Bot (`.env`):**

| Environment Variable Name | Description |
|---------------------------|-------------|
| ENVIRONMENT               | Application environment (`development`, `test`, `production`). |
| TG__WEBHOOK_USE           | Boolean value (`True`/`False`) indicating whether to use webhooks (`True`) or long polling (`False`). |
| TG__WEBHOOK_PATH          | Path for Telegram to send webhook updates (appended to `WEBHOOK__URL`). |
| TG__BOT_TOKEN             | Your Telegram bot token, obtained from `@BotFather` in Telegram. |
| TG__ADMIN_IDS             | List of Telegram user IDs (JSON list or comma-separated) who will have administrator rights in the bot. |
| WEBHOOK__URL              | Public URL where Telegram will send updates if webhooks are enabled. |
| WEBHOOK__HOST             | Host or IP address where the webhook server will listen for incoming connections (usually `0.0.0.0`). |
| WEBHOOK__PORT             | Port on which the webhook server will listen for incoming connections. |
| WEBHOOK__SECRET           | Secret token that Telegram includes in webhook request headers to verify authenticity. |
| DB__HOST                  | Database server host. |
| DB__PORT                  | Port for connecting to the database. |
| DB__USER                  | Username for database authentication. |
| DB__PASSWORD              | Password for database authentication. |
| DB__NAME                  | Name of the database to connect to. |
| REDIS__HOST               | Redis server host used for FSM and/or caching. |
| REDIS__PORT               | Port for connecting to the Redis server. |
| REDIS__USER               | Username for Redis authentication (if used). |
| REDIS__PASSWORD           | Password for Redis authentication (if used). |
| REDIS__DB                 | Redis database index to use (a number from 0 to 15, default is 0). |
| **API__HOST**             | **FastAPI host for Mini Apps API (usually `0.0.0.0`).** |
| **API__PORT**             | **FastAPI port (default `8000`).** |
| **API__DEBUG**            | **Debug mode for API (`true`/`false`).** |
| **WEBAPP__URL**           | **Public URL where Mini App is hosted (e.g., `https://your-domain.com`).** |

**Mini App Frontend (`webapp/.env`):**

| Environment Variable Name | Description |
|---------------------------|-------------|
| VITE_API_URL              | Base URL for the Mini App API (default `/api`). |

Note: docker-compose maps `WEBHOOK__PORT` to the host (defaults to `8080` if not set).

⠀
## 💻 Bot Setup
⠀

### 📦 Using Docker (Recommended)
⠀

1.  Clone the repository and navigate into the project directory:

    ```shell
    git clone https://github.com/MrConsoleka/aiogram-miniapp-template.git
    cd aiogram-miniapp-template
    ```

2.  Configure environment variables:

    ```shell
    cp .env.example .env
    cp webapp/.env.example webapp/.env
    # Edit .env and webapp/.env with your settings
    ```

3.  Start all services with Docker Compose:

    ```shell
    docker compose up -d
    ```

⠀
### 📦 Using UV (Local Development)
⠀

1.  Clone the repository and navigate into the project directory:

    ```shell
    git clone https://github.com/MrConsoleka/aiogram-miniapp-template.git
    cd aiogram-miniapp-template
    ```

2.  Ensure you have `uv` installed. If not, you can install it using `pip`:

    ```shell
    pip install uv
    ```

3.  Create a virtual environment:

    ```shell
    make venv
    ```

4.  Activate the virtual environment:

    ```shell
    # For Linux or macOS:
    source .venv/bin/activate

    # For Windows:
    .venv\Scripts\activate
    ```

5.  Install dependencies:

    ```shell
    make install
    ```

6.  Configure environment variables:

    ```shell
    cp .env.example .env
    cp webapp/.env.example webapp/.env
    # Edit .env and webapp/.env with your settings
    ```

7.  Run the bot:

    ```shell
    make run
    ```

8.  (Optional) Run Mini App frontend separately:

    ```shell
    # In a separate terminal
    cd webapp
    npm install
    npm run dev
    ```

    If running Vite dev server, set `WEBAPP__URL=http://localhost:3000` in `.env`.

⠀
## 🗄️ Migrations
⠀

Create and apply migrations with Alembic:

```shell
make migration MESSAGE="create users"
uv run alembic upgrade head
```

⠀
## 🧪 Testing
⠀

Run tests locally:

```shell
uv run pytest tests/
```

⠀
## 🧰 Pre-commit
⠀

```shell
pre-commit install
pre-commit run --all-files
```

⠀
## 🧩 Development Services
⠀

```shell
make dev-up
make dev-down
```

⠀
## 🗃️ Stack of Technologies
⠀

**Backend:**
*   [aiogram-3x](https://github.com/aiogram/aiogram) - Asynchronous framework for the Telegram Bot API.
*   [aiogram-dialog](https://github.com/aiogram/aiogram-dialog) - Dialog manager for building interactive flows.
*   [dishka](https://github.com/reagento/dishka) - Dependency injection container.
*   [fastapi](https://github.com/tiangolo/fastapi) & [uvicorn](https://github.com/encode/uvicorn) - Webhook server and Mini Apps API.
*   [pydantic](https://github.com/pydantic/pydantic) & [pydantic-settings](https://github.com/pydantic/pydantic-settings) - Data validation and configuration management.
*   [postgresql](https://github.com/postgres/postgres) with [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) and [asyncpg](https://github.com/MagicStack/asyncpg) - Database layer.
*   [redis](https://redis.io/) - In-memory data store for FSM and caching.
*   [loguru](https://github.com/Delgan/loguru) - Logging library.
*   [alembic](https://alembic.sqlalchemy.org/) - Database migrations.

**Frontend (Mini Apps):**
*   [react](https://react.dev/) - UI library.
*   [typescript](https://www.typescriptlang.org/) - Type safety.
*   [vite](https://vitejs.dev/) - Build tool and dev server.
*   [telegram-webapp-sdk](https://core.telegram.org/bots/webapps) - Telegram Mini Apps API.
*   [i18next](https://www.i18next.com/) - Internationalization.
*   [zustand](https://github.com/pmndrs/zustand) - State management.

**DevOps:**
*   [docker](https://www.docker.com/) & [docker-compose](https://docs.docker.com/compose/) - Containerization and orchestration.
*   [nginx](https://nginx.org/) - Reverse proxy and web server.
*   [ruff](https://github.com/astral-sh/ruff) - Fast Python linter.
*   [mypy](https://github.com/python/mypy) - Static type checker.
*   [pre-commit](https://github.com/pre-commit/pre-commit) - Git hooks framework.

⠀
## 💼 Credits
⠀

-   [aiogram-bot-template](https://github.com/MrConsoleka/aiogram-bot-template) - My scalable template for Telegram bots on aiogram without Mini Apps.

⠀
## 👤 Author
⠀
**© Roman Alekseev**
