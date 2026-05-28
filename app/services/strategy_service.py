"""Orchestration service for generating a unified marketing strategy."""

import logging
from typing import Any

from app.models.strategy_models import StrategyRequest, StrategyResponse
from app.models.keyword_models import RankedKeyword

# Import all sub-services
from app.services.keyword_service import KeywordService
from app.services.trend_service import TrendService
from app.services.website_service import WebsiteService
from app.services.competitor_service import CompetitorService
from app.services.industry_service import IndustryService

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class StrategyServiceError(Exception):
    """Base exception for strategy generation failures."""


class StrategyService:
    """Central orchestration engine combining all analysis modules."""

    def __init__(
        self,
        keyword_service: KeywordService | None = None,
        trend_service: TrendService | None = None,
        website_service: WebsiteService | None = None,
        competitor_service: CompetitorService | None = None,
        industry_service: IndustryService | None = None,
    ) -> None:
        """Initialize with sub-services via dependency injection."""
        self.keyword_service = keyword_service or KeywordService()
        self.trend_service = trend_service or TrendService()
        self.website_service = website_service or WebsiteService()
        self.competitor_service = competitor_service or CompetitorService()
        self.industry_service = industry_service or IndustryService()

    def generate_strategy(self, request: StrategyRequest) -> StrategyResponse:
        """Call all sub-services and aggregate intelligence into a unified strategy."""
        logger.info("Starting strategy generation for %s", request.website_url)

        try:
            # 1. Analyze Website
            website_data = self.website_service.analyze_website(request.website_url)
            seo_score = website_data.get("seo_score", 0)

            # 2. Analyze Competitors
            competitor_data = self.competitor_service.analyze_competitors(request.competitors)
            comp_list = competitor_data.get("competitors", [])
            comp_summary = competitor_data.get("market_summary", {})

            # 3. Analyze Industry
            # Heuristically infer industry from business profile or default to 'generic'
            # Let's extract an industry hint from the profile values
            profile_text = " ".join(str(v) for v in request.business_profile.profile_data.values()).lower()
            industry_name = "generic"
            for ind in ["saas", "ecommerce", "real estate", "healthcare", "finance"]:
                if ind in profile_text:
                    industry_name = ind
                    break
            
            industry_data = self.industry_service.analyze_industry(industry_name)

            # 4. Analyze Keywords & Trends
            keyword_dicts = [
                {
                    "keyword": kw, 
                    "search_volume": 1000, 
                    "difficulty": 50, 
                    "cpc": 1.0, 
                    "trend_growth": 10, 
                    "intent_score": 80
                } 
                for kw in request.keywords
            ]
            ranked_keywords_data = self.keyword_service.analyze_keywords(keyword_dicts)
            trends_data = self.trend_service.analyze_trends(request.keywords)

            # 5. Rule-Based Aggregation
            return self._build_strategy_payload(
                request=request,
                website_data=website_data,
                competitor_data=comp_list,
                comp_summary=comp_summary,
                industry_data=industry_data,
                ranked_keywords_data=ranked_keywords_data,
                trends_data=trends_data,
            )

        except Exception as exc:
            logger.exception("Failed to generate marketing strategy.")
            raise StrategyServiceError("Unable to synthesize strategy from sub-services.") from exc

    def _build_strategy_payload(
        self,
        request: StrategyRequest,
        website_data: dict[str, Any],
        competitor_data: list[dict[str, Any]],
        comp_summary: dict[str, Any],
        industry_data: dict[str, Any],
        ranked_keywords_data: list[dict[str, Any]],
        trends_data: dict[str, Any],
    ) -> StrategyResponse:
        """Synthesize disparate intelligence signals into a final structured object."""
        
        # Build Business Summary
        industry_matched = industry_data.get("industry_matched", "Unknown")
        business_summary = f"Your business operates in the {industry_matched} sector. "
        business_summary += f"Based on your profile, you are competing against {len(competitor_data)} main competitors."

        # Build SEO Strategy
        score = website_data.get("seo_score", 0)
        if score < 40:
            seo_strategy = "Critical SEO improvements needed. Focus on H1 tags, meta descriptions, and alt text."
        elif score < 80:
            seo_strategy = "Good baseline SEO. Focus on increasing internal linking and optimizing CTA placement."
        else:
            seo_strategy = "Excellent on-page SEO. Shift focus to off-page backlinks and content velocity."

        # Map Ranked Keywords
        recommended_keywords = [
            RankedKeyword(
                keyword=kw["keyword"],
                opportunity_score=kw["opportunity_score"],
                rank=kw["rank"]
            )
            for kw in ranked_keywords_data
        ]

        # Extract Trends
        rising_trends = trends_data.get("rising_keywords", [])

        # Formulate Recommendations
        recs = []
        dominant_strategy = comp_summary.get("dominant_market_strategy", "")
        if "Product-Led" in dominant_strategy:
            recs.append("The market favors Product-Led Growth. Ensure your website clearly offers a free trial or freemium tier.")
        elif "Sales-Led" in dominant_strategy:
            recs.append("The market is heavily Sales-Led. Optimize your CTAs to 'Book a Demo'.")
            
        industry_channels = industry_data.get("common_channels", [])
        if industry_channels:
            recs.append(f"Invest in proven industry channels: {', '.join(industry_channels[:2])}.")

        # If SEO is bad, add a rec
        if score < 50:
            recs.append("Prioritize technical SEO fixes before scaling paid acquisition.")

        # If no recs were triggered, add a default
        if not recs:
            recs.append("Focus on high-intent inbound marketing and content creation.")

        return StrategyResponse(
            business_summary=business_summary,
            seo_strategy=seo_strategy,
            recommended_keywords=recommended_keywords,
            rising_trends=rising_trends,
            competitor_insights=competitor_data,
            industry_patterns=industry_data.get("patterns", []),
            marketing_recommendations=recs
        )
