"""Pydantic models for the strategy orchestration engine."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, HttpUrl

from app.models.questionnaire_models import BusinessProfile
from app.models.keyword_models import RankedKeyword


class StrategyRequest(BaseModel):
    """Input payload for generating a full marketing strategy."""
    business_profile: BusinessProfile
    website_url: str
    competitors: list[str]
    keywords: list[str]


class StrategyResponse(BaseModel):
    """Structured marketing intelligence output."""
    business_summary: str
    seo_strategy: str
    recommended_keywords: list[RankedKeyword]
    rising_trends: list[str]
    competitor_insights: list[dict[str, Any]]
    industry_patterns: list[str]
    marketing_recommendations: list[str]
