"""Global exception handlers for the FastAPI application."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.services.strategy_service import StrategyServiceError

logger = logging.getLogger(__name__)


class APIErrorResponse:
    """Helper to format structured error responses."""
    
    @staticmethod
    def build(status_code: int, message: str, path: str, details: Any = None) -> dict[str, Any]:
        """Build a standardized error payload."""
        error_payload = {
            "error": {
                "code": status_code,
                "message": message,
                "path": path,
            }
        }
        if details:
            error_payload["error"]["details"] = details
        return error_payload


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""

    @app.exception_handler(StrategyServiceError)
    async def strategy_service_exception_handler(request: Request, exc: StrategyServiceError) -> JSONResponse:
        logger.warning("StrategyServiceError at %s: %s", request.url.path, str(exc))
        payload = APIErrorResponse.build(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(exc),
            path=request.url.path
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Validation error at %s: %s", request.url.path, exc.errors())
        payload = APIErrorResponse.build(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed.",
            path=request.url.path,
            details=exc.errors()
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("ValueError at %s: %s", request.url.path, str(exc))
        payload = APIErrorResponse.build(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(exc),
            path=request.url.path
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception at %s", request.url.path)
        payload = APIErrorResponse.build(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error.",
            path=request.url.path
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)
