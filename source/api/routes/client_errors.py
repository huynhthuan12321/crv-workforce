from typing import Any

from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter()


class ClientErrorBody(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    stack: str | None = Field(default=None, max_length=4000)
    tab: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    app_version: str | None = Field(default=None, max_length=64)


def _clean(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value.replace("\r", " ").replace("\n", " ")[:limit]


@router.post("")
async def report_client_error(body: ClientErrorBody, request: Request) -> dict[str, Any]:
    logger.warning(
        "client render error | message={} | tab={} | role={} | app_version={} | ip={} | stack={}",
        _clean(body.message, 500),
        _clean(body.tab, 64),
        _clean(body.role, 64),
        _clean(body.app_version, 64),
        request.client.host if request.client else None,
        _clean(body.stack, 2000),
    )
    return {"data": {"ok": True}}
