"""Marketing Strategy API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.strategy_models import StrategyRequest, StrategyResponse
from app.services.strategy_service import StrategyService, StrategyServiceError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["strategy"])


def get_strategy_service() -> StrategyService:
    """Dependency provider for StrategyService."""
    return StrategyService()


@router.post(
    "/marketing-strategy",
    response_model=StrategyResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate master marketing strategy",
)
async def generate_marketing_strategy(
    request: StrategyRequest,
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    """Combine all marketing intelligence layers into a unified strategy."""
    logger.info("Received marketing strategy request for: %s", request.website_url)

    try:
        response = service.generate_strategy(request)
        return response
    except StrategyServiceError as exc:
        logger.warning("Strategy generation validation/service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during strategy generation.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate marketing strategy.",
        ) from exc
