"""Pydantic models for trend analysis APIs."""

from __future__ import annotations

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _StrictBaseModel(BaseModel):
    """Shared production defaults for API schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TrendRequest(_StrictBaseModel):
    """Request payload for keyword trend analysis."""

    keywords: list[str] = Field(..., min_length=1, max_length=500)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, values: list[str]) -> list[str]:
        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()
        duplicate_keywords: set[str] = set()

        for value in values:
            normalized_keyword = cls._normalize_keyword(value)
            dedupe_key = normalized_keyword.casefold()
            if dedupe_key in seen_keywords:
                duplicate_keywords.add(normalized_keyword)
            seen_keywords.add(dedupe_key)
            normalized_keywords.append(normalized_keyword)

        if duplicate_keywords:
            duplicates = ", ".join(sorted(duplicate_keywords, key=str.casefold))
            raise ValueError(f"keywords must be unique; duplicates found: {duplicates}")

        return normalized_keywords

    @staticmethod
    def _normalize_keyword(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("each keyword must be a string")

        normalized_keyword = " ".join(value.split())
        if not normalized_keyword:
            raise ValueError("keywords cannot contain empty values")
        if len(normalized_keyword) > 200:
            raise ValueError("keywords cannot exceed 200 characters")

        return normalized_keyword


class TrendComparison(_StrictBaseModel):
    """Comparison row for a keyword trend result."""

    keyword: str = Field(..., min_length=1, max_length=200)
    trend_score: float = Field(..., ge=0)
    growth_rate: float
    rank: int = Field(..., ge=1)

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        normalized_keyword = " ".join(value.split())
        if not normalized_keyword:
            raise ValueError("keyword cannot be empty")
        return normalized_keyword

    @field_validator("trend_score", "growth_rate")
    @classmethod
    def validate_finite_metric(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("trend metrics must be finite")
        return value


class TrendResponse(_StrictBaseModel):
    """Response payload for keyword trend analysis."""

    trend_scores: dict[str, float] = Field(..., max_length=500)
    rising_keywords: list[str] = Field(default_factory=list, max_length=500)
    comparison: list[TrendComparison] = Field(..., max_length=500)

    @field_validator("trend_scores")
    @classmethod
    def validate_trend_scores(cls, values: dict[str, float]) -> dict[str, float]:
        normalized_scores: dict[str, float] = {}
        for keyword, score in values.items():
            normalized_keyword = cls._normalize_keyword(keyword)
            if normalized_keyword.casefold() in {
                existing_keyword.casefold() for existing_keyword in normalized_scores
            }:
                raise ValueError("trend_scores cannot contain duplicate keywords")

            if not math.isfinite(score):
                raise ValueError("trend_scores values must be finite")
            if score < 0:
                raise ValueError("trend_scores values must be non-negative")

            normalized_scores[normalized_keyword] = score

        return normalized_scores

    @field_validator("rising_keywords")
    @classmethod
    def validate_rising_keywords(cls, values: list[str]) -> list[str]:
        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()

        for value in values:
            normalized_keyword = cls._normalize_keyword(value)
            dedupe_key = normalized_keyword.casefold()
            if dedupe_key in seen_keywords:
                raise ValueError("rising_keywords cannot contain duplicates")
            seen_keywords.add(dedupe_key)
            normalized_keywords.append(normalized_keyword)

        return normalized_keywords

    @model_validator(mode="after")
    def validate_response_consistency(self) -> Self:
        ranks = [row.rank for row in self.comparison]
        if len(ranks) != len(set(ranks)):
            raise ValueError("comparison cannot contain duplicate ranks")

        expected_ranks = list(range(1, len(ranks) + 1))
        if ranks and ranks != expected_ranks:
            raise ValueError("comparison must be ordered by contiguous ranks starting at 1")

        trend_score_keys = {keyword.casefold() for keyword in self.trend_scores}
        comparison_keys = {row.keyword.casefold() for row in self.comparison}
        rising_keys = {keyword.casefold() for keyword in self.rising_keywords}

        if len(comparison_keys) != len(self.comparison):
            raise ValueError("comparison cannot contain duplicate keywords")
        if comparison_keys and comparison_keys != trend_score_keys:
            raise ValueError("comparison keywords must match trend_scores keys")
        if not rising_keys.issubset(trend_score_keys):
            raise ValueError("rising_keywords must be present in trend_scores")

        for row in self.comparison:
            score = self._get_score_for_keyword(row.keyword)
            if not math.isclose(row.trend_score, score, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(
                    f"comparison trend_score for {row.keyword!r} must match trend_scores"
                )

        return self

    def _get_score_for_keyword(self, keyword: str) -> float:
        for score_keyword, score in self.trend_scores.items():
            if score_keyword.casefold() == keyword.casefold():
                return score
        raise ValueError(f"missing trend score for keyword {keyword!r}")

    @staticmethod
    def _normalize_keyword(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("keyword values must be strings")

        normalized_keyword = " ".join(value.split())
        if not normalized_keyword:
            raise ValueError("keyword values cannot be empty")
        if len(normalized_keyword) > 200:
            raise ValueError("keyword values cannot exceed 200 characters")

        return normalized_keyword
