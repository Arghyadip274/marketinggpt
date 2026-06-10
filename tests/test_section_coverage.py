import requests
import re
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api/rag/modules/website-builder"
HEADERS = {
    "Authorization": "Bearer marketing4sight_dev_key",
    "Content-Type": "application/json"
}
COMPANY_ID = "Marketing4sight"
PROJECT_ID = "website_v1"
DOC_PATH = Path("project_docs/Website_Builder_Audit.md")

def extract_sections():
    sections = []
    if not DOC_PATH.exists():
        print(f"Error: Could not find {DOC_PATH}")
        return []
        
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# ") or line.startswith("## ") or line.startswith("### "):
                clean_sec = line.lstrip("#").strip()
                if clean_sec:
                    sections.append(clean_sec)
    return sections

def run_coverage_test():
    print("--- Starting Section Coverage Test ---")
    sections = extract_sections()
    if not sections:
        return
        
    print(f"Detected {len(sections)} sections in document.")
    passed = 0
    
    for section in sections:
        query = f"What does the '{section}' section contain?"
        payload = {
            "company_id": COMPANY_ID,
            "project_id": PROJECT_ID,
            "question": query,
            "document_name": DOC_PATH.name
        }
        
        try:
            # We use the debug endpoint to check what sections were actually retrieved
            res = requests.post(f"{BASE_URL}/debug", json=payload, headers=HEADERS)
            if res.status_code == 200:
                data = res.json()
                trace = data.get("debug_trace", {})
                
                # Check if the desired section is in the top RRF or Reranked results
                found = False
                for r in trace.get("reranked_results", []):
                    if r.get("section") == section:
                        found = True
                        break
                        
                if found:
                    passed += 1
                    print(f"[PASS] Section retrieved: {section}")
                else:
                    print(f"[FAIL] Section missed: {section}")
            else:
                print(f"[ERROR] Request failed for {section}: {res.status_code}")
                
        except Exception as e:
            print(f"Request error: {e}")
            
    print(f"\n=== COVERAGE SCORE: {passed}/{len(sections)} PASSED ===")

if __name__ == "__main__":
    run_coverage_test()
