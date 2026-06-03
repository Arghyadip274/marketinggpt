"""Health monitoring and system status API routes."""

import logging
import time
from typing import Any

from fastapi import APIRouter
from typing_extensions import TypedDict

from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track start time for uptime calculation
_START_TIME = time.time()


class HealthResponse(TypedDict):
    """Basic health endpoint response payload."""
    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: float


class DetailedHealthResponse(TypedDict):
    """Detailed health endpoint response payload."""
    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: float
    dependencies: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic service health check."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
    }


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health() -> DetailedHealthResponse:
    """Detailed health check validating internal dependencies and components."""
    dependencies = {}
    
    # Check if core services can be instantiated
    try:
        from app.services.strategy_service import StrategyService
        _ = StrategyService()
        dependencies["strategy_service"] = "ok"
    except Exception as exc:
        logger.error("Healthcheck failed to initialize StrategyService: %s", exc)
        dependencies["strategy_service"] = "unhealthy"

    # Future: check ChromaDB connection here
    dependencies["vector_store"] = "not_configured"

    system_status = "ok" if all(v == "ok" for v in dependencies.values()) else "degraded"

    return {
        "status": system_status,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "dependencies": dependencies,
    }
