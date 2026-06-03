"""Tests for the Industry Analyzer."""

from app.tools.industry_analyzer import IndustryIntelligenceAnalyzer

def test_industry_analyzer_known_industry():
    analyzer = IndustryIntelligenceAnalyzer()
    result = analyzer.analyze_industry("saas")
    
    assert result["industry_matched"] == "Saas"
    assert "Content Marketing / SEO" in result["common_channels"]
    assert result["is_fallback"] is False

def test_industry_analyzer_unknown_industry():
    analyzer = IndustryIntelligenceAnalyzer()
    result = analyzer.analyze_industry("quantum computing software")
    
    # Should use the fallback generic pattern but keep the original name
    assert result["industry_matched"] == "quantum computing software"
    assert result["is_fallback"] is True
