"""Industry analysis API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.industry_models import IndustryAnalysisRequest, IndustryAnalysisResponse
from app.services.industry_service import IndustryService, IndustryServiceError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["industry-analysis"])


def get_industry_service() -> IndustryService:
    """Dependency provider for IndustryService."""
    return IndustryService()


@router.post(
    "/industry-analysis",
    response_model=IndustryAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze industry marketing patterns",
)
async def analyze_industry(
    request: IndustryAnalysisRequest,
    service: IndustryService = Depends(get_industry_service),
) -> IndustryAnalysisResponse:
    """Analyze a specific industry and return marketing intelligence benchmarks."""
    
    logger.info("Received industry analysis request for '%s'", request.industry_name)
    
    try:
        result = service.analyze_industry(request.industry_name)
    except IndustryServiceError as exc:
        logger.error("Industry analysis validation/service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected industry analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to analyze industry",
        ) from exc
        
    return IndustryAnalysisResponse(**result)
