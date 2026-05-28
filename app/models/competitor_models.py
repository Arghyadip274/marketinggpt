"""Pydantic models for competitor analysis APIs."""

from __future__ import annotations

from typing import Any
# pyrefly: ignore [missing-import]
from pydantic import Field

from app.models.keyword_models import _StrictBaseModel


class CompetitorAnalysisRequest(_StrictBaseModel):
    """Request payload containing competitor URLs to analyze."""
    competitor_urls: list[str] = Field(..., min_length=1, max_length=10)


class CompetitorMessaging(_StrictBaseModel):
    """Positioning messaging of a competitor."""
    title: str | None
    meta_description: str | None
    h1_primary: str | None
    h1_all: list[str]
    h2_top: list[str]


class CompetitorDataModel(_StrictBaseModel):
    """Structured data for a single competitor."""
    url: str
    messaging: CompetitorMessaging
    offers: list[str]
    ctas: list[str]
    inferred_strategy: str


class MarketSummaryModel(_StrictBaseModel):
    """Top-level market summary across competitors."""
    competitors_analyzed: int
    dominant_market_strategy: str | None = None
    common_ctas: dict[str, int] = Field(default_factory=dict)
    status: str | None = None


class CompetitorAnalysisResponse(_StrictBaseModel):
    """Response payload containing structured competitor intelligence."""
    competitors: list[CompetitorDataModel]
    market_summary: MarketSummaryModel
