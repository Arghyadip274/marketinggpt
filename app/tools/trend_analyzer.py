"""Google Trends analysis utilities for keyword research."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol,  cast
from typing_extensions import TypedDict
from urllib.parse import quote

try:
    import requests
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    requests = None  # type: ignore[assignment]

try:
    from pytrends.request import TrendReq
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    TrendReq = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TrendAnalyzerError(RuntimeError):
    """Raised when trend data cannot be fetched or parsed."""


class TrendComparison(TypedDict):
    """Comparison row for a keyword."""

    keyword: str
    trend_score: float
    growth_rate: float
    rank: int


class TrendAnalysisResult(TypedDict):
    """Trend analysis response payload."""

    trend_scores: dict[str, float]
    rising_keywords: list[str]
    comparison: list[TrendComparison]


class TrendPoint(TypedDict):
    """Single trend time-series point."""

    timestamp: str
    value: float


class TrendSeries(TypedDict):
    """Keyword trend time series."""

    keyword: str
    points: list[TrendPoint]


class HTTPSession(Protocol):
    """Minimal protocol implemented by requests.Session."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        timeout: float | tuple[float, float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Send a GET request."""


@dataclass(frozen=True)
class _TrendMetrics:
    trend_score: float
    growth_rate: float


class TrendAnalyzer:
    """Fetch, compare, and detect rising Google Trends keywords."""

    GOOGLE_TRENDS_EXPLORE_URL = "https://trends.google.com/trends/api/explore"
    GOOGLE_TRENDS_MULTILINE_URL = (
        "https://trends.google.com/trends/api/widgetdata/multiline"
    )
    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
    }

    def __init__(
        self,
        *,
        hl: str = "en-US",
        tz: int = 330,
        timeframe: str = "today 12-m",
        geo: str = "",
        category: int = 0,
        timeout: float = 10.0,
        max_keywords_per_request: int = 5,
        rising_threshold: float = 20.0,
        use_pytrends: bool = True,
        session: HTTPSession | None = None,
        pytrends_client: Any | None = None,
    ) -> None:
        self.hl = self._validate_non_empty_string(hl, field_name="hl")
        self.tz = self._validate_int(tz, field_name="tz")
        self.timeframe = self._validate_non_empty_string(
            timeframe,
            field_name="timeframe",
        )
        self.geo = self._validate_string(geo, field_name="geo")
        self.category = self._validate_int(category, field_name="category")
        self.timeout = self._validate_positive_number(timeout, field_name="timeout")
        self.max_keywords_per_request = self._validate_max_keywords(
            max_keywords_per_request
        )
        self.rising_threshold = self._validate_number(
            rising_threshold,
            field_name="rising_threshold",
        )
        self.use_pytrends = use_pytrends
        self._pytrends_client = pytrends_client
        self._session = session or self._build_session()

    def fetch_google_trends(self, keywords: Iterable[str]) -> TrendAnalysisResult:
        """Fetch Google Trends data and return scores, rising terms, and ranking."""

        validated_keywords = self._validate_keywords(keywords)
        logger.info("Fetching Google Trends data for %d keywords", len(validated_keywords))

        try:
            series_by_keyword = self._fetch_trend_series(validated_keywords)
        except Exception as exc:
            logger.exception("Failed to fetch Google Trends data")
            raise TrendAnalyzerError("Unable to fetch Google Trends data") from exc

        trend_scores = {
            keyword: self._calculate_metrics(points).trend_score
            for keyword, points in series_by_keyword.items()
        }
        rising_keywords = self.detect_rising_trends(series_by_keyword)
        comparison = self.compare_keywords(series_by_keyword)

        return {
            "trend_scores": trend_scores,
            "rising_keywords": rising_keywords,
            "comparison": comparison,
        }

    def compare_keywords(
        self,
        trend_data: Mapping[str, Iterable[float | Mapping[str, Any]]] | Iterable[str],
    ) -> list[TrendComparison]:
        """Compare keywords by trend score, growth rate, and rank."""

        series_by_keyword = self._coerce_trend_data(trend_data)
        comparison: list[TrendComparison] = []
        for keyword, points in series_by_keyword.items():
            metrics = self._calculate_metrics(points)
            comparison.append(
                {
                    "keyword": keyword,
                    "trend_score": metrics.trend_score,
                    "growth_rate": metrics.growth_rate,
                    "rank": 0,
                }
            )

        comparison.sort(
            key=lambda row: (
                -row["trend_score"],
                -row["growth_rate"],
                row["keyword"].lower(),
            )
        )

        for rank, row in enumerate(comparison, start=1):
            row["rank"] = rank

        logger.debug("Compared %d keywords", len(comparison))
        return comparison

    def detect_rising_trends(
        self,
        trend_data: Mapping[str, Iterable[float | Mapping[str, Any]]] | Iterable[str],
        *,
        threshold: float | None = None,
    ) -> list[str]:
        """Return keywords whose recent trend growth meets the threshold."""

        growth_threshold = (
            self.rising_threshold
            if threshold is None
            else self._validate_number(threshold, field_name="threshold")
        )
        series_by_keyword = self._coerce_trend_data(trend_data)

        rising_keywords = [
            keyword
            for keyword, points in series_by_keyword.items()
            if self._calculate_metrics(points).growth_rate >= growth_threshold
        ]
        rising_keywords.sort(
            key=lambda keyword: (
                -self._calculate_metrics(series_by_keyword[keyword]).growth_rate,
                keyword.lower(),
            )
        )

        logger.info(
            "Detected %d rising keywords using threshold %.2f",
            len(rising_keywords),
            growth_threshold,
        )
        return rising_keywords

    def _fetch_trend_series(self, keywords: list[str]) -> dict[str, list[float]]:
        if not self.use_pytrends:
            return self._generate_mock_trends(keywords)

        if TrendReq is None:
            logger.warning("pytrends unavailable, using mock trend data")
            return self._generate_mock_trends(keywords)

        try:
            return self._fetch_with_pytrends(keywords)

        except Exception as exc:
            logger.warning(
                "Google Trends unavailable (%s). Falling back to mock trend data.",
                str(exc),
            )
            return self._generate_mock_trends(keywords)

    def _fetch_with_pytrends(self, keywords: list[str]) -> dict[str, list[float]]:
        client = self._pytrends_client or TrendReq(hl=self.hl, tz=self.tz)
        series_by_keyword: dict[str, list[float]] = {keyword: [] for keyword in keywords}

        for keyword_batch in self._chunk_keywords(keywords):
            client.build_payload(
                keyword_batch,
                cat=self.category,
                timeframe=self.timeframe,
                geo=self.geo,
                gprop="",
            )
            interest = client.interest_over_time()
            if interest is None or getattr(interest, "empty", False):
                logger.warning("pytrends returned no data for batch: %s", keyword_batch)
                continue

            for keyword in keyword_batch:
                if keyword not in interest:
                    logger.warning("Missing pytrends column for keyword: %s", keyword)
                    continue
                series_by_keyword[keyword].extend(
                    self._coerce_number(value, field_name=keyword)
                    for value in interest[keyword].tolist()
                )

        return series_by_keyword

    def _fetch_with_requests(self, keywords: list[str]) -> dict[str, list[float]]:
        if requests is None:
            raise TrendAnalyzerError(
                "Install pytrends or requests to fetch Google Trends data"
            )
        if self._session is None:
            raise TrendAnalyzerError("A requests-compatible session is required")

        series_by_keyword: dict[str, list[float]] = {keyword: [] for keyword in keywords}
        for keyword_batch in self._chunk_keywords(keywords):
            explore_payload = self._build_explore_payload(keyword_batch)
            explore_response = self._session.get(
                self.GOOGLE_TRENDS_EXPLORE_URL,
                params={
                    "hl": self.hl,
                    "tz": self.tz,
                    "req": json.dumps(explore_payload, separators=(",", ":")),
                },
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS,
            )
            explore_response.raise_for_status()
            explore_data = self._decode_google_json(explore_response.text)
            widget = self._find_time_series_widget(explore_data)

            multiline_response = self._session.get(
                self.GOOGLE_TRENDS_MULTILINE_URL,
                params={
                    "hl": self.hl,
                    "tz": self.tz,
                    "req": json.dumps(widget["request"], separators=(",", ":")),
                    "token": widget["token"],
                },
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS,
            )
            multiline_response.raise_for_status()
            timeline_data = self._decode_google_json(multiline_response.text)
            self._merge_timeline_data(series_by_keyword, keyword_batch, timeline_data)

        return series_by_keyword

    def _build_session(self) -> HTTPSession | None:
        if requests is None:
            return None
        session = requests.Session()
        session.headers.update(self.DEFAULT_HEADERS)
        return cast(HTTPSession, session)

    def _build_explore_payload(self, keywords: list[str]) -> dict[str, Any]:
        return {
            "comparisonItem": [
                {
                    "keyword": keyword,
                    "geo": self.geo,
                    "time": self.timeframe,
                }
                for keyword in keywords
            ],
            "category": self.category,
            "property": "",
        }

    @staticmethod
    def _decode_google_json(response_text: str) -> dict[str, Any]:
        json_start = response_text.find("{")
        if json_start < 0:
            raise TrendAnalyzerError("Google Trends response did not contain JSON")

        try:
            decoded = json.loads(response_text[json_start:])
        except json.JSONDecodeError as exc:
            raise TrendAnalyzerError("Failed to decode Google Trends response") from exc

        if not isinstance(decoded, dict):
            raise TrendAnalyzerError("Google Trends response was not an object")
        return decoded

    @staticmethod
    def _find_time_series_widget(explore_data: Mapping[str, Any]) -> Mapping[str, Any]:
        widgets = explore_data.get("widgets", [])
        if not isinstance(widgets, list):
            raise TrendAnalyzerError("Google Trends response has invalid widgets")

        for widget in widgets:
            if not isinstance(widget, Mapping):
                continue
            if widget.get("id") == "TIMESERIES" and widget.get("token"):
                request = widget.get("request")
                if not isinstance(request, Mapping):
                    raise TrendAnalyzerError("Timeseries widget has invalid request")
                return widget

        raise TrendAnalyzerError("Google Trends timeseries widget was not found")

    def _merge_timeline_data(
        self,
        series_by_keyword: dict[str, list[float]],
        keywords: list[str],
        timeline_data: Mapping[str, Any],
    ) -> None:
        timeline = timeline_data.get("default", {}).get("timelineData", [])
        if not isinstance(timeline, list):
            raise TrendAnalyzerError("Google Trends timeline data is invalid")

        for point in timeline:
            if not isinstance(point, Mapping):
                continue
            raw_values = point.get("value", [])
            if not isinstance(raw_values, list):
                continue
            for index, keyword in enumerate(keywords):
                if index >= len(raw_values):
                    continue
                series_by_keyword[keyword].append(
                    self._coerce_number(raw_values[index], field_name=keyword)
                )

    def _coerce_trend_data(
        self,
        trend_data: Mapping[str, Iterable[float | Mapping[str, Any]]] | Iterable[str],
    ) -> dict[str, list[float]]:
        if isinstance(trend_data, Mapping):
            series_by_keyword: dict[str, list[float]] = {}
            for raw_keyword, raw_points in trend_data.items():
                keyword = self._validate_non_empty_string(
                    raw_keyword,
                    field_name="keyword",
                )
                points = [
                    self._coerce_trend_point(point, keyword=keyword)
                    for point in raw_points
                ]
                series_by_keyword[keyword] = points
            return series_by_keyword

        keywords = self._validate_keywords(trend_data)
        return self._fetch_trend_series(keywords)

    def _calculate_metrics(self, points: Iterable[float]) -> _TrendMetrics:
        values = []
        for point in points:
            value = self._coerce_number(point, field_name="trend point")
            if value >= 0:
                values.append(value)
        if not values:
            return _TrendMetrics(trend_score=0.0, growth_rate=0.0)

        trend_score = round(sum(values) / len(values), 2)
        midpoint = max(len(values) // 2, 1)
        early_average = sum(values[:midpoint]) / midpoint
        recent_values = values[midpoint:] or values[-midpoint:]
        recent_average = sum(recent_values) / len(recent_values)

        if math.isclose(early_average, 0.0):
            growth_rate = 100.0 if recent_average > 0 else 0.0
        else:
            growth_rate = ((recent_average - early_average) / early_average) * 100

        return _TrendMetrics(
            trend_score=trend_score,
            growth_rate=round(growth_rate, 2),
        )

    def _chunk_keywords(self, keywords: list[str]) -> Iterable[list[str]]:
        for start in range(0, len(keywords), self.max_keywords_per_request):
            yield keywords[start : start + self.max_keywords_per_request]

    def _validate_keywords(self, keywords: Iterable[str]) -> list[str]:
        if keywords is None:
            raise ValueError("keywords must be an iterable of strings")
        if isinstance(keywords, str):
            raise TypeError("keywords must be an iterable of strings, not a string")

        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()
        for index, keyword in enumerate(keywords):
            normalized_keyword = self._validate_non_empty_string(
                keyword,
                field_name=f"keyword at index {index}",
            )
            dedupe_key = normalized_keyword.casefold()
            if dedupe_key in seen_keywords:
                logger.debug("Skipping duplicate keyword: %s", normalized_keyword)
                continue
            seen_keywords.add(dedupe_key)
            normalized_keywords.append(normalized_keyword)

        if not normalized_keywords:
            raise ValueError("keywords must include at least one keyword")
        return normalized_keywords
    def _generate_mock_trends(self, keywords: list[str]) -> dict[str, list[float]]:
        """
        Fallback trend data generator for demo/testing when Google Trends blocks requests.
        """
        mock_data = {}

        for idx, keyword in enumerate(keywords):
            base = 20 + (idx * 10)

            mock_data[keyword] = [
                base,
                base + 5,
                base + 10,
                base + 15,
                base + 20,
            ]

        return mock_data
    @staticmethod
    def _validate_string(value: Any, *, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        return value.strip()

    @classmethod
    def _validate_non_empty_string(cls, value: Any, *, field_name: str) -> str:
        stripped_value = cls._validate_string(value, field_name=field_name)
        if not stripped_value:
            raise ValueError(f"{field_name} cannot be empty")
        return stripped_value

    @staticmethod
    def _validate_int(value: Any, *, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        return value

    @classmethod
    def _validate_positive_number(cls, value: Any, *, field_name: str) -> float:
        number = cls._validate_number(value, field_name=field_name)
        if number <= 0:
            raise ValueError(f"{field_name} must be greater than zero")
        return number

    @classmethod
    def _validate_max_keywords(cls, value: Any) -> int:
        max_keywords = cls._validate_int(value, field_name="max_keywords_per_request")
        if max_keywords <= 0:
            raise ValueError("max_keywords_per_request must be greater than zero")
        if max_keywords > 5:
            raise ValueError("Google Trends supports at most 5 keywords per request")
        return max_keywords

    @staticmethod
    def _validate_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be a finite number")

        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{field_name} must be finite")
        return number

    @classmethod
    def _coerce_number(cls, value: Any, *, field_name: str) -> float:
        if isinstance(value, str):
            value = value.replace("<", "").replace("+", "").strip()
            if value == "":
                value = 0
        return cls._validate_number(value, field_name=field_name)

    @classmethod
    def _coerce_trend_point(cls, point: float | Mapping[str, Any], *, keyword: str) -> float:
        if isinstance(point, Mapping):
            for key in ("value", keyword, "trend_score"):
                if key in point:
                    return cls._coerce_number(point[key], field_name=keyword)
            raise ValueError(f"trend point for {keyword} is missing a value")

        return cls._coerce_number(point, field_name=keyword)

    @staticmethod
    def build_explore_url(keyword: str) -> str:
        """Build a human-readable Google Trends URL for a single keyword."""

        keyword = TrendAnalyzer._validate_non_empty_string(
            keyword,
            field_name="keyword",
        )
        return f"https://trends.google.com/trends/explore?q={quote(keyword)}"
