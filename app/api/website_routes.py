"""Website analysis API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.website_models import WebsiteAnalysisRequest, WebsiteAnalysisResponse
from app.services.website_service import WebsiteService, WebsiteServiceError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["website-analysis"])


def get_website_service() -> WebsiteService:
    """Dependency provider for WebsiteService."""
    return WebsiteService()


@router.post(
    "/website-analysis",
    response_model=WebsiteAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze website SEO metrics",
)
async def analyze_website(
    request: WebsiteAnalysisRequest,
    service: WebsiteService = Depends(get_website_service),
) -> WebsiteAnalysisResponse:
    """Analyze a single website for SEO metrics and compute a basic score."""
    
    logger.info("Received website analysis request for %s", request.url)
    
    try:
        result = service.analyze_website(request.url)
    except WebsiteServiceError as exc:
        logger.error("Website analysis validation/service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected website analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to analyze website",
        ) from exc
        
    return WebsiteAnalysisResponse(**result)
