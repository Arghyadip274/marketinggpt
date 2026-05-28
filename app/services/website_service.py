"""Service layer for website analysis."""

from __future__ import annotations

import logging

from app.tools.website_analyzer import WebsiteSEOAnalyzer, SEOAnalysisResult

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WebsiteServiceError(Exception):
    """Base exception for website service failures."""


class WebsiteService:
    """Service layer for fetching and analyzing website SEO metrics.
    
    This class adheres to clean architecture principles by wrapping the core
    business logic (WebsiteSEOAnalyzer) and providing a safe, error-handled 
    interface for upstream API routes.
    """

    def __init__(self, analyzer: WebsiteSEOAnalyzer | None = None) -> None:
        """Initialize the WebsiteService.
        
        Args:
            analyzer: Optional injected instance of WebsiteSEOAnalyzer.
                      If not provided, a default instance is created.
        """
        self.analyzer = analyzer or WebsiteSEOAnalyzer()

    def analyze_website(self, url: str) -> SEOAnalysisResult:
        """Fetch and analyze SEO metrics for a target website.
        
        Args:
            url: The fully qualified URL of the website to analyze.
            
        Returns:
            An SEOAnalysisResult dictionary containing extracted metrics
            and a computed SEO score.
            
        Raises:
            WebsiteServiceError: If the input data is invalid or the underlying
                                 analysis operation fails unexpectedly.
        """
        logger.info("Service received request to analyze website: %s", url)
        
        if not url or not isinstance(url, str):
            logger.error("Invalid URL provided to website service: %r", url)
            raise WebsiteServiceError("A valid URL string must be provided.")

        try:
            # The analyzer itself handles fetch timeouts/errors and returns an empty dict safely
            result = self.analyzer.analyze(url)
            logger.info("Service successfully analyzed website, achieved SEO score: %d", result.get("seo_score", 0))
            return result
            
        except (ValueError, TypeError) as exc:
            logger.error("Data validation error during website analysis: %s", exc)
            raise WebsiteServiceError(f"Invalid website data format: {exc}") from exc
            
        except Exception as exc:
            logger.exception("Unexpected error occurred during website analysis")
            raise WebsiteServiceError("An unexpected error occurred while analyzing the website") from exc
