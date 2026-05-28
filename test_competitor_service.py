import json
from app.services.competitor_service import CompetitorService, CompetitorServiceError

def main():
    service = CompetitorService()
    
    valid_urls = ["https://example.com"]
    invalid_urls = "https://example.com"  # String instead of list
    
    print("--- Testing Valid Competitor URLs ---")
    try:
        results = service.analyze_competitors(valid_urls)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\n--- Testing Invalid Input (Error Handling) ---")
    try:
        service.analyze_competitors(invalid_urls) # type: ignore
        print("FAILED: Expected CompetitorServiceError was not raised.")
    except CompetitorServiceError as e:
        print(f"SUCCESS: Caught expected service error -> {e}")

if __name__ == "__main__":
    main()
