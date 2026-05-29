import json
from app.tools.keyword_detector import KeywordOpportunityDetector

def main():
    detector = KeywordOpportunityDetector()
    
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
    
    print(f"Testing KeywordOpportunityDetector with {len(keywords_data)} keywords...\n")
    ranked_keywords = detector.rank_keywords(keywords_data)
    
    print(json.dumps(ranked_keywords, indent=2))

if __name__ == "__main__":
    main()
