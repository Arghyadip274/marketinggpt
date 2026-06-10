# Website Builder RAG API - Developer Reference

This document provides the technical integration guide for the Website Builder BRD (Business Requirements Document) RAG API. 

## Base URL
All requests should be routed to the FastAPI instance.
Local development: `http://127.0.0.1:8000/api/rag`

## Authentication
This API is secured using a static Bearer token. You must pass this in the `Authorization` header for **all** requests.
- **Header Format**: `Authorization: Bearer <TOKEN>`
- **Development Token**: `marketing4sight_dev_key` (Replace with your `.env` `API_SECRET_KEY` in production).

---

## 1. Upload Document
Uploads a raw BRD document (PDF, TXT, DOCX) to the server. The document is stored temporarily pending chunking and ingestion.

**Endpoint**: `POST /documents/upload`
**Content-Type**: `multipart/form-data`

### cURL Example
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/rag/documents/upload' \
  -H 'Authorization: Bearer marketing4sight_dev_key' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/WEBSITE_BUILDER.docx' \
  -F 'company_id=Marketing4sight' \
  -F 'project_id=website_v1'
```

**Success Response (200 OK)**
```json
{
  "filename": "WEBSITE_BUILDER.docx",
  "status": "uploaded",
  "message": "File uploaded successfully. Please call /ingest to process it.",
  "file_path": "app/rag/documents/WEBSITE_BUILDER.docx"
}
```

---

## 2. Ingest Document
Parses, chunks, and semantically embeds the uploaded document into the multi-tenant vector database (ChromaDB). You must pass the exact `file_path` returned from Step 1.

**Endpoint**: `POST /documents/ingest`
**Content-Type**: `application/x-www-form-urlencoded`

### cURL Example
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/rag/documents/ingest' \
  -H 'Authorization: Bearer marketing4sight_dev_key' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'file_path=app/rag/documents/WEBSITE_BUILDER.docx' \
  -d 'company_id=Marketing4sight' \
  -d 'project_id=website_v1' \
  -d 'module=website_builder' \
  -d 'document_type=BRD'
```

**Success Response (200 OK)**
```json
{
  "status": "success",
  "chunks_indexed": 14,
  "file": "WEBSITE_BUILDER.docx"
}
```

---

## 3. Query the BRD
Ask generative questions against a specific project's BRD. The vector database enforces strict tenant isolation using the provided `company_id` and `project_id`.

**Endpoint**: `POST /modules/website-builder/query`
**Content-Type**: `application/json`

### cURL Example
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/rag/modules/website-builder/query' \
  -H 'Authorization: Bearer marketing4sight_dev_key' \
  -H 'Content-Type: application/json' \
  -d '{
  "company_id": "Marketing4sight",
  "project_id": "website_v1",
  "question": "What is the primary brand color and what core features should be on the pricing page?"
}'
```

**Success Response (200 OK)**
```json
{
  "answer": "Based on the provided BRD, the primary brand color is Hex #FF5733. The core features on the pricing page must include a toggle for monthly/annual billing and a FAQ accordion at the bottom.",
  "sources": [
    {
      "source": "WEBSITE_BUILDER.docx",
      "chunk_index": 2
    },
    {
      "source": "WEBSITE_BUILDER.docx",
      "chunk_index": 5
    }
  ]
}
```

## Error Codes
- **401 Unauthorized**: Missing or invalid Bearer token.
- **404 Not Found**: File path does not exist (during ingestion).
- **500 Internal Server Error**: Gemini LLM failure, ChromaDB query syntax error, or disk IO issues.
