"""Service layer for competitor analysis."""

from __future__ import annotations

import logging

from app.tools.competitor_analyzer import CompetitorIntelligenceAnalyzer, CompetitorIntelligenceReport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CompetitorServiceError(Exception):
    """Base exception for competitor service failures."""


class CompetitorService:
    """Service layer for fetching and analyzing competitor intelligence.
    
    This class adheres to clean architecture principles by wrapping the core
    business logic (CompetitorIntelligenceAnalyzer) and providing a safe, 
    error-handled interface for upstream API routes.
    """

    def __init__(self, analyzer: CompetitorIntelligenceAnalyzer | None = None) -> None:
        """Initialize the CompetitorService.
        
        Args:
            analyzer: Optional injected instance of CompetitorIntelligenceAnalyzer.
                      If not provided, a default instance is created.
        """
        self.analyzer = analyzer or CompetitorIntelligenceAnalyzer()

    def analyze_competitors(self, urls: list[str]) -> CompetitorIntelligenceReport:
        """Fetch and analyze intelligence for a list of competitor websites.
        
        Args:
            urls: A list of fully qualified URLs of the competitor websites.
            
        Returns:
            A CompetitorIntelligenceReport dictionary containing extracted metrics
            for each competitor and a top-level market summary.
            
        Raises:
            CompetitorServiceError: If the input data is invalid or the underlying
                                    analysis operation fails unexpectedly.
        """
        logger.info("Service received request to analyze %d competitors", len(urls) if urls else 0)
        
        if not urls or not isinstance(urls, list):
            logger.error("Invalid URLs provided to competitor service: %r", urls)
            raise CompetitorServiceError("A valid list of URL strings must be provided.")

        try:
            # The analyzer iterates through the URLs and handles individual fetch failures
            result = self.analyzer.analyze_competitors(urls)
            logger.info(
                "Service successfully analyzed competitors, dominant strategy: %s", 
                result.get("market_summary", {}).get("dominant_market_strategy", "Unknown")
            )
            return result
            
        except (ValueError, TypeError) as exc:
            logger.error("Data validation error during competitor analysis: %s", exc)
            raise CompetitorServiceError(f"Invalid competitor data format: {exc}") from exc
            
        except Exception as exc:
            logger.exception("Unexpected error occurred during competitor analysis")
            raise CompetitorServiceError("An unexpected error occurred while analyzing competitors") from exc
