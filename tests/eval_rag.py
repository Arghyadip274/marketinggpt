import os
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/rag/modules/website-builder"
TOKEN = "marketing4sight_dev_key"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def eval_rag():
    print("Starting RAG Evaluation Suite...")
    
    # Check health
    try:
        requests.get("http://127.0.0.1:8000/api/health")
    except requests.exceptions.ConnectionError:
        print("Backend is not running. Please start uvicorn main:app --reload")
        return

    questions = [
        {
            "level": 1,
            "desc": "Direct Retrieval",
            "q": "What technical debt items are identified in the audit?",
            "expected_keywords": ["technical debt", "risk", "components"]
        },
        {
            "level": 2,
            "desc": "Multi-Chunk Retrieval",
            "q": "What recommendations are listed in the Website Builder audit?",
            "expected_keywords": ["recommendation", "audit"]
        },
        {
            "level": 3,
            "desc": "Cross-Document Synthesis",
            "q": "Identify the top 3 production risks and justify them.",
            "expected_keywords": ["production", "risk"]
        },
        {
            "level": 4,
            "desc": "Gap Analysis",
            "q": "Compare requirements vs implementation and identify gaps.",
            "expected_keywords": ["requirements", "implementation", "gap"]
        },
        {
            "level": 5,
            "desc": "Architectural Reasoning",
            "q": "Which onboarding fields influence AI content generation?",
            "expected_keywords": ["onboarding", "ai content"]
        }
    ]
    
    total = len(questions)
    passed = 0
    
    for q in questions:
        print(f"\n--- Level {q['level']}: {q['desc']} ---")
        print(f"Q: {q['q']}")
        
        start_time = time.time()
        
        payload = {
            "company_id": "Marketing4sight",
            "project_id": "website_v1",
            "question": q['q']
        }
        
        try:
            res = requests.post(f"{BASE_URL}/query", json=payload, headers=HEADERS)
            duration = time.time() - start_time
            
            if res.status_code == 200:
                data = res.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                
                print(f"Status: Success ({duration:.2f}s)")
                print(f"Sources retrieved: {len(sources)}")
                
                # We consider it passed if it didn't fail and retrieved sources
                if len(sources) > 0 and "I cannot answer this" not in answer:
                    passed += 1
                    print("Result: PASS")
                else:
                    print("Result: FAIL (No sources or couldn't answer)")
                    print(f"Answer snippet: {answer[:100]}...")
            else:
                print(f"Status: Error {res.status_code}")
                print(res.text)
        except Exception as e:
            print(f"Request failed: {e}")
            
    print(f"\n=== EVALUATION COMPLETE: {passed}/{total} PASSED ===")

if __name__ == "__main__":
    eval_rag()
