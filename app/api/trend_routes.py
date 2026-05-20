"""Trend analysis API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.trend_models import TrendRequest, TrendResponse
from app.tools.trend_analyzer import TrendAnalyzer, TrendAnalyzerError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

router = APIRouter(tags=["trends"])
trend_analyzer = TrendAnalyzer()


@router.post(
    "/trend-analysis",
    response_model=TrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze keyword trends",
)
async def trend_analysis(request: TrendRequest) -> TrendResponse:
    """Fetch and analyze Google Trends data for submitted keywords."""

    logger.info("Analyzing trends for %d keywords", len(request.keywords))

    try:
        analysis = trend_analyzer.fetch_google_trends(request.keywords)
        response = TrendResponse(**analysis)
    except TrendAnalyzerError as exc:
        logger.warning("Trend provider failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch trend data",
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
