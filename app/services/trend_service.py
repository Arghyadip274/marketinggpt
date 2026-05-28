"""Service layer for trend analysis."""

from __future__ import annotations

import logging

from app.tools.trend_analyzer import TrendAnalyzer, TrendAnalyzerError, TrendAnalysisResult

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TrendServiceError(Exception):
    """Base exception for trend service failures."""


class TrendService:
    """Service layer for fetching and analyzing Google Trends data.
    
    This class adheres to clean architecture principles by wrapping the core
    business logic (TrendAnalyzer) and providing a safe, error-handled 
    interface for upstream consumers.
    """

    def __init__(self, analyzer: TrendAnalyzer | None = None) -> None:
        """Initialize the TrendService.
        
        Args:
            analyzer: Optional injected instance of TrendAnalyzer.
                      If not provided, a default instance is created.
        """
        self.analyzer = analyzer or TrendAnalyzer()

    def analyze_trends(self, keywords: list[str]) -> TrendAnalysisResult:
        """Fetch and analyze trend metrics for a list of keywords.
        
        Args:
            keywords: A list of keyword strings to analyze.
            
        Returns:
            A TrendAnalysisResult dictionary containing trend scores, rising keywords, 
            and a ranked comparison payload.
            
        Raises:
            TrendServiceError: If the input data is invalid or the underlying
                               trend fetch operation fails.
        """
        logger.info("Service received request to analyze trends for %d keywords", len(keywords) if keywords else 0)
        
        if not keywords:
            logger.warning("No keywords provided to trend service.")
            # Return an empty payload structure if no keywords exist
            return {
                "trend_scores": {},
                "rising_keywords": [],
                "comparison": []
            }

        try:
            result = self.analyzer.fetch_google_trends(keywords)
            logger.info("Service successfully analyzed trends for %d keywords", len(result["comparison"]))
            return result
            
        except (ValueError, TypeError) as exc:
            logger.error("Data validation error during trend analysis: %s", exc)
            raise TrendServiceError(f"Invalid keyword data provided: {exc}") from exc
            
        except TrendAnalyzerError as exc:
            logger.error("Google Trends extraction failed: %s", exc)
            raise TrendServiceError(f"Trend data extraction failed: {exc}") from exc
            
        except Exception as exc:
            logger.exception("Unexpected error occurred during trend analysis")
            raise TrendServiceError("An unexpected error occurred while analyzing trends") from exc
