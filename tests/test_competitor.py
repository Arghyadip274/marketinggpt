"""Tests for Competitor Intelligence Analyzer."""

from unittest.mock import patch, MagicMock
from app.tools.competitor_analyzer import CompetitorIntelligenceAnalyzer

def test_competitor_analyzer_sales_led():
    analyzer = CompetitorIntelligenceAnalyzer()
    
    # Mocking the requests.get inside the analyzer
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Enterprise CRM</h1><button>Book a Demo</button><a href='/contact'>Contact Sales</a></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        report = analyzer.analyze_competitors(["https://test-competitor.com"])
        
        assert "competitors" in report
        assert len(report["competitors"]) == 1
        assert "Sales-Led" in report["market_summary"]["dominant_market_strategy"]

def test_competitor_analyzer_product_led():
    analyzer = CompetitorIntelligenceAnalyzer()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Free forever software</h1><button>Start Free Trial</button></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        report = analyzer.analyze_competitors(["https://test-competitor.com"])
        
        assert "Product-Led" in report["market_summary"]["dominant_market_strategy"]
