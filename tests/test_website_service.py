import json
from app.services.website_service import WebsiteService, WebsiteServiceError

def main():
    service = WebsiteService()
    
    valid_url = "https://example.com"
    invalid_url = None
    
    print("--- Testing Valid Website URL ---")
    try:
        results = service.analyze_website(valid_url)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\n--- Testing Invalid Input (Error Handling) ---")
    try:
        service.analyze_website(invalid_url)
        print("FAILED: Expected WebsiteServiceError was not raised.")
    except WebsiteServiceError as e:
        print(f"SUCCESS: Caught expected service error -> {e}")

if __name__ == "__main__":
    main()
