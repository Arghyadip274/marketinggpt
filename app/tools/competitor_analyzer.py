"""Competitor Intelligence Analyzer tool."""

from __future__ import annotations

import logging
import re
from typing import Any
from typing_extensions import TypedDict

from bs4 import BeautifulSoup
from app.tools.website_analyzer import WebsiteSEOAnalyzer

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CompetitorData(TypedDict):
    """Structured data for a single competitor."""
    url: str
    messaging: dict[str, Any]
    offers: list[str]
    ctas: list[str]
    inferred_strategy: str


class CompetitorIntelligenceReport(TypedDict):
    """Structured aggregate intelligence report."""
    competitors: list[CompetitorData]
    market_summary: dict[str, Any]


class CompetitorIntelligenceAnalyzer:
    """Analyzes competitor websites for messaging, offers, and strategy."""

    def __init__(self, request_timeout: int = 15) -> None:
        self.request_timeout = request_timeout
        # We reuse the fetching capability of WebsiteSEOAnalyzer
        self.fetcher = WebsiteSEOAnalyzer(request_timeout=self.request_timeout)

        self.offer_keywords = {
            "free trial", "discount", "off", "pricing", "subscribe", 
            "demo", "save", "guarantee", "month", "year", "cancel", "starts at"
        }
        
        self.cta_keywords = {
            "buy", "sign up", "get started", "contact", "subscribe", 
            "download", "register", "join", "book", "demo", "try"
        }

    def analyze_competitors(self, urls: list[str]) -> CompetitorIntelligenceReport:
        """Analyze a list of competitor URLs and build a comparative report."""
        logger.info("Starting competitor analysis for %d URLs", len(urls))
        
        competitors_data: list[CompetitorData] = []
        
        for url in urls:
            data = self._analyze_single_competitor(url)
            if data:
                competitors_data.append(data)
                
        market_summary = self._generate_market_summary(competitors_data)
        
        report: CompetitorIntelligenceReport = {
            "competitors": competitors_data,
            "market_summary": market_summary,
        }
        
        logger.info("Successfully generated competitor intelligence report.")
        return report

    def _analyze_single_competitor(self, url: str) -> CompetitorData | None:
        """Fetch and extract intelligence from a single competitor."""
        logger.debug("Analyzing competitor: %s", url)
        
        # Access the private method of the SEO analyzer since it's an internal tool reuse
        # In a strict OOP setup, we might extract this to a base class, but this is pragmatic.
        html = self.fetcher._fetch_html(url)
        if not html:
            logger.warning("Failed to fetch HTML for %s, skipping.", url)
            return None

        soup = BeautifulSoup(html, "lxml")
        
        messaging = self._extract_messaging(soup)
        offers = self._extract_offers(soup)
        ctas = self._extract_ctas(soup)
        strategy = self._infer_strategy(messaging, offers, ctas)
        
        return {
            "url": url,
            "messaging": messaging,
            "offers": offers,
            "ctas": ctas,
            "inferred_strategy": strategy,
        }

    def _extract_messaging(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract primary positioning messaging (Title, Meta, H1s, H2s)."""
        messaging: dict[str, Any] = {}
        
        # Title
        title_tag = soup.find("title")
        messaging["title"] = title_tag.text.strip() if title_tag and title_tag.text else None
        
        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc:
            meta_desc = soup.find("meta", attrs={"property": "og:description"})
        messaging["meta_description"] = meta_desc.get("content", "").strip() if meta_desc else None
        
        # Headings (limit to top 3 for brevity)
        h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
        messaging["h1_primary"] = h1_tags[0] if h1_tags else None
        messaging["h1_all"] = h1_tags[:3]
        
        h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]
        messaging["h2_top"] = h2_tags[:5]
        
        return messaging

    def _extract_offers(self, soup: BeautifulSoup) -> list[str]:
        """Scan text for pricing/offer patterns and extract surrounding context."""
        offers: set[str] = set()
        
        # Look at paragraphs and list items
        text_elements = soup.find_all(["p", "li", "h3", "div"])
        
        for element in text_elements:
            text = element.get_text(strip=True)
            # Skip massive blocks of text
            if len(text) > 150 or len(text) < 5:
                continue
                
            text_lower = text.lower()
            
            # Check for dollar amounts using regex e.g., $19, $99.99
            if re.search(r"\$\d+", text_lower):
                offers.add(text)
                continue
                
            # Check for offer keywords
            if any(kw in text_lower for kw in self.offer_keywords):
                # Filter out generic navigation links that happen to use these words
                if len(text.split()) > 2:
                    offers.add(text)
                    
            if len(offers) >= 10:  # Cap the number of extracted offers
                break
                
        return list(offers)

    def _extract_ctas(self, soup: BeautifulSoup) -> list[str]:
        """Extract the actual text of Call to Action buttons/links."""
        ctas: set[str] = set()
        
        # 1. Standard buttons
        for button in soup.find_all("button"):
            text = button.get_text(strip=True)
            if text and len(text) < 30:
                ctas.add(text)
                
        # 2. Links that look like CTAs
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            if not text or len(text) > 30:
                continue
                
            text_lower = text.lower()
            classes = link.get("class", [])
            class_str = " ".join(classes).lower()
            
            if any(kw in text_lower for kw in self.cta_keywords) or "btn" in class_str or "button" in class_str:
                ctas.add(text)
                
        return sorted(list(ctas))

    def _infer_strategy(self, messaging: dict[str, Any], offers: list[str], ctas: list[str]) -> str:
        """Heuristically infer the competitor's main strategy based on extracted data."""
        ctas_lower = [c.lower() for c in ctas]
        offers_lower = [o.lower() for o in offers]
        
        is_sales_led = any("demo" in c or "contact" in c for c in ctas_lower)
        is_product_led = any("free trial" in c or "get started" in c or "try" in c for c in ctas_lower)
        is_price_competitive = any("free" in o or "discount" in o or "$" in o for o in offers_lower)
        
        strategies = []
        if is_product_led:
            strategies.append("Product-Led Growth (Self-serve focus)")
        elif is_sales_led:
            strategies.append("Sales-Led (Enterprise/Demo focus)")
            
        if is_price_competitive:
            strategies.append("Aggressive Pricing/Offers")
            
        if not strategies:
            return "Standard Inbound Strategy"
            
        return " + ".join(strategies)

    def _generate_market_summary(self, competitors: list[CompetitorData]) -> dict[str, Any]:
        """Aggregate data to build a top-level market summary."""
        total = len(competitors)
        if total == 0:
            return {"status": "No competitor data available"}
            
        all_ctas = []
        for comp in competitors:
            all_ctas.extend(comp["ctas"])
            
        common_ctas = {cta: all_ctas.count(cta) for cta in set(all_ctas) if all_ctas.count(cta) > 1}
        
        strategies = [comp["inferred_strategy"] for comp in competitors]
        dominant_strategy = max(set(strategies), key=strategies.count) if strategies else "Unknown"
        
        return {
            "competitors_analyzed": total,
            "dominant_market_strategy": dominant_strategy,
            "common_ctas": common_ctas,
        }
