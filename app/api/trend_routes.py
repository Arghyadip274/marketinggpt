"""Trend analysis API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.trend_models import TrendRequest, TrendResponse
from app.services.trend_service import TrendService, TrendServiceError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["trends"])


def get_trend_service() -> TrendService:
    """Dependency provider for TrendService."""
    return TrendService()


@router.post(
    "/trend-analysis",
    response_model=TrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze keyword trends",
)
async def get_trends(
    request: TrendRequest,
    service: TrendService = Depends(get_trend_service),
) -> TrendResponse:
    """Fetch google trends data for a list of keywords."""

    logger.info("Analyzing trends for %d keywords", len(request.keywords))

    try:
        response = service.analyze_trends(request.keywords)
    except TrendServiceError as exc:
        logger.warning("Trend analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid trend analysis request or response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected trend analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to analyze keyword trends",
        ) from exc

    logger.info(
        "Trend analysis completed for %d keywords",
        len(response.trend_scores),
    )
    return response
