"""FastAPI application entrypoint for MarketingGPT."""

from __future__ import annotations
import os
import logging
import time

# Force load key from .env to bypass caching (same as frontend fix)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GOOGLE_API_KEY="):
                os.environ["GOOGLE_API_KEY"] = line.split("=")[1].strip().strip('"').strip("'")

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Config and Utils
from app.config.settings import settings
from app.utils.logger import configure_logging
from app.api.exceptions import setup_exception_handlers

# Routers
from app.api.keyword_routes import router as keyword_router
from app.api.trend_routes import router as trend_router
from app.api.website_routes import router as website_router
from app.api.competitor_routes import router as competitor_router
from app.api.industry_routes import router as industry_router
from app.api.questionnaire_routes import router as questionnaire_router
from app.api.strategy_routes import router as strategy_router
from app.api.health_routes import router as health_router
from app.api.chat_routes import router as chat_router
from app.api.rag_routes import router as rag_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown hooks."""
    configure_logging()
    logger.info("Starting %s v%s in %s mode", settings.app_name, settings.app_version, settings.environment)
    try:
        yield
    finally:
        logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Marketing intelligence and strategy generation API.",
        lifespan=lifespan,
    )

    # Global Exception Handlers
    setup_exception_handlers(application)

    # CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Logging Middleware
    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            "%s %s - HTTP %d - %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        return response

    # Include API Routers
    from app.api.chat_routes import router as chat_router
    from app.api.rag_routes import router as rag_router
    application.include_router(chat_router)
    application.include_router(rag_router)
    
    application.include_router(health_router)
    application.include_router(keyword_router)
    application.include_router(trend_router)
    application.include_router(website_router, prefix=settings.api_v1_prefix)
    application.include_router(competitor_router, prefix=settings.api_v1_prefix)
    application.include_router(industry_router, prefix=settings.api_v1_prefix)
    application.include_router(questionnaire_router, prefix=settings.api_v1_prefix)
    application.include_router(strategy_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
