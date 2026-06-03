"""Local sentence-transformers embedding generation.

Provides local embeddings with standard document and query methods,
including a deterministic mock fallback if sentence-transformers is missing.
"""

import logging
import hashlib
import random
from typing import List

from app.config.settings import settings

logger = logging.getLogger(__name__)

class LocalEmbeddings:
    """Wrapper for local sentence-transformers embeddings.
    
    Includes a deterministic hash-based fallback if the package is missing.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.rag_embeddings_model
        self._model = None
        self._fallback_mode = False

        # Attempt to load sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading local sentence-transformers model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.warning(
                "Could not load sentence-transformers (%s). RAG will use deterministic fallback embeddings. Error: %s",
                self.model_name, e
            )
            self._fallback_mode = True

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document strings."""
        if self._fallback_mode or self._model is None:
            return [self._fallback_embed(text) for text in texts]
        
        try:
            embeddings = self._model.encode(texts)
            # Ensure return type is a list of lists of floats
            if hasattr(embeddings, "tolist"):
                return embeddings.tolist()
            return [list(map(float, e)) for e in embeddings]
        except Exception as e:
            logger.error("Error during document embedding generation: %s", e)
            return [self._fallback_embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        if self._fallback_mode or self._model is None:
            return self._fallback_embed(text)
        
        try:
            embeddings = self._model.encode([text])
            embedding = embeddings[0]
            if hasattr(embedding, "tolist"):
                return embedding.tolist()
            return list(map(float, embedding))
        except Exception as e:
            logger.error("Error during query embedding generation: %s", e)
            return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> List[float]:
        """Generate a deterministic fallback mock vector of dimension 384 based on the text hash.
        
        This allows testing and execution to succeed even if torch/sentence-transformers cannot be loaded.
        """
        dim = 384
        # Deterministic hashing based on string
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed generator with hash bytes to make it deterministic
        rng = random.Random(h)
        # Create a unit-normalized random vector
        vector = [rng.gauss(0, 1) for _ in range(dim)]
        norm = sum(x*x for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

try:
    from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
    class ChromaLocalEmbeddings(EmbeddingFunction):
        """ChromaDB compatible embedding function wrapper."""
        def __init__(self, local_embeddings: LocalEmbeddings):
            self.local_embeddings = local_embeddings

        def __call__(self, input: Documents) -> Embeddings:
            return self.local_embeddings.embed_documents(input)
except ImportError:
    class ChromaLocalEmbeddings:  # type: ignore
        """Dummy ChromaLocalEmbeddings for fallback mode."""
        def __init__(self, local_embeddings: LocalEmbeddings):
            self.local_embeddings = local_embeddings
        def __call__(self, input: list[str]) -> list[list[float]]:
            return self.local_embeddings.embed_documents(input)
