import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_questionnaire_pipeline():
    print("Registered routes:")
    for route in app.routes:
        print(getattr(route, "path", route.name))
        
    print("Testing GET /api/questionnaire...")
    response = client.get("/api/questionnaire")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print("FAILED to fetch questions.")
        return
        
    data = response.json()
    questions = data.get("questions", [])
    print(f"Successfully fetched {len(questions)} questions.")
    if questions:
        print("First question snippet:")
        print(json.dumps(questions[0], indent=2))
        
    print("\nTesting POST /api/questionnaire/submit...")
    
    # We will submit all required questions to test a valid profile generation
    answers = []
    for q in questions:
        if q["required"]:
            answers.append({
                "question": q["question"],
                "answer": "Test Answer" if q["input_type"] == "text" else "test@example.com"
            })
            
    payload = {"answers": answers}
    
    submit_res = client.post("/api/questionnaire/submit", json=payload)
    print(f"Status Code: {submit_res.status_code}")
    
    if submit_res.status_code == 200:
        profile = submit_res.json()
        print(f"Successfully generated business profile with {len(profile.get('profile_data', {}))} keys.")
    else:
        print(f"FAILED submission: {submit_res.text}")

if __name__ == "__main__":
    test_questionnaire_pipeline()
