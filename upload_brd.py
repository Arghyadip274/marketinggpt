import requests
import argparse
import sys
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

def _process_single_file(file_path: Path, company_id: str, project_id: str, headers: dict) -> bool:
    print(f"\n--- Starting BRD Upload Pipeline ---")
    print(f"Target File: {file_path.name}")
    print(f"Tenant: Company='{company_id}', Project='{project_id}'")
    

    print("\n1. Uploading document to server...")
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/rag/documents/upload",
                headers=headers,
                files={"file": (file_path.name, f, "application/octet-stream")},
                data={"company_id": company_id, "project_id": project_id}
            )
            response.raise_for_status()
            upload_data = response.json()
            server_file_path = upload_data["file_path"]
            print(f"✅ Upload successful! Saved to server at: {server_file_path}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload failed: {e}")
        if 'response' in locals() and response is not None:
            print(response.text)
        return False

    # 2. Ingest the file
    print("\n2. Ingesting (Chunking, Embedding, and Indexing in ChromaDB)...")
    try:
        response = requests.post(
            f"{BASE_URL}/rag/documents/ingest",
            headers=headers,
            data={
                "file_path": server_file_path,
                "company_id": company_id,
                "project_id": project_id,
                "document_type": "BRD"
            }
        )
        response.raise_for_status()
        ingest_data = response.json()
        print(f"✅ Ingestion successful! Indexed {ingest_data.get('chunks_indexed', 0)} chunks.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Ingestion failed: {e}")
        if 'response' in locals() and response is not None:
            print(response.text)
        return False
        
    print(f"\n🎉 Done! The BRD '{file_path.name}' is now securely stored in the RAG engine for tenant {company_id}.")
    return True

def upload_and_ingest(path_str: str, company_id: str, project_id: str):
    target_path = Path(path_str)
    headers = {"Authorization": "Bearer marketing4sight_dev_key"}
    
    if not target_path.exists():
        print(f"Error: Path '{path_str}' does not exist.")
        sys.exit(1)
        
    if target_path.is_file():
        success = _process_single_file(target_path, company_id, project_id, headers)
        if not success:
            sys.exit(1)
    elif target_path.is_dir():
        supported_suffixes = {".txt", ".md", ".markdown", ".docx", ".pdf"}
        files_to_process = [
            f for f in target_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported_suffixes
        ]
        
        if not files_to_process:
            print(f"Error: No supported files found in directory '{target_path.name}'.")
            sys.exit(1)
            
        print(f"Found {len(files_to_process)} supported files in '{target_path.name}'. Starting batch upload...\n")
        
        success_count = 0
        for f in files_to_process:
            if _process_single_file(f, company_id, project_id, headers):
                success_count += 1
                
        print(f"\n📊 Batch Upload Summary: {success_count}/{len(files_to_process)} files successfully ingested.")
        if success_count != len(files_to_process):
            sys.exit(1)
    else:
        print(f"Error: Path '{path_str}' is neither a file nor a directory.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and ingest a BRD into the MarketingGPT RAG engine.")
    parser.add_argument("filepath", help="Path to a local BRD file or a directory of BRD files (e.g., my_brd.pdf or ./my_docs_folder)")
    parser.add_argument("--company", required=True, help="Unique ID for the company/tenant")
    parser.add_argument("--project", required=True, help="Unique ID for the project")
    
    args = parser.parse_args()
    upload_and_ingest(args.filepath, args.company, args.project)
