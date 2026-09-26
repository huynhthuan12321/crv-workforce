from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from source.schemas.responses import ApiResponse


async def error_handler_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except StarletteHTTPException as exc:
        payload = ApiResponse(success=False, error=str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())
    except Exception as exc:
        logger.exception("Unhandled API error", error=str(exc))
        payload = ApiResponse(success=False, error="Internal server error")
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(),
        )
