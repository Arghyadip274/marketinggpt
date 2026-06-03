"""Application configuration and settings management."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for MarketingGPT."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application details
    app_name: str = Field(default="MarketingGPT API", description="The name of the service.")
    app_version: str = Field(default="0.1.0", description="Application version.")
    environment: str = Field(default="development", description="Deployment environment (development, staging, production).")

    # API Settings
    api_v1_prefix: str = "/api"
    
    # Security/CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="List of allowed CORS origins."
    )

    # Logging
    log_level: str = Field(default="INFO", description="Global logging level (e.g., INFO, DEBUG).")

    # RAG Settings
    rag_chunk_size: int = Field(default=1000, description="Default chunk size for text splitting.")
    rag_chunk_overlap: int = Field(default=200, description="Default chunk overlap for text splitting.")
    rag_embeddings_model: str = Field(default="all-MiniLM-L6-v2", description="Model name for sentence-transformers local embeddings.")
    rag_vector_store_dir: str = Field(default="app/rag/vector_store", description="Directory to persist the vector database.")
    rag_documents_dir: str = Field(default="app/rag/documents", description="Directory to place documents for ingestion.")

    @property
    def is_production(self) -> bool:
        """Return True if the environment is production."""
        return self.environment.lower() == "production"

# Create a global settings singleton
settings = Settings()
