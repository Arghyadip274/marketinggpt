import json
from app.services.trend_service import TrendService, TrendServiceError

def main():
    service = TrendService()
    
    valid_keywords = ["fastapi", "django", "flask"]
    invalid_keywords = [123, True]  # Not strings
    
    print("--- Testing Valid Keywords ---")
    try:
        results = service.analyze_trends(valid_keywords)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\n--- Testing Invalid Keywords (Error Handling) ---")
    try:
        service.analyze_trends(invalid_keywords)
        print("FAILED: Expected TrendServiceError was not raised.")
    except TrendServiceError as e:
        print(f"SUCCESS: Caught expected service error -> {e}")

if __name__ == "__main__":
    main()
