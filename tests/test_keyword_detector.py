"""Tests for the Keyword Opportunity Detector."""

import pytest
from app.tools.keyword_detector import KeywordOpportunityDetector

@pytest.fixture
def detector():
    return KeywordOpportunityDetector()

def test_keyword_detector_normalization_and_scoring(detector: KeywordOpportunityDetector):
    keywords_data = [
        {
            "keyword": "crm software",
            "search_volume": 50000,
            "difficulty": 70,
            "trend_growth": 1.2,
            "intent_score": 0.9
        },
        {
            "keyword": "sales automation tools",
            "search_volume": 18000,
            "difficulty": 45,
            "trend_growth": 1.6,
            "intent_score": 0.85
        },
        {
            "keyword": "free crm for startups",
            "search_volume": 12000,
            "difficulty": 30,
            "trend_growth": 1.8,
            "intent_score": 0.8
        }
    ]
    
    ranked = detector.rank_keywords(keywords_data)
    
    # Check that it returns exactly 3 items
    assert len(ranked) == 3
    
    # Check rank order
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2
    assert ranked[2]["rank"] == 3
    
    # Ensure opportunity score is calculated
    for item in ranked:
        assert "opportunity_score" in item
        assert isinstance(item["opportunity_score"], float)

def test_keyword_detector_empty_list(detector: KeywordOpportunityDetector):
    assert detector.rank_keywords([]) == []

def test_keyword_detector_validation_error(detector: KeywordOpportunityDetector):
    with pytest.raises(ValueError):
        detector.rank_keywords([{"keyword": "missing metrics"}])
