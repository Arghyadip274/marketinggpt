"""Keyword opportunity scoring utilities."""

from __future__ import annotations

import logging
import math
from typing import Any, Iterable, Mapping
from typing_extensions import TypedDict


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class KeywordInput(TypedDict):
    """Required keyword metrics for opportunity scoring."""

    keyword: str
    search_volume: float
    trend_growth: float
    intent_score: float
    difficulty: float


class RankedKeywordOpportunity(KeywordInput):
    """Ranked keyword opportunity payload."""

    opportunity_score: float
    rank: int


class KeywordOpportunityDetector:
    """Detect and rank keyword opportunities from marketing metrics.

    Expected input records contain:
    - ``keyword``: non-empty keyword text
    - ``search_volume``: non-negative demand metric
    - ``trend_growth``: non-negative growth metric
    - ``intent_score``: non-negative commercial or conversion-intent metric
    - ``difficulty``: positive competition metric
    """

    REQUIRED_FIELDS = (
        "keyword",
        "search_volume",
        "trend_growth",
        "intent_score",
        "difficulty",
    )

    SCORE_FIELDS = ("search_volume", "trend_growth", "intent_score", "difficulty")

    def __init__(
        self,
        *,
        min_normalized_difficulty: float = 0.01,
        score_precision: int = 6,
    ) -> None:
        self.min_normalized_difficulty = self._validate_positive_number(
            min_normalized_difficulty,
            field_name="min_normalized_difficulty",
        )
        if not isinstance(score_precision, int) or score_precision < 0:
            raise ValueError("score_precision must be a non-negative integer")
        self.score_precision = score_precision

    def normalize_scores(
        self,
        keywords: Iterable[Mapping[str, Any]],
    ) -> list[KeywordInput]:
        """Normalize numeric keyword metrics to a 0-1 scale.

        Difficulty is bounded by ``min_normalized_difficulty`` to keep the
        opportunity formula from dividing by zero after normalization.
        """

        validated_keywords = self._validate_keywords(keywords)
        if not validated_keywords:
            logger.info("No keywords supplied for normalization")
            return []

        normalized_values: dict[str, list[float]] = {}
        for field_name in self.SCORE_FIELDS:
            values = [keyword[field_name] for keyword in validated_keywords]
            minimum = min(values)
            maximum = max(values)
            normalized_values[field_name] = [
                self._normalize_value(value, minimum=minimum, maximum=maximum)
                for value in values
            ]

        normalized_keywords: list[KeywordInput] = []
        for index, keyword in enumerate(validated_keywords):
            normalized_difficulty = max(
                normalized_values["difficulty"][index],
                self.min_normalized_difficulty,
            )
            normalized_keywords.append(
                {
                    "keyword": keyword["keyword"],
                    "search_volume": normalized_values["search_volume"][index],
                    "trend_growth": normalized_values["trend_growth"][index],
                    "intent_score": normalized_values["intent_score"][index],
                    "difficulty": normalized_difficulty,
                }
            )

        logger.debug("Normalized %d keyword records", len(normalized_keywords))
        return normalized_keywords

    def calculate_opportunity_score(
        self,
        *,
        search_volume: float,
        trend_growth: float,
        intent_score: float,
        difficulty: float,
    ) -> float:
        """Calculate keyword opportunity score.

        Formula:
        ``score = (search_volume * trend_growth * intent_score) / difficulty``
        """

        search_volume = self._validate_non_negative_number(
            search_volume,
            field_name="search_volume",
        )
        trend_growth = self._validate_non_negative_number(
            trend_growth,
            field_name="trend_growth",
        )
        intent_score = self._validate_non_negative_number(
            intent_score,
            field_name="intent_score",
        )
        difficulty = self._validate_positive_number(difficulty, field_name="difficulty")

        score = (search_volume * trend_growth * intent_score) / difficulty
        rounded_score = round(score, self.score_precision)
        logger.debug(
            "Calculated opportunity score %.6f from volume=%s trend=%s intent=%s difficulty=%s",
            rounded_score,
            search_volume,
            trend_growth,
            intent_score,
            difficulty,
        )
        return rounded_score

    def rank_keywords(
        self,
        keywords: Iterable[Mapping[str, Any]],
        *,
        normalize: bool = True,
        limit: int | None = None,
    ) -> list[RankedKeywordOpportunity]:
        """Return keyword opportunities ranked by descending score."""

        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise ValueError("limit must be a positive integer when provided")

        scoring_keywords = (
            self.normalize_scores(keywords)
            if normalize
            else self._validate_keywords(keywords)
        )

        ranked_keywords: list[RankedKeywordOpportunity] = []
        for keyword in scoring_keywords:
            opportunity_score = self.calculate_opportunity_score(
                search_volume=keyword["search_volume"],
                trend_growth=keyword["trend_growth"],
                intent_score=keyword["intent_score"],
                difficulty=keyword["difficulty"],
            )
            ranked_keywords.append(
                {
                    **keyword,
                    "opportunity_score": opportunity_score,
                    "rank": 0,
                }
            )

        ranked_keywords.sort(
            key=lambda keyword: (
                -keyword["opportunity_score"],
                -keyword["search_volume"],
                keyword["difficulty"],
                keyword["keyword"].lower(),
            )
        )

        if limit is not None:
            ranked_keywords = ranked_keywords[:limit]

        for rank, keyword in enumerate(ranked_keywords, start=1):
            keyword["rank"] = rank

        logger.info("Ranked %d keyword opportunities", len(ranked_keywords))
        return ranked_keywords

    def _validate_keywords(
        self,
        keywords: Iterable[Mapping[str, Any]],
    ) -> list[KeywordInput]:
        if keywords is None:
            raise ValueError("keywords must be an iterable of keyword records")

        validated_keywords: list[KeywordInput] = []
        for index, keyword in enumerate(keywords):
            if not isinstance(keyword, Mapping):
                raise TypeError(f"keyword at index {index} must be a mapping")

            missing_fields = [
                field_name
                for field_name in self.REQUIRED_FIELDS
                if field_name not in keyword
            ]
            if missing_fields:
                raise ValueError(
                    f"keyword at index {index} is missing required fields: "
                    f"{', '.join(missing_fields)}"
                )

            keyword_text = self._validate_keyword_text(keyword["keyword"], index=index)
            validated_keywords.append(
                {
                    "keyword": keyword_text,
                    "search_volume": self._validate_non_negative_number(
                        keyword["search_volume"],
                        field_name="search_volume",
                        index=index,
                    ),
                    "trend_growth": self._validate_non_negative_number(
                        keyword["trend_growth"],
                        field_name="trend_growth",
                        index=index,
                    ),
                    "intent_score": self._validate_non_negative_number(
                        keyword["intent_score"],
                        field_name="intent_score",
                        index=index,
                    ),
                    "difficulty": self._validate_positive_number(
                        keyword["difficulty"],
                        field_name="difficulty",
                        index=index,
                    ),
                }
            )

        return validated_keywords

    @staticmethod
    def _validate_keyword_text(value: Any, *, index: int) -> str:
        if not isinstance(value, str):
            raise TypeError(f"keyword at index {index} must be a string")

        keyword_text = value.strip()
        if not keyword_text:
            raise ValueError(f"keyword at index {index} cannot be empty")

        return keyword_text

    @staticmethod
    def _validate_non_negative_number(
        value: Any,
        *,
        field_name: str,
        index: int | None = None,
    ) -> float:
        number = KeywordOpportunityDetector._validate_number(
            value,
            field_name=field_name,
            index=index,
        )
        if number < 0:
            location = f" at index {index}" if index is not None else ""
            raise ValueError(f"{field_name}{location} must be non-negative")
        return number

    @staticmethod
    def _validate_positive_number(
        value: Any,
        *,
        field_name: str,
        index: int | None = None,
    ) -> float:
        number = KeywordOpportunityDetector._validate_number(
            value,
            field_name=field_name,
            index=index,
        )
        if number <= 0:
            location = f" at index {index}" if index is not None else ""
            raise ValueError(f"{field_name}{location} must be greater than zero")
        return number

    @staticmethod
    def _validate_number(
        value: Any,
        *,
        field_name: str,
        index: int | None = None,
    ) -> float:
        location = f" at index {index}" if index is not None else ""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name}{location} must be a finite number")

        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{field_name}{location} must be finite")

        return number

    @staticmethod
    def _normalize_value(value: float, *, minimum: float, maximum: float) -> float:
        if math.isclose(maximum, minimum):
            return 1.0 if value > 0 else 0.0
        return (value - minimum) / (maximum - minimum)
