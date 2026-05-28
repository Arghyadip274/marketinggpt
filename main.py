"""FastAPI application entrypoint for MarketingGPT."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import TypedDict

from app.api.keyword_routes import router as keyword_router
from app.api.trend_routes import router as trend_router
from app.api.website_routes import router as website_router
from app.api.competitor_routes import router as competitor_router
from app.api.industry_routes import router as industry_router
from app.api.questionnaire_routes import router as questionnaire_router
from app.api.strategy_routes import router as strategy_router


SERVICE_NAME = "MarketingGPT API"
DEFAULT_VERSION = "0.1.0"
DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://localhost:8000")
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

logger = logging.getLogger(__name__)


class HealthResponse(TypedDict):
    """Health endpoint response payload."""

    status: str
    service: str
    version: str


def configure_logging() -> None:
    """Configure application logging from environment variables."""

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)


def get_app_version() -> str:
    """Return the application version exposed in metadata and health checks."""

    return os.getenv("APP_VERSION", DEFAULT_VERSION).strip() or DEFAULT_VERSION


def get_cors_origins() -> list[str]:
    """Return allowed CORS origins from environment configuration."""

    raw_origins = os.getenv("CORS_ORIGINS", "").strip()
    if not raw_origins:
        return list(DEFAULT_CORS_ORIGINS)

    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if not origins:
        raise ValueError("CORS_ORIGINS must include at least one origin when set")

    return origins


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown hooks."""

    configure_logging()
    logger.info("Starting %s", app.title)
    try:
        yield
    finally:
        logger.info("Shutting down %s", app.title)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    version = get_app_version()
    application = FastAPI(
        title=SERVICE_NAME,
        version=version,
        description="Keyword opportunity and trend analysis API.",
        lifespan=lifespan,
    )

    cors_origins = get_cors_origins()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials="*" not in cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.include_router(keyword_router)
    application.include_router(trend_router)
    application.include_router(website_router, prefix="/api")
    application.include_router(competitor_router, prefix="/api")
    application.include_router(industry_router, prefix="/api")
    application.include_router(questionnaire_router, prefix="/api")
    application.include_router(strategy_router, prefix="/api")

    @application.get("/health", tags=["health"])
    async def health() -> HealthResponse:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "version": version,
        }

    return application


app = create_app()
