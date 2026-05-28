import json
from app.services.keyword_service import KeywordService, KeywordServiceError

def main():
    service = KeywordService()
    
    valid_keywords = [
        {
            "keyword": "seo software",
            "search_volume": 10000,
            "trend_growth": 0.5,
            "intent_score": 0.8,
            "difficulty": 85
        },
        {
            "keyword": "free seo tools",
            "search_volume": 50000,
            "trend_growth": 0.1,
            "intent_score": 0.3,
            "difficulty": 40
        }
    ]
    
    invalid_keywords = [
        {
            "keyword": "bad data",
            "search_volume": -500, # Invalid negative volume
            "trend_growth": 0.5,
            "intent_score": 0.8,
            "difficulty": 85
        }
    ]

    print("--- Testing Valid Keywords ---")
    try:
        results = service.analyze_keywords(valid_keywords)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\n--- Testing Invalid Keywords (Error Handling) ---")
    try:
        service.analyze_keywords(invalid_keywords)
        print("FAILED: Expected KeywordServiceError was not raised.")
    except KeywordServiceError as e:
        print(f"SUCCESS: Caught expected service error -> {e}")

if __name__ == "__main__":
    main()
