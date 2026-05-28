"""Competitor intelligence API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.competitor_models import CompetitorAnalysisRequest, CompetitorAnalysisResponse
from app.services.competitor_service import CompetitorService, CompetitorServiceError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["competitor-analysis"])


def get_competitor_service() -> CompetitorService:
    """Dependency provider for CompetitorService."""
    return CompetitorService()


@router.post(
    "/competitor-analysis",
    response_model=CompetitorAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze competitor websites",
)
async def analyze_competitor(
    request: CompetitorAnalysisRequest,
    service: CompetitorService = Depends(get_competitor_service),
) -> CompetitorAnalysisResponse:
    """Analyze a list of competitor URLs for messaging and intelligence."""
    
    logger.info("Received competitor analysis request for %d URLs", len(request.competitor_urls))
    
    try:
        result = service.analyze_competitors(request.competitor_urls)
    except CompetitorServiceError as exc:
        logger.error("Competitor analysis validation/service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected competitor analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to analyze competitors",
        ) from exc
        
    return CompetitorAnalysisResponse(**result)
