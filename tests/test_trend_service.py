"""Tests for Trend Analyzer."""

from app.tools.trend_analyzer import TrendAnalyzer

def test_trend_analyzer_mocked_data():
    analyzer = TrendAnalyzer()
    
    # It defaults to mock data if pytrends is unavailable or in mock mode
    result = analyzer.fetch_google_trends(["b2b saas", "marketing automation"])
    
    assert "rising_keywords" in result
    assert "trend_scores" in result
    assert "b2b saas" in result["trend_scores"]
