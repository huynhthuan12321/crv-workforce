from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from source.api.middlewares import cors_settings
from source.api.middlewares import error_handler_middleware
from source.api.middlewares import LoggingMiddleware
from source.api.middlewares import RateLimitMiddleware
from source.api.routes import auth
from source.api.routes import health
from source.api.routes import attendance, consent, employees, history, outputs, payroll, reports, review
from source.config import settings
from source.constants import API_DOCS_URL
from source.constants import API_PREFIX
from source.constants import API_REDOC_URL
from source.domain.workforce_errors import WorkforceError


async def workforce_error_handler(_, exc: WorkforceError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


def setup_api(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
    app.add_middleware(LoggingMiddleware)

    app.add_middleware(CORSMiddleware, **cors_settings())

    app.add_exception_handler(WorkforceError, workforce_error_handler)
    app.middleware("http")(error_handler_middleware)

    app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
    app.include_router(consent.router, prefix=f"{API_PREFIX}/consent", tags=["Consent"])
    app.include_router(attendance.router, prefix=f"{API_PREFIX}/attendance", tags=["Attendance"])
    app.include_router(outputs.router, prefix=f"{API_PREFIX}/outputs", tags=["Outputs"])
    app.include_router(history.router, prefix=f"{API_PREFIX}/history", tags=["History"])
    app.include_router(review.router, prefix=f"{API_PREFIX}/review", tags=["Review"])
    app.include_router(payroll.router, prefix=f"{API_PREFIX}/payroll", tags=["Payroll"])
    app.include_router(employees.router, prefix=f"{API_PREFIX}/employees", tags=["Employees"])
    app.include_router(reports.router, prefix=f"{API_PREFIX}/reports", tags=["Reports"])


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
