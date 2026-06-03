"""Unit tests for the RAG infrastructure."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import docx

from app.rag.embeddings import LocalEmbeddings
from app.rag.retriever import KnowledgeRetriever, MemoryVectorStore
from app.rag.ingest import DocumentIngester, IngestError
from app.rag.rag_service import RAGService


def test_local_embeddings_fallback():
    """Test that LocalEmbeddings falls back deterministically to hash-based vectors."""
    # Force fallback mode by raising an error on import of sentence-transformers
    with patch("sentence_transformers.SentenceTransformer", side_effect=ImportError("Mock missing package")):
        embeddings = LocalEmbeddings(model_name="nonexistent-model")
        assert embeddings._fallback_mode is True

        text = "Hello world of marketing"
        vec = embeddings.embed_query(text)
        assert len(vec) == 384
        # Verify normalization
        norm = sum(x*x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-5) == 1.0

        # Deterministic check
        vec2 = embeddings.embed_query(text)
        assert vec == vec2

        # Multiple texts
        texts = ["Text A", "Text B"]
        vecs = embeddings.embed_documents(texts)
        assert len(vecs) == 2
        assert len(vecs[0]) == 384
        assert len(vecs[1]) == 384


def test_memory_vector_store():
    """Test the MemoryVectorStore fallback logic, including similarity matching and metadata filtering."""
    embeddings = LocalEmbeddings()
    store = MemoryVectorStore(embeddings)

    texts = [
        "A strategy is focused on inbound marketing and search engine optimization.",
        "Social media campaigns are useful for brand awareness and content creation.",
        "Competitor analysis helps detect pricing strategies and market position."
    ]
    metadatas = [
        {"source": "seo.txt", "topic": "SEO"},
        {"source": "social.txt", "topic": "Social"},
        {"source": "competitor.txt", "topic": "Competitor"}
    ]
    ids = ["id_0", "id_1", "id_2"]

    store.add_texts(texts, metadatas=metadatas, ids=ids)

    # Search for inbound marketing/SEO content
    results = store.similarity_search("inbound marketing", k=1)
    assert len(results) == 1
    assert "inbound marketing" in results[0]["page_content"]
    assert results[0]["metadata"]["topic"] == "SEO"

    # Search with metadata filter
    results_filtered = store.similarity_search("marketing strategy", k=3, filter_dict={"topic": "Social"})
    assert len(results_filtered) == 1
    assert "Social media campaigns" in results_filtered[0]["page_content"]
    assert results_filtered[0]["metadata"]["topic"] == "Social"


def test_document_ingester_parsing(tmp_path):
    """Test document ingester parsers for TXT, Markdown, DOCX, and PDF."""
    ingester = DocumentIngester(documents_dir=str(tmp_path))

    # 1. TXT Ingestion
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello TXT Content", encoding="utf-8")
    assert ingester.parse_txt(txt_file) == "Hello TXT Content"

    # 2. Markdown Ingestion
    md_file = tmp_path / "test.md"
    md_file.write_text("## Markdown Title\nHello MD Content", encoding="utf-8")
    assert ingester.parse_md(md_file) == "## Markdown Title\nHello MD Content"

    # 3. DOCX Ingestion
    docx_file = tmp_path / "test.docx"
    doc = docx.Document()
    doc.add_paragraph("Hello DOCX Paragraph")
    doc.save(str(docx_file))
    assert "Hello DOCX Paragraph" in ingester.parse_docx(docx_file)

    # 4. PDF Ingestion (mocking pypdf)
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("PDF Binary Mock", encoding="utf-8")
    
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello PDF Extracted Text"
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        assert ingester.parse_pdf(pdf_file) == "Hello PDF Extracted Text"


def test_document_ingester_chunking_and_ingestion(tmp_path):
    """Test ingestion end-to-end using recursive splitting and the retriever wrapper."""
    # Force Memory Store fallback for Retriever
    with patch("chromadb.PersistentClient", side_effect=Exception("Force Fallback")):
        retriever = KnowledgeRetriever(vector_store_dir=str(tmp_path / "vstore"))
        assert retriever.use_chroma is False
        assert retriever.memory_store is not None

        ingester = DocumentIngester(documents_dir=str(tmp_path), retriever=retriever)

        # Write text file with long text to force split
        txt_file = tmp_path / "strategy.txt"
        long_text = "Word " * 500  # Will exceed default chunk size of 1000 chars
        txt_file.write_text(long_text, encoding="utf-8")

        chunks_created = ingester.ingest_file(txt_file, chunk_size=200, chunk_overlap=20)
        assert chunks_created > 1

        # Search the ingested text
        contexts = retriever.retrieve_context("Word", top_k=2)
        assert len(contexts) == 2
        assert "Word" in contexts[0]


def test_rag_service_orchestration(tmp_path):
    """Test end-to-end integration via the RAGService."""
    with patch("chromadb.PersistentClient", side_effect=Exception("Force Fallback")):
        retriever = KnowledgeRetriever(vector_store_dir=str(tmp_path / "vstore"))
        ingester = DocumentIngester(documents_dir=str(tmp_path), retriever=retriever)
        service = RAGService(retriever=retriever, ingester=ingester)

        # Write some files
        (tmp_path / "doc1.txt").write_text("Competitor pricing strategy details.", encoding="utf-8")
        (tmp_path / "doc2.md").write_text("# Social Campaign\nInstagram and Facebook ads guide.", encoding="utf-8")

        # Ingest directory
        res = service.ingest_documents()
        assert res["status"] == "success"
        assert len(res["processed_files"]) == 2
        assert res["chunks_processed"] >= 2

        # Retrieve context
        contexts = service.retrieve_context("pricing", top_k=1)
        assert len(contexts) == 1
        assert "pricing" in contexts[0]

        # Answer query
        answer = service.answer_query("pricing")
        assert "Based on the retrieved marketing knowledge" in answer
        assert "pricing" in answer


def test_ingest_nonexistent_file():
    """Verify ingestion raises IngestError on invalid file."""
    ingester = DocumentIngester()
    with pytest.raises(IngestError):
        ingester.ingest_file(Path("nonexistent_file_path_123.txt"))


def test_ingest_unsupported_type(tmp_path):
    """Verify ingestion raises IngestError on unsupported extension."""
    ingester = DocumentIngester(documents_dir=str(tmp_path))
    unsupported_file = tmp_path / "test.jpg"
    unsupported_file.write_text("image dummy", encoding="utf-8")
    with pytest.raises(IngestError):
        ingester.ingest_file(unsupported_file)
