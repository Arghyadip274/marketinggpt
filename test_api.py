import json
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_website_analysis():
    print("Testing POST /api/website-analysis...")
    response = client.post("/api/website-analysis", json={"url": "https://example.com"})
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_competitor_analysis():
    print("\nTesting POST /api/competitor-analysis...")
    response = client.post("/api/competitor-analysis", json={"competitor_urls": ["https://example.com"]})
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_industry_analysis():
    print("\nTesting POST /api/industry-analysis...")
    response = client.post("/api/industry-analysis", json={"industry_name": "SaaS"})
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_strategy_analysis():
    print("\nTesting POST /api/marketing-strategy...")
    strategy_payload = {
        "business_profile": {
            "profile_data": {
                "What is your business model?": "We are a B2B SaaS platform.",
                "Who is your target audience?": "Enterprise marketers."
            }
        },
        "website_url": "https://example.com",
        "competitors": ["https://competitor.com"],
        "keywords": ["marketing automation", "b2b saas"]
    }
    response = client.post("/api/marketing-strategy", json=strategy_payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Successfully generated master strategy!")
        strategy_json = response.json()
        print(f"Business Summary: {strategy_json.get('business_summary')}")
        print(f"Recommended Keywords: {len(strategy_json.get('recommended_keywords', []))}")
        print(f"Marketing Recommendations: {len(strategy_json.get('marketing_recommendations', []))}")
    else:
        print(f"FAILED strategy generation: {response.text}")
    assert response.status_code == 200

if __name__ == "__main__":
    test_website_analysis()
    test_competitor_analysis()
    test_industry_analysis()
    test_strategy_analysis()
    print("\nAll tests passed successfully.")
