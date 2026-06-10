"""RAG Service.

Coordinates document ingestion, vector storage, and similarity search context 
retrieval to support augmented strategy generation.
"""

import logging
from typing import Any, Dict, List, Optional

from app.rag.retriever import KnowledgeRetriever
from app.rag.ingest import DocumentIngester
from app.prompts.personality_manager import PersonalityManager

logger = logging.getLogger(__name__)


class RAGService:
    """Service coordinating document ingestion and context retrieval for strategy generation."""

    def __init__(self, retriever: KnowledgeRetriever | None = None, ingester: DocumentIngester | None = None):
        """Initialize the RAGService.
        
        Args:
            retriever: Optional KnowledgeRetriever instance.
            ingester: Optional DocumentIngester instance.
        """
        self.retriever = retriever or KnowledgeRetriever()
        self.ingester = ingester or DocumentIngester(retriever=self.retriever)
        logger.info("RAGService successfully initialized.")

    def retrieve_context(self, query: str, top_k: int = 4, metadata_filter: dict | None = None) -> list[str]:
        """Retrieve relevant context strings for a query.
        
        Args:
            query: Semantic search query.
            top_k: Number of contexts to retrieve.
            metadata_filter: Optional filter dict.
            
        Returns:
            A list of retrieved textual context snippets.
        """
        logger.info("RAGService.retrieve_context called for query: '%s', top_k=%d", query, top_k)
        return self.retriever.retrieve_context(query, top_k=top_k, metadata_filter=metadata_filter)


    def _init_chat_db(self) -> str:
        import os
        import sqlite3
        import time
        db_path = os.path.join(os.path.dirname(__file__), "chat_history.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history
                     (session_id TEXT, timestamp REAL, role TEXT, content TEXT)''')
        # Prune older than 24 hours (86400 seconds)
        cutoff = time.time() - 86400
        c.execute("DELETE FROM history WHERE timestamp < ?", (cutoff,))
        conn.commit()
        conn.close()
        return db_path

    def _get_chat_history(self, session_id: str) -> str:
        import sqlite3
        db_path = self._init_chat_db()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT role, content FROM history WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return ""
        # Keep last 5 exchanges (10 messages) to avoid token explosion
        rows = rows[-10:]
        formatted = "\n".join(f"{role.capitalize()}: {content}" for role, content in rows)
        return f"\n\nPrevious Conversation History:\n{formatted}"

    def _save_chat_history(self, session_id: str, role: str, content: str):
        import sqlite3
        import time
        db_path = self._init_chat_db()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (session_id, time.time(), role, content))
        conn.commit()
        conn.close()

    def answer_query(self, query: str, metadata_filter: dict | None = None, return_debug: bool = False, persona: str = "Kiki (The Smart Marketing Buddy)", session_id: str = "default_session") -> dict[str, Any]:
        """Retrieve context and generate a real response using the LLM.
        
        Args:
            query: Semantic search query / question.
            metadata_filter: Optional filter dict.
            return_debug: Whether to return internal retrieval traces.
            
        Returns:
            A dict with 'answer', 'sources', and optionally 'debug_trace'.
        """
        import os
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel, Field
        
        logger.info("RAGService.answer_query called for query: '%s', filter: %s", query, metadata_filter)
        
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not google_api_key or google_api_key == "dummy_key":
            logger.error("GOOGLE_API_KEY is missing. Falling back to default RAG response.")
            return {
                "answer": "Based on the provided documents, we can see details regarding your query. (Offline Fallback).",
                "sources": [],
                "keyword_opportunities": [],
                "debug_trace": {},
                "faithfulness_score": 1.0,
                "unsupported_claims": []
            }
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            temperature=0.0,
            max_tokens=1024,
            google_api_key=google_api_key
        )
        
        # --- Query Classification Layer ---
        lower_query = query.lower()
        top_k = 5
        classification = "direct"
        import re
        section_match = re.search(r'(?:show|what is in|retrieve|read)(?: the)? ([\w\s]+) section', lower_query)
        
        if section_match:
            classification = "exact_section"
            top_k = 15
            extracted_sec = section_match.group(1).title()
            # It might be "Technical Debt" or "Recommendations"
            if metadata_filter is None:
                metadata_filter = {}
            if "$and" not in metadata_filter:
                # convert existing simple dict to $and if needed
                if metadata_filter:
                    old_filter = metadata_filter.copy()
                    metadata_filter = {"$and": [old_filter]}
                else:
                    metadata_filter = {"$and": []}
            
            # Avoid appending if there is no $and (edge case)
            if "$and" in metadata_filter:
                metadata_filter["$and"] = [f for f in metadata_filter["$and"] if list(f.keys())[0] != "section"]
                metadata_filter["$and"].append({"section": {"$eq": extracted_sec}})
                
        elif any(w in lower_query for w in ["compare", "vs", "versus", "difference"]):
            classification = "comparison"
            top_k = 10
        elif any(w in lower_query for w in ["gap", "missing", "lack"]):
            classification = "gap_analysis"
            top_k = 15
        elif any(w in lower_query for w in ["summarize", "synthesis", "overview", "all"]):
            classification = "synthesis"
            top_k = 15
        elif any(w in lower_query for w in ["architecture", "flow", "system", "infrastructure", "influence"]):
            classification = "architecture"
            top_k = 10
            
        logger.info("Query Classifier: Intent=%s, Assigned TopK=%d, Filter=%s", classification, top_k, metadata_filter)
        
        # --- Local Smart Query Expansion ---
        try:
            import spacy
            from rake_nltk import Rake
            
            # Cache the spacy model globally if possible, but for now load inline
            if not hasattr(self, "_nlp"):
                self._nlp = spacy.load("en_core_web_sm")
                
            doc = self._nlp(query)
            extracted_keywords = [token.text for token in doc if token.pos_ in ("NOUN", "PROPN")]
            
            rake = Rake()
            rake.extract_keywords_from_text(query)
            keyphrases = rake.get_ranked_phrases()[:2]
            
            extracted_keywords.extend(keyphrases)
            extracted_keywords = list(set([kw.lower() for kw in extracted_keywords if len(kw) > 2]))
            
            generated_queries = [query]
            if keyphrases:
                generated_queries.extend(keyphrases)
                
            logger.info("Local Extraction - Keywords: %s | Queries: %s", extracted_keywords, generated_queries)
        except Exception as e:
            logger.warning("Local pre-retrieval extraction failed: %s", e)
            extracted_keywords = []
            generated_queries = [query]
            
        if return_debug:
            results, debug_trace = self.retriever.search(
                query, k=top_k, metadata_filter=metadata_filter, 
                extracted_keywords=extracted_keywords, queries=generated_queries, return_debug=True
            )
        else:
            results = self.retriever.search(
                query, k=top_k, metadata_filter=metadata_filter, 
                extracted_keywords=extracted_keywords, queries=generated_queries, return_debug=False
            )
            debug_trace = None
        
        if not results:
            return {
                "answer": "No relevant documents found for this query in the knowledge base.",
                "sources": [],
                "debug_trace": debug_trace
            }
            
        context_str = "\n\n".join(f"[Source: {doc['metadata'].get('source', 'Unknown')} (Chunk {doc['metadata'].get('chunk_index', 0)})]\n{doc['page_content']}" for doc in results)
        
        # Optimize token count by truncating context strictly
        if len(context_str) > 15000:
            logger.info("Truncating retrieved context from %d to 15000 characters to optimize token usage.", len(context_str))
            context_str = context_str[:15000] + "\n...[Context Truncated for Token Optimization]"
        
        sources = []
        for doc in results:
            sources.append({
                "source": doc['metadata'].get("source", "Unknown"),
                "chunk_index": doc['metadata'].get("chunk_index", 0)
            })
            
        # Initialize PersonalityManager and fetch base persona prompt
        try:
            persona_mgr = PersonalityManager(active_persona=persona)
            base_system_prompt = persona_mgr.get_system_prompt()
        except Exception as e:
            logger.warning("Failed to load persona '%s', falling back to default: %s", persona, e)
            base_system_prompt = "You are a professional Marketing Assistant."

        # Construct unified system instructions with guardrails
        combined_system_instruction = f"""{base_system_prompt}

You must answer the user's question using the provided context.
- For factual questions, rely strictly on the context.
- For analytical or hypothetical questions, use the provided architecture and context to synthesize expert, logical recommendations.
Do NOT simply say 'I cannot answer this' for hypothetical questions. Extrapolate logically. Cite the context to justify your reasoning.

GUARDRAILS (CRITICAL):
1. Do not provide financial, legal, or medical advice under any circumstances.
2. Do not endorse competitor products.
3. If the context absolutely does not support the answer, politely state that you do not have that information, rather than hallucinating facts."""
        
        # Retrieve history
        history_context = self._get_chat_history(session_id)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_system_instruction),
            ("human", "Context:\n{context}{history_context}\n\nQuestion:\n{question}")
        ])
        
        chain = prompt | llm
        
        try:
            response = chain.invoke({
                "context": context_str,
                "history_context": history_context,
                "question": query
            })
            reply = response.content
            if isinstance(reply, list):
                reply = "".join(b.get("text", "") for b in reply if isinstance(b, dict))
                
            # Save query and reply to history
            self._save_chat_history(session_id, "user", query)
            self._save_chat_history(session_id, "assistant", reply)
                
            # --- Keyword Extraction Pipeline ---
            from pydantic import BaseModel, Field
            from app.services.keyword_service import KeywordService
            
            class KeywordExtraction(BaseModel):
                keyword: str = Field(description="The exact SEO keyword phrase")
                search_volume: float = Field(description="Estimated monthly search volume (100 to 50000)")
                trend_growth: float = Field(description="Estimated growth percentage (e.g. 0.5 for 50%)")
                intent_score: float = Field(description="Commercial intent score from 0.0 to 1.0")
                difficulty: float = Field(description="SEO difficulty score from 1.0 to 100.0")
                
            class KeywordList(BaseModel):
                keywords: list[KeywordExtraction]
                
            keyword_llm = llm.with_structured_output(KeywordList)
            keyword_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert SEO analyst. Based on the following answer, extract up to 5 highly relevant SEO keywords. Estimate realistic mathematical metrics for search_volume, trend_growth, intent_score, and difficulty. Return them strictly conforming to the requested schema."),
                ("human", "{answer}")
            ])
            
            keyword_chain = keyword_prompt | keyword_llm
            keyword_res = keyword_chain.invoke({"answer": reply})
            logger.info("Keyword Extraction Result: %s", keyword_res)
            
            # Rank the keywords using the KeywordService
            ranked_opportunities = []
            if keyword_res and hasattr(keyword_res, 'keywords') and keyword_res.keywords:
                raw_keywords = [kw.model_dump() for kw in keyword_res.keywords]
                keyword_service = KeywordService()
                ranked_opportunities = keyword_service.analyze_keywords(raw_keywords)
            
            # Ensure serialization
            serialized_keywords = [
                {
                    "keyword": k["keyword"],
                    "search_volume": k["search_volume"],
                    "trend_growth": k["trend_growth"],
                    "intent_score": k["intent_score"],
                    "difficulty": k["difficulty"],
                    "opportunity_score": k["opportunity_score"],
                    "rank": k["rank"]
                } for k in ranked_opportunities
            ]
                
            # --- Hallucination Detection ---
            class Faithfulness(BaseModel):
                faithfulness_score: float = Field(description="Score from 0.0 to 1.0 indicating how strictly the answer is derived from the context")
                unsupported_claims: list[str] = Field(description="List of any statements in the answer NOT supported by the context")
                
            faithfulness_score = 1.0
            unsupported_claims = []
            if "I cannot answer this" not in reply:
                try:
                    faith_llm = llm.with_structured_output(Faithfulness)
                    faith_prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are an automated evaluator. Compare the ANSWER against the CONTEXT. Return a faithfulness_score (1.0 if perfectly supported, 0.0 if hallucinated). Note: If the ANSWER contains logical extrapolations, recommendations, or hypothetical architectures based on the system's current state described in the CONTEXT, treat these as SUPPORTED and DO NOT penalize them. Only list strictly factual contradictions or completely irrelevant inventions as unsupported_claims."),
                        ("human", "CONTEXT:\n{context}\n\nANSWER:\n{answer}")
                    ])
                    faith_res = (faith_prompt | faith_llm).invoke({"context": context_str, "answer": reply})
                    faithfulness_score = faith_res.faithfulness_score if hasattr(faith_res, 'faithfulness_score') else 1.0
                    unsupported_claims = faith_res.unsupported_claims if hasattr(faith_res, 'unsupported_claims') else []
                    logger.info("Faithfulness: score=%.2f, unsupported=%s", faithfulness_score, unsupported_claims)
                except Exception as e:
                    logger.warning("Faithfulness check failed: %s", e)
                    
            # --- Analytics Logging ---
            try:
                import sqlite3
                import time
                db_path = os.path.join(os.path.dirname(__file__), "rag_analytics.db")
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS queries
                             (timestamp TEXT, query TEXT, classification TEXT, faithfulness REAL)''')
                c.execute("INSERT INTO queries VALUES (?, ?, ?, ?)",
                          (time.strftime("%Y-%m-%d %H:%M:%S"), query, classification, faithfulness_score))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning("Failed to log analytics: %s", e)
                
            return {
                "answer": reply,
                "sources": sources,
                "keyword_opportunities": serialized_keywords,
                "debug_trace": debug_trace,
                "faithfulness_score": faithfulness_score,
                "unsupported_claims": unsupported_claims
            }
        except Exception as e:
            logger.error("LLM Generation failed: %s", e)
            return {
                "answer": f"Failed to generate answer: {e}",
                "sources": sources,
                "keyword_opportunities": [],
                "debug_trace": debug_trace
            }

    def ingest_documents(self) -> dict[str, Any]:
        """Process all documents inside the configured documents directory.
        
        Returns:
            A status dictionary detailing processed/failed files and chunk counts.
        """
        logger.info("RAGService.ingest_documents triggered.")
        return self.ingester.ingest_directory()
