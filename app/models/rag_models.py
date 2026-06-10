from pydantic import BaseModel, Field
from typing import List, Optional

class ProjectRAGRequest(BaseModel):
    company_id: str = Field(..., description="Unique identifier for the tenant/company")
    project_id: str = Field(..., description="Unique identifier for the specific website project")
    question: str = Field(..., description="User's query against the BRD")
    document_name: Optional[str] = Field(None, description="Optional filter to retrieve only from a specific document")
    section: Optional[str] = Field(None, description="Optional filter to retrieve only from a specific heading section")
    persona: Optional[str] = Field("Kiki (The Smart Marketing Buddy)", description="The personality the RAG should adopt")
    session_id: Optional[str] = Field("default_session", description="Optional session ID for chat history")

class DocumentIngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to the uploaded document on disk")
    company_id: str = Field(..., description="Unique identifier for the tenant/company")
    project_id: str = Field(..., description="Unique identifier for the specific website project")
    document_type: str = Field(default="BRD", description="Type of the document (e.g., BRD, Brand_Guidelines)")

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    file_path: str

class RAGSource(BaseModel):
    source: str
    chunk_index: int

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[RAGSource]
    faithfulness_score: float = 0.0
    unsupported_claims: List[str] = []
    keyword_opportunities: List[dict] = []
