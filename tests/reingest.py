import requests
import os

url = "http://127.0.0.1:8000/api/rag/documents/ingest"
headers = {"Authorization": "Bearer marketing4sight_dev_key"}
data = {
    "company_id": "Marketing4sight",
    "project_id": "website_v1",
    "file_path": "project_docs/Website_Builder_Audit.md"
}

try:
    res = requests.post(url, headers=headers, data=data)
    print(res.status_code, res.text)
except Exception as e:
    print(f"Failed: {e}")
