"""Keyword opportunity API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.keyword_models import KeywordRequest, KeywordResponse, RankedKeyword
from app.services.keyword_service import KeywordService, KeywordServiceError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["keywords"])


def get_keyword_service() -> KeywordService:
    """Dependency provider for KeywordService."""
    return KeywordService()


@router.post(
    "/keyword-opportunities",
    response_model=KeywordResponse,
    status_code=status.HTTP_200_OK,
    summary="Rank keyword opportunities",
)
async def keyword_opportunities(
    request: KeywordRequest,
    service: KeywordService = Depends(get_keyword_service),
) -> KeywordResponse:
    """Rank keywords by opportunity score."""

    logger.info("Ranking keyword opportunities for %d keywords", len(request.keywords))

    try:
        ranked_keywords = service.analyze_keywords(
            [keyword.model_dump() for keyword in request.keywords]
        )
    except KeywordServiceError as exc:
        logger.warning("Invalid keyword opportunity request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected keyword opportunity ranking failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to rank keyword opportunities",
        ) from exc

    response = KeywordResponse(
        ranked_keywords=[
            RankedKeyword(
                keyword=keyword["keyword"],
                opportunity_score=keyword["opportunity_score"],
                rank=keyword["rank"],
            )
            for keyword in ranked_keywords
        ]
    )

    logger.info(
        "Ranked %d keyword opportunities successfully",
        len(response.ranked_keywords),
    )
    return response
