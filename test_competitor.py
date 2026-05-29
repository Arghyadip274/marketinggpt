import json
from app.tools.competitor_analyzer import CompetitorIntelligenceAnalyzer

def main():
    analyzer = CompetitorIntelligenceAnalyzer()
    
    # We use some generic stable domains for testing
    competitors = [
        "https://www.hubspot.com",
        "https://www.salesforce.com",
        "https://www.zoho.com"
    ]
    
    print(f"Testing competitor analysis for {len(competitors)} URLs...")
    report = analyzer.analyze_competitors(competitors)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
