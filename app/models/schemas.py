from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime, timezone
import re


SourceType = Literal["note", "url"]


class IngestRequest(BaseModel):
    """Payload for POST /ingest"""
    type: SourceType = Field(
        ...,
        description="Type of content: 'note' for raw plain text, 'url' for web pages."
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=300000,
        description="Raw note content or target web URL."
    )
    title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional title. If omitted, will be auto-generated from text or page title."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional custom metadata tags or attributes."
    )

    @field_validator("content")
    @classmethod
    def validate_content_and_url(cls, v: str, info) -> str:
        content_stripped = v.strip()
        if not content_stripped:
            raise ValueError("Content cannot be empty or whitespace only.")

        source_type = info.data.get("type")
        if source_type == "url":
            # Strict validation for URL format
            url_pattern = re.compile(
                r"^https?://[a-zA-Z0-9-._~:/?#\[\]@!$&'()*+,;%=]+$",
                re.IGNORECASE
            )
            if not url_pattern.match(content_stripped):
                raise ValueError("When type is 'url', content must be a valid HTTP or HTTPS URL (e.g. 'https://example.com').")

        return content_stripped

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "note",
                "content": "Turium provides enterprise-grade AI knowledge solutions and modern RAG pipelines.",
                "title": "Turium Overview",
                "metadata": {"tag": "interview-notes"}
            }
        }
    }


class ItemSummary(BaseModel):
    """Compact summary of a saved item for listings."""
    id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    content_preview: str
    char_count: int
    word_count: int
    chunk_count: int
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkPreview(BaseModel):
    """Preview of an individual stored vector chunk."""
    id: str
    chunk_index: int
    char_start: int
    char_end: int
    content: str
    created_at: str


class ItemDetail(ItemSummary):
    """Full detail of an item, including complete raw content and chunk breakdown."""
    raw_content: str
    chunks: List[ChunkPreview] = Field(default_factory=list)


class ItemListResponse(BaseModel):
    """Response shape for GET /items"""
    items: List[ItemSummary]
    total: int


class QueryRequest(BaseModel):
    """Payload for POST /query"""
    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="User's natural language question or search query."
    )
    top_k: Optional[int] = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of top relevant chunks to retrieve for context."
    )
    min_score: Optional[float] = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What are the core features of Turium's RAG pipeline?",
                "top_k": 4,
                "min_score": 0.1
            }
        }
    }


class SourceCitation(BaseModel):
    """A cited chunk snippet returned with query answers."""
    item_id: str
    chunk_id: str
    source_title: str
    source_type: SourceType
    url: Optional[str] = None
    chunk_index: int
    snippet: str
    similarity_score: float


class QueryResponse(BaseModel):
    """Response shape for POST /query"""
    query: str
    answer: str
    sources: List[SourceCitation]
    retrieval_count: int
    provider: str
    model: str
    latency_ms: float


class HealthResponse(BaseModel):
    """System health and operational status."""
    status: str
    version: str
    provider: str
    active_embedding_model: str
    active_chat_model: str
    items_count: int
    chunks_count: int
    database_path: str
