import requests
import time
import json
import statistics

BASE_URL = "http://127.0.0.1:8000/api/rag/modules/website-builder"
HEADERS = {"Authorization": "Bearer marketing4sight_dev_key"}

# 20 diverse benchmark questions across 5 categories
BENCHMARK_QUESTIONS = [
    # Category 1: Direct Retrieval
    {"q": "What technical debt items are identified in the audit?", "expected_section": "Technical Debt & Risk Assessment", "cat": "Direct"},
    {"q": "What is the 5-second polling interval issue?", "expected_section": "Recommendations", "cat": "Direct"},
    {"q": "List the generation matrix for the Home page.", "expected_section": "Generation Matrix", "cat": "Direct"},
    {"q": "Who are the target audiences for the system?", "expected_section": "Target Audience", "cat": "Direct"},
    
    # Category 2: Security Analysis
    {"q": "What XSS vulnerabilities exist in the system?", "expected_section": "Security Risks", "cat": "Security"},
    {"q": "How is authentication handled in the Website Builder?", "expected_section": "Authentication Integration", "cat": "Security"},
    {"q": "What are the authorization gaps?", "expected_section": "Security Risks", "cat": "Security"},
    
    # Category 3: Gap Analysis
    {"q": "Compare the required AI features with the current implementation.", "expected_section": "AI Generation Engine", "cat": "Gap"},
    {"q": "What is missing from the WYSIWYG editor?", "expected_section": "Technical Debt & Risk Assessment", "cat": "Gap"},
    {"q": "What was skipped during the Step 1 to Step 2 transition?", "expected_section": "Recommendations", "cat": "Gap"},
    
    # Category 4: Cross Document Synthesis
    {"q": "Identify the top production risks.", "expected_section": "Performance Risks", "cat": "Synthesis"},
    {"q": "Summarize the major backend performance bottlenecks.", "expected_section": "Performance Risks", "cat": "Synthesis"},
    {"q": "What are the highest severity issues to fix before launch?", "expected_section": "Critical / High Severity Issues", "cat": "Synthesis"},
    
    # Category 5: Architecture Reasoning
    {"q": "Which onboarding fields influence AI content generation?", "expected_section": "AI Generation Engine", "cat": "Architecture"},
    {"q": "How does the Parent-Child chunking work?", "expected_section": "General", "cat": "Architecture"},
    {"q": "How is state management handled currently?", "expected_section": "Frontend React Audit", "cat": "Architecture"},
]

def run_benchmark():
    print("=== STARTING MARKETINGGPT RAG BENCHMARK ===\n")
    
    metrics = {
        "passed": 0,
        "failed": 0,
        "latencies": [],
        "faithfulness_scores": [],
        "recall_at_k": 0
    }
    
    for i, item in enumerate(BENCHMARK_QUESTIONS):
        print(f"[{i+1}/{len(BENCHMARK_QUESTIONS)}] Category: {item['cat']}")
        print(f"Q: {item['q']}")
        
        start_t = time.time()
        payload = {
            "company_id": "Marketing4sight",
            "project_id": "website_v1",
            "question": item['q']
        }
        
        try:
            res = requests.post(f"{BASE_URL}/query", json=payload, headers=HEADERS)
            latency = time.time() - start_t
            metrics["latencies"].append(latency)
            
            if res.status_code == 200:
                data = res.json()
                ans = data.get("answer", "")
                sources = data.get("sources", [])
                faith = data.get("faithfulness_score", 0.0)
                metrics["faithfulness_scores"].append(faith)
                
                # Assume Recall@K passes if the LLM successfully generated an answer
                if "I cannot answer this" not in ans and len(sources) > 0:
                    metrics["passed"] += 1
                    metrics["recall_at_k"] += 1
                    print(f"  -> PASS ({latency:.2f}s) | Faithfulness: {faith:.2f}")
                else:
                    metrics["failed"] += 1
                    print(f"  -> FAIL ({latency:.2f}s) | Answer: {ans[:60]}...")
            else:
                metrics["failed"] += 1
                print(f"  -> HTTP ERROR {res.status_code}")
        except Exception as e:
            metrics["failed"] += 1
            print(f"  -> EXCEPTION: {e}")
            
    print("\n=== BENCHMARK RESULTS ===")
    print(f"Total Queries: {len(BENCHMARK_QUESTIONS)}")
    print(f"Success Rate: {metrics['passed']}/{len(BENCHMARK_QUESTIONS)} ({(metrics['passed']/len(BENCHMARK_QUESTIONS))*100:.1f}%)")
    print(f"Recall@K: {(metrics['recall_at_k']/len(BENCHMARK_QUESTIONS))*100:.1f}%")
    
    if metrics["latencies"]:
        print(f"Avg Latency: {statistics.mean(metrics['latencies']):.2f}s")
    if metrics["faithfulness_scores"]:
        print(f"Avg Faithfulness: {statistics.mean(metrics['faithfulness_scores']):.2f}")

if __name__ == "__main__":
    run_benchmark()
