import os
import shutil
from typing import Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.rag_models import ProjectRAGRequest, DocumentUploadResponse, RAGQueryResponse, RAGSource
from app.rag.rag_service import RAGService
from app.config.settings import settings

router = APIRouter(prefix="/api/rag", tags=["Website Builder RAG"])

# --- Security ---
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate the Bearer token against the server's API_SECRET_KEY."""
    expected_token = os.environ.get("API_SECRET_KEY", "marketing4sight_dev_key")
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# --- Services ---
rag_service = RAGService()


@router.post(
    "/documents/upload", 
    response_model=DocumentUploadResponse,
    summary="Upload a Business Requirements Document",
    description="Uploads a raw document (PDF, TXT, DOCX) to the server. The document is stored temporarily pending chunking and ingestion.",
    responses={
        400: {"description": "Filename not provided"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Internal server error during file IO"}
    }
)
async def upload_document(
    file: UploadFile = File(..., description="The BRD file to upload"),
    company_id: str = Form(..., description="Unique tenant ID"),
    project_id: str = Form(..., description="Unique project ID"),
    token: str = Depends(verify_api_key)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename not provided.")
        
    docs_dir = Path(settings.rag_documents_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = docs_dir / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
    return DocumentUploadResponse(
        filename=file.filename,
        status="uploaded",
        message="File uploaded successfully. Please call /ingest to process it.",
        file_path=str(file_path)
    )

@router.post(
    "/documents/ingest",
    summary="Ingest a document into ChromaDB",
    description="Parses, chunks, and semantically embeds an uploaded document into the multi-tenant vector database.",
    responses={
        401: {"description": "Unauthorized access"},
        404: {"description": "Uploaded file not found on disk"},
        500: {"description": "Ingestion pipeline failure"}
    }
)
async def ingest_document(
    file_path: str = Form(..., description="Absolute or relative path to the uploaded file on the server"),
    company_id: str = Form(..., description="Unique tenant ID"),
    project_id: str = Form(..., description="Unique project ID"),
    document_type: str = Form("BRD", description="Classification of the document"),
    token: str = Depends(verify_api_key)
):
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on server.")
        
    try:
        chunks = rag_service.ingester.ingest_file(
            file_path=path,
            company_id=company_id,
            project_id=project_id,
            document_type=document_type
        )
        return {"status": "success", "chunks_indexed": chunks, "file": path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@router.post(
    "/query", 
    response_model=RAGQueryResponse,
    summary="Query Project Knowledge Base",
    description="Ask questions against a specific project's entire knowledge base. The query strictly filters context by company_id and project_id to ensure zero cross-tenant contamination.",
    responses={
        401: {"description": "Unauthorized access"},
        500: {"description": "LLM generation or Retrieval failure"}
    }
)
async def query_project(
    request: ProjectRAGRequest,
    token: str = Depends(verify_api_key)
):
    # Format for ChromaDB multiple conditions
    metadata_filter = {
        "$and": [
            {"company_id": {"$eq": request.company_id}},
            {"project_id": {"$eq": request.project_id}}
        ]
    }
    
    if hasattr(request, 'document_name') and request.document_name:
        metadata_filter["$and"].append({"source": {"$eq": request.document_name}})
    if hasattr(request, 'section') and request.section:
        metadata_filter["$and"].append({"section": {"$eq": request.section}})
    
    try:
        persona = request.persona if hasattr(request, 'persona') and request.persona else "Kiki (The Smart Marketing Buddy)"
        session_id = request.session_id if hasattr(request, 'session_id') and request.session_id else "default_session"
        result = rag_service.answer_query(request.question, metadata_filter=metadata_filter, persona=persona, session_id=session_id)
        
        sources = [
            RAGSource(source=src["source"], chunk_index=src["chunk_index"]) 
            for src in result.get("sources", [])
        ]
        
        return RAGQueryResponse(
            answer=result["answer"],
            sources=sources,
            faithfulness_score=result.get("faithfulness_score", 0.0),
            unsupported_claims=result.get("unsupported_claims", []),
            keyword_opportunities=result.get("keyword_opportunities", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

@router.post(
    "/debug", 
    summary="Debug RAG Pipeline",
    description="Returns the full internal state of the hybrid retriever including BM25, Vector, RRF, CrossEncoder, and Parent-Child resolution.",
    responses={401: {"description": "Unauthorized access"}}
)
async def debug_project(
    request: ProjectRAGRequest,
    token: str = Depends(verify_api_key)
):
    metadata_filter = {
        "$and": [
            {"company_id": {"$eq": request.company_id}},
            {"project_id": {"$eq": request.project_id}}
        ]
    }
    
    if hasattr(request, 'document_name') and request.document_name:
        metadata_filter["$and"].append({"source": {"$eq": request.document_name}})
    if hasattr(request, 'section') and request.section:
        metadata_filter["$and"].append({"section": {"$eq": request.section}})
    
    try:
        persona = request.persona if hasattr(request, 'persona') and request.persona else "Kiki (The Smart Marketing Buddy)"
        session_id = request.session_id if hasattr(request, 'session_id') and request.session_id else "default_session"
        result = rag_service.answer_query(request.question, metadata_filter=metadata_filter, return_debug=True, persona=persona, session_id=session_id)
        return {
            "answer": result.get("answer"),
            "debug_trace": result.get("debug_trace", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug Query failed: {e}")
