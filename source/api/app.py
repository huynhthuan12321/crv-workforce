from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from source.api.middlewares import cors_settings
from source.api.middlewares import error_handler_middleware
from source.api.middlewares import LoggingMiddleware
from source.api.middlewares import RateLimitMiddleware
from source.api.routes import auth
from source.api.routes import health
from source.api.routes import users
from source.config import settings
from source.constants import API_DOCS_URL
from source.constants import API_PREFIX
from source.constants import API_REDOC_URL


def setup_api(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
    app.add_middleware(LoggingMiddleware)

    app.add_middleware(CORSMiddleware, **cors_settings())

    app.middleware("http")(error_handler_middleware)

    app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
    app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["Users"])


def create_app(container) -> FastAPI:
    app = FastAPI(
        title="Telegram Mini App API",
        version="1.0.0",
        docs_url=API_DOCS_URL if settings.api.debug else None,
        redoc_url=API_REDOC_URL if settings.api.debug else None,
    )

    setup_dishka(container, app)
    setup_api(app)

    return app
