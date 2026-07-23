"""Registers FastAPI exception handlers so every error response has a
consistent APIResponse shape."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.exceptions.base import AppException
from app.schemas.response import APIResponse

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning("%s on %s: %s", exc.__class__.__name__, request.url.path, exc.message)
        payload = APIResponse.fail(message=exc.message, errors=[exc.__class__.__name__])
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        payload = APIResponse.fail(message="Internal server error", errors=["InternalServerError"])
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))
