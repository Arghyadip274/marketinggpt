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

    def retrieve_context(self, query: str, top_k: int | None = None, metadata_filter: dict | None = None, extracted_keywords: list[str] | None = None, queries: list[str] | None = None) -> list[str]:
        """Perform a similarity search to retrieve relevant document chunks as text strings.
        
        Args:
            query: The user's question or strategy context.
            top_k: Optional override for the number of chunks.
            metadata_filter: Optional dictionary for filtering documents by metadata.
            extracted_keywords: Optional keywords for Heading Boosting.
            queries: Optional list of expanded synthetic queries.
            
        Returns:
            A list of retrieved textual contexts.
        """
        k = top_k or self.top_k
        results = self.search(query, k=k, metadata_filter=metadata_filter, extracted_keywords=extracted_keywords, queries=queries)
        return [doc["page_content"] for doc in results]


    def _build_bm25(self, metadata_filter: dict | None = None):
        """Builds an in-memory BM25 index of the current ChromaDB child chunks."""
        if not self.use_chroma or not self.collection:
            return None, []
        try:
            bm25_filter = {"chunk_type": "child"}
            if metadata_filter:
                bm25_filter = {"$and": [{"chunk_type": "child"}, metadata_filter]}
                
            all_docs = self.collection.get(where=bm25_filter)
            if not all_docs or not all_docs.get("documents"):
                return None, []
                
            from rank_bm25 import BM25Okapi
            tokenized_corpus = [doc.lower().split(" ") for doc in all_docs["documents"]]
            bm25 = BM25Okapi(tokenized_corpus)
            
            formatted_docs = []
            for doc, meta, doc_id in zip(all_docs["documents"], all_docs["metadatas"], all_docs["ids"]):
                formatted_docs.append({
                    "page_content": doc,
                    "metadata": meta or {},
                    "id": doc_id
                })
            return bm25, formatted_docs
        except Exception as e:
            logger.error("Failed to build BM25 index: %s", e)
            return None, []

    def search(self, query: str, k: int = 4, metadata_filter: dict | None = None, extracted_keywords: list[str] | None = None, queries: list[str] | None = None, return_debug: bool = False) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """Perform similarity search and return full dictionary result (content, metadata, id).
        
        Args:
            query: Semantic search query.
            k: Top k documents.
            metadata_filter: Metadata filters to apply.
            extracted_keywords: Optional keywords for Heading Boosting.
            queries: Optional list of expanded synthetic queries.
            return_debug: If true, returns a tuple of (results, debug_trace_dict).
            
        Returns:
            A list of dictionaries containing keys: page_content, metadata, id.
        """
        logger.info("Hybrid searching vector store for query: '%s', top_k=%d, filter=%s", query, k, metadata_filter)
        
        search_queries = queries if queries else [query]
        vector_filter = {"chunk_type": "child"}
        if metadata_filter:
            vector_filter = {"$and": [{"chunk_type": "child"}, metadata_filter]}
            
        all_results_dict = {}
        
        if self.use_chroma and self.collection is not None:
            try:
                # 1. Vector Search
                vec_results = self.collection.query(
                    query_texts=search_queries,
                    n_results=k * 2,
                    where=vector_filter
                )
                
                for q_idx in range(len(search_queries)):
                    if vec_results and "documents" in vec_results and vec_results["documents"][q_idx]:
                        docs = vec_results["documents"][q_idx]
                        metas = vec_results["metadatas"][q_idx] if vec_results["metadatas"] else [{} for _ in docs]
                        ids = vec_results["ids"][q_idx] if vec_results["ids"] else [f"id_{i}" for i in range(len(docs))]
                        distances = vec_results["distances"][q_idx] if "distances" in vec_results and vec_results["distances"] else [0]*len(docs)
                        
                        for rank, (doc, meta, doc_id, dist) in enumerate(zip(docs, metas, ids, distances)):
                            if doc_id not in all_results_dict:
                                all_results_dict[doc_id] = {
                                    "page_content": doc,
                                    "metadata": meta or {},
                                    "id": doc_id,
                                    "vector_rank": rank,
                                    "bm25_rank": 999
                                }
                            else:
                                all_results_dict[doc_id]["vector_rank"] = min(all_results_dict[doc_id]["vector_rank"], rank)
                                
                # 2. BM25 Search
                bm25, bm25_docs = self._build_bm25(metadata_filter)
                if bm25 and bm25_docs:
                    for search_query in search_queries:
                        tokenized_query = search_query.lower().split(" ")
                        doc_scores = bm25.get_scores(tokenized_query)
                        top_n_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:k*2]
                        for rank, idx in enumerate(top_n_indices):
                            if doc_scores[idx] <= 0: continue
                            doc_id = bm25_docs[idx]["id"]
                            if doc_id not in all_results_dict:
                                all_results_dict[doc_id] = bm25_docs[idx].copy()
                                all_results_dict[doc_id]["vector_rank"] = 999
                                all_results_dict[doc_id]["bm25_rank"] = rank
                            else:
                                all_results_dict[doc_id]["bm25_rank"] = min(all_results_dict[doc_id]["bm25_rank"], rank)
                                
                # 3. Reciprocal Rank Fusion & Heading Boosting
                candidates = list(all_results_dict.values())
                for c in candidates:
                    v_score = 1.0 / (60 + c["vector_rank"]) if c["vector_rank"] < 999 else 0
                    b_score = 1.0 / (60 + c["bm25_rank"]) if c["bm25_rank"] < 999 else 0
                    base_rrf = v_score + b_score
                    
                    boost = 1.0
                    section = str(c["metadata"].get("section", "")).lower()
                    if extracted_keywords and section:
                        for kw in extracted_keywords:
                            if kw.lower() in section:
                                boost = 1.2
                                break
                    c["rrf_score"] = base_rrf * boost
                    
                candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
                top_candidates = candidates[:k*3]
                
                # 4. CrossEncoder Reranking
                try:
                    if not hasattr(self, "_reranker"):
                        from sentence_transformers import CrossEncoder
                        self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                    pairs = [[query, c["page_content"]] for c in top_candidates]
                    rerank_scores = self._reranker.predict(pairs)
                    for i, score in enumerate(rerank_scores):
                        top_candidates[i]["rerank_score"] = float(score)
                    top_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
                except Exception as e:
                    logger.warning("CrossEncoder reranking failed or missing: %s", e)
                    
                final_candidates = top_candidates[:k]
                
                # 5. Parent-Child Context Compression
                resolved_results = []
                for c in final_candidates:
                    parent_id = c["metadata"].get("parent_id")
                    if parent_id:
                        parent_res = self.collection.get(ids=[parent_id])
                        if parent_res and parent_res.get("documents") and len(parent_res["documents"]) > 0:
                            parent_text = parent_res["documents"][0]
                            paragraphs = [p.strip() for p in parent_text.split("\n\n") if len(p.strip()) > 30]
                            if len(paragraphs) > 3:
                                try:
                                    p_pairs = [[query, p] for p in paragraphs]
                                    p_scores = self._reranker.predict(p_pairs)
                                    top_p_indices = sorted(range(len(p_scores)), key=lambda i: p_scores[i], reverse=True)[:3]
                                    compressed_text = "\n\n".join([paragraphs[i] for i in sorted(top_p_indices)])
                                    c["page_content"] = compressed_text
                                except Exception:
                                    c["page_content"] = parent_text
                            else:
                                c["page_content"] = parent_text
                            c["metadata"] = parent_res["metadatas"][0] if parent_res["metadatas"] else c["metadata"]
                    resolved_results.append(c)
                    
                debug_trace = {
                    "query": query,
                    "keywords": extracted_keywords or [],
                    "expanded_queries": search_queries,
                    "rrf_results": [
                        {
                            "id": rc["id"], 
                            "vector_rank": rc.get("vector_rank"), 
                            "bm25_rank": rc.get("bm25_rank"), 
                            "rrf_score": rc.get("rrf_score"),
                            "section": rc["metadata"].get("section")
                        } 
                        for rc in candidates[:k*3]
                    ],
                    "reranked_results": [
                        {
                            "id": tc["id"],
                            "rerank_score": tc.get("rerank_score", 0.0),
                            "section": tc["metadata"].get("section")
                        }
                        for tc in top_candidates
                    ],
                    "final_context": [
                        {"id": fc["id"], "content_preview": fc["page_content"][:100]}
                        for fc in resolved_results
                    ]
                }
                
                if return_debug:
                    return resolved_results, debug_trace
                return resolved_results
                
            except Exception as e:
                logger.error("Hybrid query failed: %s. Falling back to memory store.", e)
                if self.memory_store is not None:
                    res = self.memory_store.similarity_search(query, k=k, filter_dict=metadata_filter)
                    return (res, {}) if return_debug else res
                raise RetrieverError(f"Search failed: {e}") from e

        if self.memory_store is not None:
            res = self.memory_store.similarity_search(query, k=k, filter_dict=metadata_filter)
            return (res, {}) if return_debug else res
            
        return ([], {}) if return_debug else []
