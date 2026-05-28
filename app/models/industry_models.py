"""Pydantic models for industry analysis APIs."""

from __future__ import annotations

from pydantic import Field

from app.models.keyword_models import _StrictBaseModel


class IndustryAnalysisRequest(_StrictBaseModel):
    """Request payload containing the industry name to analyze."""
    industry_name: str = Field(..., min_length=2, max_length=100)


class MessagingBenchmarkModel(_StrictBaseModel):
    """Structured messaging benchmarks for an industry."""
    primary_value_prop: str
    tone: str
    common_objections_addressed: list[str]


class IndustryAnalysisResponse(_StrictBaseModel):
    """Response payload containing structured industry intelligence."""
    industry_matched: str
    is_fallback: bool
    patterns: list[str]
    common_channels: list[str]
    common_offers: list[str]
    messaging_benchmarks: MessagingBenchmarkModel
    positioning_trends: list[str]
