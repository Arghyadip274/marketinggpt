import json
from app.services.industry_service import IndustryService, IndustryServiceError

def main():
    service = IndustryService()
    
    valid_industry = "SaaS Startup"
    invalid_industry = None  # None instead of string
    
    print("--- Testing Valid Industry Name ---")
    try:
        results = service.analyze_industry(valid_industry)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"FAILED: {e}")
        
    print("\n--- Testing Invalid Input (Error Handling) ---")
    try:
        service.analyze_industry(invalid_industry) # type: ignore
        print("FAILED: Expected IndustryServiceError was not raised.")
    except IndustryServiceError as e:
        print(f"SUCCESS: Caught expected service error -> {e}")

if __name__ == "__main__":
    main()
