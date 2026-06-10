import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def test_rag_pipeline():
    print("=== Testing Multi-Tenant BRD RAG Pipeline ===\n")
    
    # 1. Create a dummy BRD file
    brd_content = "The website must include a pricing page. The primary brand color is Hex #FF5733."
    with open("test_brd.txt", "w") as f:
        f.write(brd_content)
        
    HEADERS = {"Authorization": "Bearer marketing4sight_dev_key"}

    print("1. Uploading BRD...")
    with open("test_brd.txt", "rb") as f:
        response = requests.post(
            f"{BASE_URL}/rag/documents/upload",
            headers=HEADERS,
            files={"file": ("test_brd.txt", f, "text/plain")},
            data={"company_id": "apple", "project_id": "iphone_site"}
        )
    print(response.json())
    file_path = response.json()["file_path"]
    
    print("\n2. Ingesting BRD (Chunking & Embedding)...")
    response = requests.post(
        f"{BASE_URL}/rag/documents/ingest",
        headers=HEADERS,
        data={
            "file_path": file_path,
            "company_id": "apple",
            "project_id": "iphone_site",
            "document_type": "BRD"
        }
    )
    print(response.json())
    time.sleep(2) # Give ChromaDB a second to index
    
    print("\n3. Querying with CORRECT Tenant Metadata (company: apple)...")
    response = requests.post(
        f"{BASE_URL}/rag/query",
        headers=HEADERS,
        json={
            "company_id": "apple",
            "project_id": "iphone_site",
            "question": "What is the primary brand color?"
        }
    )
    res_json = response.json()
    print(f"Answer: {res_json.get('answer', '')}")
    print(f"Keywords Found: {len(res_json.get('keyword_opportunities', []))}")
    for k in res_json.get('keyword_opportunities', []):
        print(f" - [{k['rank']}] {k['keyword']} (Score: {k['opportunity_score']})")
    
    print("\n4. Querying with INCORRECT Tenant Metadata (company: microsoft)...")
    response = requests.post(
        f"{BASE_URL}/rag/query",
        headers=HEADERS,
        json={
            "company_id": "microsoft",
            "project_id": "surface_site",
            "question": "What is the primary brand color?"
        }
    )
    res_json = response.json()
    print(f"Answer: {res_json.get('answer', '')}")
    print(f"Keywords Found: {len(res_json.get('keyword_opportunities', []))}")
    
if __name__ == "__main__":
    test_rag_pipeline()
