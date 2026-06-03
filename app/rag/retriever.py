"""Semantic retrieval pipeline.

Queries the local vector store (ChromaDB or in-memory fallback) to augment
LLM generations with contextual marketing intelligence.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.rag.embeddings import LocalEmbeddings, ChromaLocalEmbeddings

logger = logging.getLogger(__name__)


class RetrieverError(Exception):
    """Base exception for retrieval failures."""


class MemoryVectorStore:
    """A lightweight in-memory fallback vector store when ChromaDB is not available."""
    
    def __init__(self, embeddings: LocalEmbeddings):
        self.embeddings = embeddings
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.vectors: List[List[float]] = []

    def add_texts(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict[str, Any]]] = None, 
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add texts, generate embeddings, and store them."""
        metadatas = metadatas or [{} for _ in texts]
        ids = ids or [f"id_{i}" for i in range(len(self.documents), len(self.documents) + len(texts))]
        vectors = self.embeddings.embed_documents(texts)
        
        for text, meta, text_id, vec in zip(texts, metadatas, ids, vectors):
            self.documents.append(text)
            self.metadatas.append(meta)
            self.ids.append(text_id)
            self.vectors.append(vec)
        return ids

    def similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform simple cosine similarity search over in-memory documents."""
        if not self.documents:
            return []
            
        query_vec = self.embeddings.embed_query(query)
        
        scores = []
        for i, doc_vec in enumerate(self.vectors):
            # Evaluate metadata filter if specified
            meta = self.metadatas[i]
            if filter_dict:
                match = True
                for fk, fv in filter_dict.items():
                    if meta.get(fk) != fv:
                        match = False
                        break
                if not match:
                    continue
            
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_vec, doc_vec))
            norm_a = sum(a * a for a in query_vec) ** 0.5
            norm_b = sum(b * b for b in doc_vec) ** 0.5
            similarity = dot / (norm_a * norm_b) if (norm_a * norm_b) > 0 else 0.0
            
            scores.append((similarity, i))
            
        # Sort by similarity in descending order
        scores.sort(key=lambda x: x[0], reverse=True)
        top_indices = [idx for _, idx in scores[:k]]
        
        results = []
        for idx in top_indices:
            results.append({
                "page_content": self.documents[idx],
                "metadata": self.metadatas[idx],
                "id": self.ids[idx]
            })
        return results


class KnowledgeRetriever:
    """Handles semantic search queries against the vector store (ChromaDB or Memory fallback)."""

    def __init__(self, vector_store_dir: str | None = None, top_k: int = 4):
        """Initialize the retriever.
        
        Args:
            vector_store_dir: Path to the persistent vector database.
            top_k: Number of semantic chunks to return per query.
        """
        self.top_k = top_k
        base_dir = Path(__file__).parent.parent
        self.vector_store_dir = Path(vector_store_dir) if vector_store_dir else Path(settings.rag_vector_store_dir)
        
        self.embeddings = LocalEmbeddings()
        self.chroma_client = None
        self.collection = None
        self.memory_store = None
        self.use_chroma = False

        # Attempt to load ChromaDB
        try:
            import chromadb
            logger.info("Initializing ChromaDB persistent client at: %s", self.vector_store_dir)
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=str(self.vector_store_dir))
            
            # Wrap embeddings for ChromaDB
            chroma_emb_fn = ChromaLocalEmbeddings(self.embeddings)
            
            # Initialize collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="marketing_knowledge",
                embedding_function=chroma_emb_fn  # type: ignore
            )
            self.use_chroma = True
            logger.info("ChromaDB vector store successfully initialized.")
        except Exception as e:
            logger.warning(
                "ChromaDB persistent client failed to initialize. Falling back to in-memory vector store. Error: %s",
                e
            )
            self.memory_store = MemoryVectorStore(self.embeddings)

    def retrieve_context(self, query: str, top_k: int | None = None, metadata_filter: dict | None = None) -> list[str]:
        """Perform a similarity search to retrieve relevant document chunks as text strings.
        
        Args:
            query: The user's question or strategy context.
            top_k: Optional override for the number of chunks.
            metadata_filter: Optional dictionary for filtering documents by metadata.
            
        Returns:
            A list of retrieved textual contexts.
        """
        k = top_k or self.top_k
        results = self.search(query, k=k, metadata_filter=metadata_filter)
        return [doc["page_content"] for doc in results]

    def search(self, query: str, k: int = 4, metadata_filter: dict | None = None) -> list[dict[str, Any]]:
        """Perform similarity search and return full dictionary result (content, metadata, id).
        
        Args:
            query: Semantic search query.
            k: Top k documents.
            metadata_filter: Metadata filters to apply.
            
        Returns:
            A list of dictionaries containing keys: page_content, metadata, id.
        """
        logger.info("Searching vector store for query: '%s', top_k=%d, filter=%s", query, k, metadata_filter)
        
        if self.use_chroma and self.collection is not None:
            try:
                # Query ChromaDB
                results = self.collection.query(
                    query_texts=[query],
                    n_results=k,
                    where=metadata_filter
                )
                
                formatted = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0] if results["metadatas"] else [{} for _ in docs]
                    ids = results["ids"][0] if results["ids"] else [f"id_{i}" for i in range(len(docs))]
                    
                    for doc, meta, doc_id in zip(docs, metas, ids):
                        formatted.append({
                            "page_content": doc,
                            "metadata": meta or {},
                            "id": doc_id
                        })
                return formatted
            except Exception as e:
                logger.error("ChromaDB query failed: %s. Falling back to memory store.", e)
                # Fallback to memory store
                if self.memory_store is not None:
                    return self.memory_store.similarity_search(query, k=k, filter_dict=metadata_filter)
                raise RetrieverError(f"Search failed: {e}") from e

        # Memory store fallback search
        if self.memory_store is not None:
            return self.memory_store.similarity_search(query, k=k, filter_dict=metadata_filter)
            
        return []
