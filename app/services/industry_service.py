"""Service layer for industry analysis."""

from __future__ import annotations

import logging

from app.tools.industry_analyzer import IndustryIntelligenceAnalyzer, IndustryIntelligenceReport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class IndustryServiceError(Exception):
    """Base exception for industry service failures."""


class IndustryService:
    """Service layer for fetching and analyzing industry intelligence.
    
    This class adheres to clean architecture principles by wrapping the core
    business logic (IndustryIntelligenceAnalyzer) and providing a safe, 
    error-handled interface for upstream API routes.
    """

    def __init__(self, analyzer: IndustryIntelligenceAnalyzer | None = None) -> None:
        """Initialize the IndustryService.
        
        Args:
            analyzer: Optional injected instance of IndustryIntelligenceAnalyzer.
                      If not provided, a default instance is created.
        """
        self.analyzer = analyzer or IndustryIntelligenceAnalyzer()

    def analyze_industry(self, industry_name: str) -> IndustryIntelligenceReport:
        """Fetch marketing intelligence for the requested industry.
        
        Args:
            industry_name: The name of the industry to analyze (e.g., 'SaaS', 'Real Estate').
            
        Returns:
            An IndustryIntelligenceReport dictionary containing structured intelligence
            such as common patterns, channels, offers, and messaging benchmarks.
            
        Raises:
            IndustryServiceError: If the input data is invalid or the underlying
                                  analysis operation fails unexpectedly.
        """
        logger.info("Service received request to analyze industry: '%s'", industry_name)
        
        if not industry_name or not isinstance(industry_name, str):
            logger.error("Invalid industry name provided to service: %r", industry_name)
            raise IndustryServiceError("A valid industry name string must be provided.")

        try:
            result = self.analyzer.analyze_industry(industry_name)
            logger.info(
                "Service successfully analyzed industry, mapped to: %s", 
                result.get("industry_matched", "Unknown")
            )
            return result
            
        except (ValueError, TypeError, AttributeError) as exc:
            logger.error("Data validation error during industry analysis: %s", exc)
            raise IndustryServiceError(f"Invalid industry data format: {exc}") from exc
            
        except Exception as exc:
            logger.exception("Unexpected error occurred during industry analysis")
            raise IndustryServiceError("An unexpected error occurred while analyzing the industry") from exc
