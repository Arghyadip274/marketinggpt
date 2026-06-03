"""Tests for Master Strategy Orchestration."""

from unittest.mock import patch
from app.services.strategy_service import StrategyService
from app.models.strategy_models import StrategyRequest
from app.models.questionnaire_models import BusinessProfile

def test_strategy_service_generation():
    service = StrategyService()

    profile = BusinessProfile(
        profile_data={
            "What is your business model?": "We are a B2B SaaS platform.",
            "Who is your target audience?": "Enterprise marketers."
        }
    )
    
    request = StrategyRequest(
        business_profile=profile,
        website_url="https://example.com",
        competitors=["https://competitor.com"],
        keywords=["marketing automation", "b2b saas"]
    )

    # We patch the underlying sub-services so we don't do real scraping
    with patch("app.services.website_service.WebsiteService.analyze_website") as mock_website, \
         patch("app.services.competitor_service.CompetitorService.analyze_competitors") as mock_comp, \
         patch("app.services.trend_service.TrendService.analyze_trends") as mock_trend:
         
        mock_website.return_value = {"seo_score": 85, "title": "Example"}
        mock_comp.return_value = {
            "competitors": [{"url": "https://competitor.com"}],
            "market_summary": {"dominant_market_strategy": "Product-Led"}
        }
        mock_trend.return_value = {"rising_keywords": ["marketing automation"]}

        strategy = service.generate_strategy(request)
        
        assert strategy.business_summary is not None
        assert "Saas" in strategy.business_summary
        assert "Product-Led" in strategy.marketing_recommendations[0]
        assert strategy.seo_strategy is not None
