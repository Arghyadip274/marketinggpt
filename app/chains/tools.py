"""LangChain tool wrappers for MarketingGPT domain services."""

import logging
from typing import Any

from langchain_core.tools import tool

# Import Services
from app.services.strategy_service import StrategyService
from app.services.keyword_service import KeywordService
from app.services.trend_service import TrendService
from app.services.website_service import WebsiteService
from app.services.competitor_service import CompetitorService
from app.services.industry_service import IndustryService
from app.services.questionnaire_service import QuestionnaireService

# Import Models for structured input validation
from app.models.strategy_models import StrategyRequest
from app.models.questionnaire_models import BusinessProfile, QuestionnaireSubmission, AnswerModel


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---------------------------------------------------------------------------
# Global Service Singletons (lazy loaded inside functions or defined here to 
# avoid re-instantiating heavy NLP logic during agent loops)
# ---------------------------------------------------------------------------
_strategy_service = StrategyService()
_keyword_service = KeywordService()
_trend_service = TrendService()
_website_service = WebsiteService()
_competitor_service = CompetitorService()
_industry_service = IndustryService()
_questionnaire_service = QuestionnaireService()


@tool
def analyze_website_tool(url: str) -> dict[str, Any]:
    """Analyze a single website URL to extract SEO metrics and an overall score.
    
    Args:
        url: The absolute HTTP/HTTPS URL of the target website to scrape.
        
    Returns:
        A dictionary containing technical SEO insights, header counts, image metrics,
        and an aggregated `seo_score`.
    """
    logger.info("LangChain Tool executing website analysis for: %s", url)
    return _website_service.analyze_website(url)


@tool
def analyze_competitors_tool(urls: list[str]) -> dict[str, Any]:
    """Analyze a list of competitor websites to extract positioning and CTA strategies.
    
    Args:
        urls: A list of competitor website URLs (e.g. ['https://example.com']).
        
    Returns:
        A dictionary containing deep messaging breakdowns per competitor,
        along with an aggregated market summary determining if the landscape
        is Sales-Led or Product-Led.
    """
    logger.info("LangChain Tool executing competitor analysis for %d URLs.", len(urls))
    return _competitor_service.analyze_competitors(urls)


@tool
def analyze_industry_tool(industry_name: str) -> dict[str, Any]:
    """Fetch generic marketing intelligence patterns for a specific industry.
    
    Args:
        industry_name: The target industry vertical (e.g., 'saas', 'ecommerce').
        
    Returns:
        A dictionary detailing standard channels, common offers, messaging
        benchmarks, and positioning trends.
    """
    logger.info("LangChain Tool executing industry analysis for: %s", industry_name)
    return _industry_service.analyze_industry(industry_name)


@tool
def analyze_keywords_tool(keywords_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank a list of target keywords by their opportunity score.
    
    Args:
        keywords_data: A list of keyword dictionaries containing:
            'keyword' (str), 'search_volume' (float), 'difficulty' (float), 
            'cpc' (float), 'trend_growth' (float), 'intent_score' (float).
            
    Returns:
        A list of dictionaries representing ranked keywords ordered by opportunity.
    """
    logger.info("LangChain Tool executing keyword analysis.")
    return _keyword_service.analyze_keywords(keywords_data)


@tool
def analyze_trends_tool(keywords: list[str]) -> dict[str, Any]:
    """Analyze Google Trends velocity for a list of target keywords.
    
    Args:
        keywords: A list of keywords to check for rising popularity.
        
    Returns:
        A dictionary featuring 'trend_scores' and a 'rising_keywords' list.
    """
    logger.info("LangChain Tool executing trend analysis.")
    return _trend_service.analyze_trends(keywords)


@tool
def generate_master_strategy_tool(
    business_profile_data: dict[str, str],
    website_url: str,
    competitor_urls: list[str],
    keywords: list[str]
) -> dict[str, Any]:
    """Synthesize a complete Marketing Strategy using all downstream analyzers.
    
    Args:
        business_profile_data: A key-value dictionary representing the business profile answers.
        website_url: The primary URL of the business.
        competitor_urls: A list of target competitor URLs.
        keywords: A list of relevant keywords to analyze.
        
    Returns:
        A comprehensive JSON-serializable dictionary containing actionable
        SEO strategies, ranked keywords, industry patterns, and marketing recommendations.
    """
    logger.info("LangChain Tool generating master strategy for: %s", website_url)
    profile = BusinessProfile(profile_data=business_profile_data)
    request = StrategyRequest(
        business_profile=profile,
        website_url=website_url,
        competitors=competitor_urls,
        keywords=keywords
    )
    
    response = _strategy_service.generate_strategy(request)
    return response.model_dump()


@tool
def process_questionnaire_tool(answers: list[dict[str, str]]) -> dict[str, Any]:
    """Process dynamic onboarding questionnaire answers into a structured profile.
    
    Args:
        answers: A list of dictionaries, each containing 'question' and 'answer'.
        
    Returns:
        A structured BusinessProfile dictionary formatted as {"profile_data": {...}}.
    """
    logger.info("LangChain Tool processing questionnaire answers.")
    
    # Cast to Pydantic models to leverage strict validation inside the service
    answer_models = [AnswerModel(**ans) for ans in answers]
    submission = QuestionnaireSubmission(answers=answer_models)
    
    profile = _questionnaire_service.build_business_profile(submission)
    return profile.model_dump()
