"""Website SEO Analyzer tool for extracting on-page metrics."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any
from typing_extensions import TypedDict

import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SEOAnalysisResult(TypedDict):
    """Structured SEO analysis output."""
    url: str
    title: str | None
    meta_description: str | None
    h1_count: int
    h2_count: int
    internal_link_count: int
    cta_count: int
    image_total_count: int
    image_alt_count: int
    image_alt_coverage_percent: float
    seo_score: int


class WebsiteSEOAnalyzer:
    """Fetches and parses a website to extract basic SEO metrics and compute a score."""

    def __init__(self, request_timeout: int = 10) -> None:
        self.request_timeout = request_timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def analyze(self, url: str) -> SEOAnalysisResult:
        """Main method to fetch, parse, and analyze the website URL."""
        logger.info("Starting SEO analysis for URL: %s", url)

        html = self._fetch_html(url)
        if not html:
            logger.warning("No HTML fetched for URL: %s. Returning empty result.", url)
            return self._empty_result(url)

        metrics = self._parse_html(html, base_url=url)
        score = self._calculate_seo_score(metrics)

        result: SEOAnalysisResult = {
            "url": url,
            "title": metrics.get("title"),
            "meta_description": metrics.get("meta_description"),
            "h1_count": metrics.get("h1_count", 0),
            "h2_count": metrics.get("h2_count", 0),
            "internal_link_count": metrics.get("internal_link_count", 0),
            "cta_count": metrics.get("cta_count", 0),
            "image_total_count": metrics.get("image_total_count", 0),
            "image_alt_count": metrics.get("image_alt_count", 0),
            "image_alt_coverage_percent": metrics.get("image_alt_coverage_percent", 0.0),
            "seo_score": score,
        }

        logger.info("Completed SEO analysis for URL: %s with score: %d", url, score)
        return result

    def _fetch_html(self, url: str) -> str:
        """Fetch the HTML content of the target URL."""
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.request_timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            logger.error("Failed to fetch HTML for %s: %s", url, exc)
            return ""

    def _parse_html(self, html: str, base_url: str) -> dict[str, Any]:
        """Parse HTML to extract SEO elements."""
        soup = BeautifulSoup(html, "lxml")
        metrics: dict[str, Any] = {}

        # 1. Title
        title_tag = soup.find("title")
        metrics["title"] = title_tag.text.strip() if title_tag and title_tag.text else None

        # 2. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc:
            # Fallback for some sites using property="og:description"
            meta_desc = soup.find("meta", attrs={"property": "og:description"})
        
        metrics["meta_description"] = (
            meta_desc.get("content", "").strip() if meta_desc else None
        )

        # 3. H1/H2 Headings
        metrics["h1_count"] = len(soup.find_all("h1"))
        metrics["h2_count"] = len(soup.find_all("h2"))

        # 4. Internal Links
        parsed_base = urllib.parse.urlparse(base_url)
        base_domain = parsed_base.netloc.lower()
        
        internal_links = 0
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link["href"].strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            
            parsed_href = urllib.parse.urlparse(href)
            # It is internal if there is no domain (relative), or domain matches base_domain
            if not parsed_href.netloc or parsed_href.netloc.lower() == base_domain:
                internal_links += 1

        metrics["internal_link_count"] = internal_links

        # 5. CTA Buttons/Text
        cta_keywords = {"buy", "sign up", "get started", "contact", "subscribe", "download", "register", "join"}
        cta_count = 0
        
        # Check standard buttons
        buttons = soup.find_all("button")
        cta_count += len(buttons)
        
        # Check links that act like CTAs based on text or classes
        for link in all_links:
            text = link.get_text(strip=True).lower()
            classes = link.get("class", [])
            class_str = " ".join(classes).lower()
            
            # If text matches cta keywords or has btn classes
            if any(kw in text for kw in cta_keywords) or "btn" in class_str or "button" in class_str:
                cta_count += 1

        metrics["cta_count"] = cta_count

        # 6. Image Alt Coverage
        images = soup.find_all("img")
        metrics["image_total_count"] = len(images)
        
        alt_count = 0
        for img in images:
            alt = img.get("alt")
            # Consider it covered if alt exists (even if empty, as empty is valid for decorative images)
            if alt is not None:
                alt_count += 1
                
        metrics["image_alt_count"] = alt_count
        metrics["image_alt_coverage_percent"] = (
            round((alt_count / len(images)) * 100, 2) if images else 100.0
        )

        return metrics

    def _calculate_seo_score(self, metrics: dict[str, Any]) -> int:
        """Compute basic SEO score (0-100)."""
        score = 0

        # Title (+20)
        if metrics.get("title"):
            score += 20
            
        # Meta Description (+20)
        if metrics.get("meta_description"):
            score += 20
            
        # H1 (+20)
        if metrics.get("h1_count", 0) > 0:
            score += 20
            
        # Image Alt Coverage >= 80% (+20)
        if metrics.get("image_alt_coverage_percent", 0.0) >= 80.0:
            score += 20
            
        # Has Internal Links & CTAs (+20)
        if metrics.get("internal_link_count", 0) > 0 and metrics.get("cta_count", 0) > 0:
            score += 20

        return score

    def _empty_result(self, url: str) -> SEOAnalysisResult:
        """Return an empty result dict when fetch fails."""
        return {
            "url": url,
            "title": None,
            "meta_description": None,
            "h1_count": 0,
            "h2_count": 0,
            "internal_link_count": 0,
            "cta_count": 0,
            "image_total_count": 0,
            "image_alt_count": 0,
            "image_alt_coverage_percent": 0.0,
            "seo_score": 0,
        }
