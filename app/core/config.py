from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Server Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    APP_NAME: str = "Turium AI Knowledge Inbox"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_PATH: str = "knowledge_inbox.db"

    # AI Provider Settings ("auto", "openai", "gemini", "local")
    AI_PROVIDER: str = "auto"

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # Google Gemini Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_CHAT_MODEL: str = "gemini-3-flash-preview"

    # Chunking Configuration
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    # RAG Retrieval Configuration
    DEFAULT_TOP_K: int = 4
    MIN_SIMILARITY_SCORE: float = 0.05

    # Scraping Configuration
    SCRAPE_TIMEOUT_SECONDS: float = 15.0
    MAX_SCRAPE_BYTES: int = 5 * 1024 * 1024  # 5MB limit
    MAX_CONTENT_CHARS: int = 300000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def resolve_provider(self) -> str:
        """Determines active AI provider based on preference and available API keys."""
        req = self.AI_PROVIDER.lower().strip()
        if req == "openai" and self.OPENAI_API_KEY:
            return "openai"
        if req == "gemini" and self.GEMINI_API_KEY:
            return "gemini"
        if req == "local":
            return "local"

        # Auto detection logic
        if self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip():
            return "openai"
        if self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip():
            return "gemini"

        return "local"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
