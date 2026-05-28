"""Service layer for keyword opportunity analysis."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from app.tools.keyword_detector import KeywordOpportunityDetector, RankedKeywordOpportunity

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class KeywordServiceError(Exception):
    """Base exception for keyword service failures."""


class KeywordService:
    """Service layer for analyzing and ranking keyword opportunities.
    
    This class adheres to clean architecture principles by wrapping the core
    business logic (KeywordOpportunityDetector) and providing a safe,
    error-handled interface for upstream consumers (e.g., API routes).
    """

    def __init__(self, detector: KeywordOpportunityDetector | None = None) -> None:
        """Initialize the KeywordService.
        
        Args:
            detector: Optional injected instance of KeywordOpportunityDetector.
                      If not provided, a default instance is created.
        """
        self.detector = detector or KeywordOpportunityDetector()

    def analyze_keywords(self, keywords: list[Mapping[str, Any]]) -> list[RankedKeywordOpportunity]:
        """Analyze and rank a list of keyword dictionaries.
        
        Args:
            keywords: A list of dictionaries containing keyword metrics 
                      (keyword, search_volume, trend_growth, intent_score, difficulty).
            
        Returns:
            A list of RankedKeywordOpportunity dictionaries, sorted by highest opportunity.
            
        Raises:
            KeywordServiceError: If the input data is invalid or analysis fails.
        """
        logger.info("Service received request to analyze %d keywords", len(keywords) if keywords else 0)
        
        if not keywords:
            logger.warning("No keywords provided to service.")
            return []

        try:
            # We enforce normalization by default in the service layer
            ranked_keywords = self.detector.rank_keywords(keywords, normalize=True)
            logger.info("Service successfully ranked %d keywords", len(ranked_keywords))
            return ranked_keywords
            
        except (ValueError, TypeError) as exc:
            logger.error("Data validation error during keyword analysis: %s", exc)
            raise KeywordServiceError(f"Invalid keyword data provided: {exc}") from exc
            
        except Exception as exc:
            logger.exception("Unexpected error occurred during keyword analysis")
            raise KeywordServiceError("An unexpected error occurred while analyzing keywords") from exc
