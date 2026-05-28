"""Pydantic models for keyword opportunity APIs."""

from __future__ import annotations

from typing import Self

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _StrictBaseModel(BaseModel):
    """Shared production defaults for API schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class KeywordInput(_StrictBaseModel):
    """Keyword metrics required to calculate opportunity score."""

    keyword: str = Field(..., min_length=1, max_length=200)
    search_volume: float = Field(..., ge=0)
    difficulty: float = Field(..., gt=0)
    trend_growth: float = Field(..., ge=0)
    intent_score: float = Field(..., ge=0, le=1)

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        normalized_keyword = " ".join(value.split())
        if not normalized_keyword:
            raise ValueError("keyword cannot be empty")
        return normalized_keyword


class KeywordRequest(_StrictBaseModel):
    """Request payload containing keyword metrics to rank."""

    keywords: list[KeywordInput] = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_keywords(self) -> Self:
        seen_keywords: set[str] = set()
        duplicate_keywords: set[str] = set()

        for keyword_input in self.keywords:
            dedupe_key = keyword_input.keyword.casefold()
            if dedupe_key in seen_keywords:
                duplicate_keywords.add(keyword_input.keyword)
            seen_keywords.add(dedupe_key)

        if duplicate_keywords:
            duplicates = ", ".join(sorted(duplicate_keywords, key=str.casefold))
            raise ValueError(f"keywords must be unique; duplicates found: {duplicates}")

        return self


class RankedKeyword(_StrictBaseModel):
    """Ranked keyword opportunity response item."""

    keyword: str = Field(..., min_length=1, max_length=200)
    opportunity_score: float = Field(..., ge=0)
    rank: int = Field(..., ge=1)

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        normalized_keyword = " ".join(value.split())
        if not normalized_keyword:
            raise ValueError("keyword cannot be empty")
        return normalized_keyword


class KeywordResponse(_StrictBaseModel):
    """Response payload containing ranked keyword opportunities."""

    ranked_keywords: list[RankedKeyword] = Field(..., max_length=500)

    @model_validator(mode="after")
    def validate_rank_order(self) -> Self:
        ranks = [keyword.rank for keyword in self.ranked_keywords]
        if len(ranks) != len(set(ranks)):
            raise ValueError("ranked_keywords cannot contain duplicate ranks")

        expected_ranks = list(range(1, len(ranks) + 1))
        if ranks and ranks != expected_ranks:
            raise ValueError(
                "ranked_keywords must be ordered by contiguous ranks starting at 1"
            )

        return self
