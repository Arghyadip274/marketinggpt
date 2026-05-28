"""Industry Intelligence Analyzer tool."""

from __future__ import annotations

import logging
from typing import Any
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MessagingBenchmark(TypedDict):
    """Structured messaging benchmarks for an industry."""
    primary_value_prop: str
    tone: str
    common_objections_addressed: list[str]


class IndustryIntelligenceReport(TypedDict):
    """Structured industry intelligence payload."""
    industry_matched: str
    is_fallback: bool
    patterns: list[str]
    common_channels: list[str]
    common_offers: list[str]
    messaging_benchmarks: MessagingBenchmark
    positioning_trends: list[str]


class IndustryIntelligenceAnalyzer:
    """Rule-based engine to provide marketing intelligence for various industries."""

    def __init__(self) -> None:
        self.knowledge_base = self._build_knowledge_base()

    def analyze_industry(self, industry_name: str) -> IndustryIntelligenceReport:
        """Fetch marketing intelligence for the requested industry."""
        normalized_name = self._normalize_industry_name(industry_name)
        logger.info("Analyzing industry: '%s' (normalized: '%s')", industry_name, normalized_name)

        # Keyword matching heuristic
        matched_key = None
        for key in self.knowledge_base.keys():
            if key in normalized_name or normalized_name in key:
                matched_key = key
                break
                
        # If no strict match, check if any keyword overlaps
        if not matched_key:
            words = set(normalized_name.split())
            for key in self.knowledge_base.keys():
                if any(word in key for word in words if len(word) > 3):
                    matched_key = key
                    break

        if matched_key:
            logger.info("Successfully matched industry to knowledge base key: %s", matched_key)
            data = self.knowledge_base[matched_key]
            is_fallback = False
            actual_industry = matched_key.title()
        else:
            logger.warning("No match found for '%s'. Using generic B2B fallback.", industry_name)
            data = self.knowledge_base["generic"]
            is_fallback = True
            actual_industry = industry_name

        report: IndustryIntelligenceReport = {
            "industry_matched": actual_industry,
            "is_fallback": is_fallback,
            "patterns": data["patterns"],
            "common_channels": data["common_channels"],
            "common_offers": data["common_offers"],
            "messaging_benchmarks": data["messaging_benchmarks"],
            "positioning_trends": data["positioning_trends"],
        }
        return report

    def _normalize_industry_name(self, name: str) -> str:
        """Clean and normalize the industry name for matching."""
        import string
        name = name.lower().strip()
        # Remove punctuation
        name = name.translate(str.maketrans("", "", string.punctuation))
        return name

    def _build_knowledge_base(self) -> dict[str, Any]:
        """Construct the internal rule-based database of industry intelligence."""
        
        return {
            "saas": {
                "patterns": ["High CLV focus", "Subscription revenue model", "Heavy reliance on inbound marketing"],
                "common_channels": ["LinkedIn Ads", "Content Marketing / SEO", "Product Hunt", "Cold Email"],
                "common_offers": ["14-Day Free Trial", "Freemium Tier", "Book a Demo", "Annual Discount"],
                "messaging_benchmarks": {
                    "primary_value_prop": "Save time, automate workflows, and increase ROI.",
                    "tone": "Professional, innovative, and authoritative.",
                    "common_objections_addressed": ["Integration difficulty", "Data security", "Time to onboard"]
                },
                "positioning_trends": ["Product-Led Growth (PLG)", "AI integration features", "Usage-based pricing"]
            },
            "ecommerce": {
                "patterns": ["High volume transactional", "Seasonality driven", "Visual-first marketing"],
                "common_channels": ["Instagram / TikTok Ads", "Google Shopping", "Email Newsletters", "Influencer Marketing"],
                "common_offers": ["10% Off First Order", "Free Shipping over $50", "BOGO", "Limited Time Flash Sale"],
                "messaging_benchmarks": {
                    "primary_value_prop": "High-quality products delivered fast at a great price.",
                    "tone": "Urgent, exciting, and lifestyle-oriented.",
                    "common_objections_addressed": ["Shipping costs", "Return policy", "Product quality"]
                },
                "positioning_trends": ["Sustainable/Ethical sourcing", "Direct-to-Consumer (DTC) authenticity", "User Generated Content (UGC)"]
            },
            "real estate": {
                "patterns": ["Hyper-local targeting", "High ticket, low frequency", "Relationship driven"],
                "common_channels": ["Zillow/Trulia Ads", "Facebook Local Ads", "Direct Mail", "Local SEO"],
                "common_offers": ["Free Home Valuation", "Exclusive Property Lists", "First-time Buyer Guide"],
                "messaging_benchmarks": {
                    "primary_value_prop": "Find your dream home or sell for top dollar with local experts.",
                    "tone": "Trustworthy, community-focused, and premium.",
                    "common_objections_addressed": ["Agent commission fees", "Market timing", "Hidden property issues"]
                },
                "positioning_trends": ["Virtual 3D tours", "Off-market access", "Neighborhood lifestyle selling"]
            },
            "healthcare": {
                "patterns": ["Trust and authority critical", "Heavy regulatory compliance", "Local search dominance"],
                "common_channels": ["Google Search Ads (High Intent)", "Local SEO (Google Business)", "Patient Referrals", "Content Marketing"],
                "common_offers": ["Free Initial Consultation", "New Patient Special", "Insurance Coverage Check"],
                "messaging_benchmarks": {
                    "primary_value_prop": "Compassionate, state-of-the-art care you can trust.",
                    "tone": "Empathetic, clinical, and reassuring.",
                    "common_objections_addressed": ["Insurance acceptance", "Wait times", "Pain/Discomfort"]
                },
                "positioning_trends": ["Telehealth availability", "Holistic/Preventative focus", "Patient reviews as social proof"]
            },
            "finance": {
                "patterns": ["Long decision cycles", "Trust and security paramount", "Compliance heavy"],
                "common_channels": ["LinkedIn", "Google Search Ads", "Financial Webinars", "Authority Blogging"],
                "common_offers": ["Free Portfolio Review", "0% Intro APR", "Sign-up Cash Bonus", "Free Financial Plan"],
                "messaging_benchmarks": {
                    "primary_value_prop": "Grow and protect your wealth with secure, expert guidance.",
                    "tone": "Serious, secure, and highly professional.",
                    "common_objections_addressed": ["Hidden fees", "Market volatility risks", "Security breaches"]
                },
                "positioning_trends": ["Fintech disruption", "ESG (Environmental, Social, Governance) investing", "Fee transparency"]
            },
            "generic": {
                "patterns": ["Standard lead generation", "B2B sales cycle"],
                "common_channels": ["Google Ads", "LinkedIn", "SEO", "Email Marketing"],
                "common_offers": ["Contact Us", "Download Whitepaper", "Request a Quote", "Newsletter Signup"],
                "messaging_benchmarks": {
                    "primary_value_prop": "Reliable solutions to improve your business outcomes.",
                    "tone": "Professional and clear.",
                    "common_objections_addressed": ["Cost", "Implementation time", "Reliability"]
                },
                "positioning_trends": ["Customer-centric solutions", "Digital transformation"]
            }
        }
