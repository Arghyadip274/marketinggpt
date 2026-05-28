import json
from app.tools.industry_analyzer import IndustryIntelligenceAnalyzer

def main():
    analyzer = IndustryIntelligenceAnalyzer()
    
    industries_to_test = [
        "B2B SaaS Startup",
        "Local Real Estate Agent",
        "Underwater Basket Weaving"
    ]
    
    for industry in industries_to_test:
        print(f"\n--- Testing: {industry} ---")
        report = analyzer.analyze_industry(industry)
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
