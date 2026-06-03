"""Tests for the Website SEO Analyzer."""

from unittest.mock import patch, MagicMock
from app.tools.website_analyzer import WebsiteSEOAnalyzer

def test_website_analyzer_good_seo():
    analyzer = WebsiteSEOAnalyzer()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = '''
        <html>
            <head>
                <title>Best Software</title>
                <meta name="description" content="A great tool.">
            </head>
            <body>
                <h1>Welcome</h1>
                <h2>Features</h2>
                <img src="logo.png" alt="Company Logo">
                <a href="/pricing">Pricing</a>
                <button>Get Started</button>
            </body>
        </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = analyzer.analyze("https://example.com")
        
        assert result["title"] == "Best Software"
        assert result["h1_count"] == 1
        assert result["image_alt_coverage_percent"] == 100.0
        assert result["internal_link_count"] >= 1
        assert result["cta_count"] >= 1
        assert result["seo_score"] == 100

def test_website_analyzer_bad_seo():
    analyzer = WebsiteSEOAnalyzer()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = '<html><body><img src="logo.png"></body></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = analyzer.analyze("https://example.com")
        
        assert result["title"] is None
        assert result["h1_count"] == 0
        assert result["image_alt_coverage_percent"] == 0.0
        assert result["seo_score"] == 0
