"""Pydantic models for website analysis APIs."""

from __future__ import annotations

from pydantic import Field

from app.models.keyword_models import _StrictBaseModel


class WebsiteAnalysisRequest(_StrictBaseModel):
    """Request payload containing the website URL to analyze."""
    url: str = Field(..., min_length=1, max_length=2000, pattern=r"^https?://")


class WebsiteAnalysisResponse(_StrictBaseModel):
    """Response payload containing website SEO analysis."""
    url: str
    title: str | None
    meta_description: str | None
    h1_count: int = Field(..., ge=0)
    h2_count: int = Field(..., ge=0)
    internal_link_count: int = Field(..., ge=0)
    cta_count: int = Field(..., ge=0)
    image_total_count: int = Field(..., ge=0)
    image_alt_count: int = Field(..., ge=0)
    image_alt_coverage_percent: float = Field(..., ge=0, le=100)
    seo_score: int = Field(..., ge=0, le=100)
