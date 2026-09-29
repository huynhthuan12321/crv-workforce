from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from source.api.middlewares import cors_settings
from source.api.middlewares import error_handler_middleware
from source.api.middlewares import LoggingMiddleware
from source.api.middlewares import RateLimitMiddleware
from source.api.routes import auth
from source.api.routes import health
from source.api.routes import attendance, client_errors, consent, employees, history, locations, messaging, outputs, payroll, reports, review, working
from source.config import settings
from source.constants import API_DOCS_URL
from source.constants import API_PREFIX
from source.constants import API_REDOC_URL
from source.domain.workforce_errors import WorkforceError
from source.services.rate_limit import attendance_rate_limiter


async def workforce_error_handler(_, exc: WorkforceError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


FIELD_LABELS = {
    "code": "Mã kho",
    "name": "Tên kho",
    "latitude": "Vĩ độ",
    "longitude": "Kinh độ",
    "radius_m": "Bán kính",
    "hourly_rate": "Đơn giá",
    "full_name": "Họ tên",
    "reason": "Lý do",
    "check_out_time": "Giờ ra",
    "effective_from": "Ngày hiệu lực",
    "effective_date": "Ngày hiệu lực",
    "mode": "Chế độ hiệu lực",
    "confirm_large_change": "Xác nhận thay đổi lớn",
    "cancel_reason": "Lý do hủy",
    "location_id": "Kho",
    "lat": "Vĩ độ",
    "lng": "Kinh độ",
    "accuracy_m": "Độ chính xác vị trí",
}


def _validation_field_name(loc: tuple | list) -> str:
    for part in reversed(loc):
        if isinstance(part, str) and part not in {"body", "query", "path"}:
            return part
    return "data"


def _validation_message(error: dict) -> str:
    error_type = str(error.get("type", ""))
    if "missing" in error_type:
        return "Bắt buộc nhập"
    if "string_too_short" in error_type:
        return "Quá ngắn"
    if "string_too_long" in error_type:
        return "Quá dài"
    if "greater_than" in error_type or "greater_than_equal" in error_type:
        return "Giá trị quá nhỏ"
    if "less_than" in error_type or "less_than_equal" in error_type:
        return "Giá trị quá lớn"
    if "date" in error_type:
        return "Ngày không hợp lệ"
    return "Không hợp lệ"


async def validation_error_handler(_, exc: RequestValidationError):
    from fastapi.responses import JSONResponse

    fields: dict[str, str] = {}
    labels: list[str] = []
    for error in exc.errors():
        name = _validation_field_name(error.get("loc", ()))
        label = FIELD_LABELS.get(name, name)
        fields[name] = _validation_message(error)
        if label not in labels:
            labels.append(label)
    listed = ", ".join(labels) if labels else "dữ liệu gửi lên"
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": f"Dữ liệu chưa hợp lệ: {listed}",
            "details": {"fields": fields},
        },
    )


def setup_api(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)
    app.add_middleware(LoggingMiddleware)

    app.add_middleware(CORSMiddleware, **cors_settings())

    app.add_exception_handler(WorkforceError, workforce_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.middleware("http")(error_handler_middleware)

    app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
    app.include_router(client_errors.router, prefix=f"{API_PREFIX}/client-errors", tags=["Client errors"])
    app.include_router(consent.router, prefix=f"{API_PREFIX}/consent", tags=["Consent"])
    app.include_router(attendance.router, prefix=f"{API_PREFIX}/attendance", tags=["Attendance"])
    app.include_router(outputs.router, prefix=f"{API_PREFIX}/outputs", tags=["Outputs"])
    app.include_router(history.router, prefix=f"{API_PREFIX}/history", tags=["History"])
    app.include_router(working.router, prefix=f"{API_PREFIX}/working-now", tags=["Working"])
    app.include_router(review.router, prefix=f"{API_PREFIX}/review", tags=["Review"])
    app.include_router(payroll.router, prefix=f"{API_PREFIX}/payroll", tags=["Payroll"])
    app.include_router(employees.router, prefix=f"{API_PREFIX}/employees", tags=["Employees"])
    app.include_router(locations.router, prefix=f"{API_PREFIX}/locations", tags=["Locations"])
    app.include_router(reports.router, prefix=f"{API_PREFIX}/reports", tags=["Reports"])
    app.include_router(messaging.router, prefix=API_PREFIX, tags=["Messaging"])

    @app.on_event("startup")
    async def startup_rate_limiter() -> None:
        await attendance_rate_limiter.start()

    @app.on_event("shutdown")
    async def shutdown_rate_limiter() -> None:
        await attendance_rate_limiter.close()


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
