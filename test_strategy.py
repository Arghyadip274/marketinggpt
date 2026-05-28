import json
import logging
from app.services.strategy_service import StrategyService
from app.models.strategy_models import StrategyRequest
from app.models.questionnaire_models import BusinessProfile

logging.basicConfig(level=logging.DEBUG)

def main():
    service = StrategyService()

    # Mock inputs
    profile = BusinessProfile(
        profile_data={
            "What is your business model?": "We are a B2B SaaS platform.",
            "Who is your target audience?": "Enterprise marketers."
        }
    )
    
    request = StrategyRequest(
        business_profile=profile,
        website_url="https://example.com",
        competitors=["https://competitor.com"],
        keywords=["marketing automation", "b2b saas"]
    )

    print("--- Generating Unified Strategy ---")
    try:
        strategy = service.generate_strategy(request)
        print(json.dumps(strategy.model_dump(), indent=2))
        print("\nSUCCESS: Strategy generated correctly.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    main()
