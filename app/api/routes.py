import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.core.logging import logger
from app.core.errors import AppError, ItemNotFoundError, ValidationError, ScraperError
from app.models.schemas import (
    IngestRequest,
    ItemSummary,
    ItemDetail,
    ItemListResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
)
from app.db.database import db
from app.services.scraper import scraper
from app.services.chunker import get_chunker
from app.services.embedder import get_embedder
from app.services.rag_service import rag_service

router = APIRouter()


@router.post(
    "/ingest",
    response_model=ItemSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest plain text note or web URL",
    description="Fetches URL content or accepts raw text, segments into semantic chunks, generates vector embeddings, and stores in SQLite.",
)
async def ingest_content(payload: IngestRequest):
    settings = get_settings()
    now_iso = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())

    source_type = payload.type
    title = payload.title
    url: Optional[str] = None
    raw_content = ""

    # 1. Fetch or parse content
    if source_type == "url":
        url = payload.content.strip()
        scraped = await scraper.fetch_and_extract(url)
        raw_content = scraped["content"]
        if not title:
            title = scraped["title"]
    else:  # plain text note
        raw_content = payload.content.strip()
        if not title:
            # Auto-title from first line or first 50 chars
            first_line = raw_content.splitlines()[0].strip() if raw_content.splitlines() else "Untitled Note"
            title = first_line[:60] if len(first_line) > 60 else first_line

    if not raw_content:
        raise ValidationError("Ingested content cannot be empty.")

    char_count = len(raw_content)
    word_count = len(raw_content.split())
    content_preview = raw_content[:240] + ("..." if len(raw_content) > 240 else "")

    # 2. Segment content into recursive semantic chunks
    chunker = get_chunker()
    chunks = chunker.chunk_text(raw_content)
    if not chunks:
        raise ValidationError("Content could not be segmented into any chunks.")

    # 3. Generate vector embeddings
    embedder = get_embedder()
    chunk_texts = [c.content for c in chunks]
    embeddings = await embedder.embed_texts(chunk_texts)

    # 4. Prepare chunk records
    chunk_records = []
    for chunk, emb in zip(chunks, embeddings):
        chunk_records.append({
            "id": str(uuid.uuid4()),
            "item_id": item_id,
            "chunk_index": chunk.index,
            "content": chunk.content,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "embedding": emb,
            "created_at": now_iso,
        })

    # 5. Persist item and chunks into SQLite
    db.insert_item(
        item_id=item_id,
        source_type=source_type,
        title=title or "Untitled",
        raw_content=raw_content,
        content_preview=content_preview,
        char_count=char_count,
        word_count=word_count,
        chunk_count=len(chunk_records),
        created_at=now_iso,
        url=url,
        metadata=payload.metadata,
    )
    db.insert_chunks(chunk_records)

    logger.info(
        f"Ingested {source_type} item '{title}' ({item_id}) with {len(chunk_records)} chunks.",
        extra={"item_id": item_id, "chunks_count": len(chunk_records), "provider": embedder.provider_name}
    )

    return ItemSummary(
        id=item_id,
        source_type=source_type,
        title=title or "Untitled",
        url=url,
        content_preview=content_preview,
        char_count=char_count,
        word_count=word_count,
        chunk_count=len(chunk_records),
        created_at=now_iso,
        metadata=payload.metadata or {},
    )


@router.get(
    "/items",
    response_model=ItemListResponse,
    summary="List saved notes and articles",
    description="Returns a paginated list of saved items with metadata, previews, and chunk counts.",
)
async def list_items(
    limit: int = Query(default=100, ge=1, le=500, description="Items limit"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    items_raw, total = db.list_items(limit=limit, offset=offset)
    items = [ItemSummary(**item) for item in items_raw]
    return ItemListResponse(items=items, total=total)


@router.get(
    "/items/{item_id}",
    response_model=ItemDetail,
    summary="Get single item details",
    description="Returns the full raw text and all chunk segments for a specific item.",
)
async def get_item_detail(item_id: str):
    item = db.get_item(item_id)
    if not item:
        raise ItemNotFoundError(item_id)
    return ItemDetail(**item)


@router.delete(
    "/items/{item_id}",
    summary="Delete item",
    description="Deletes a saved item and cascade-deletes its vector chunks from the database.",
)
async def delete_item(item_id: str):
    deleted = db.delete_item(item_id)
    if not deleted:
        raise ItemNotFoundError(item_id)
    logger.info(f"Deleted item {item_id} and its associated vector chunks.")
    return {"deleted": True, "id": item_id}


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask questions over saved knowledge inbox",
    description="Retrieves top relevant chunks using cosine similarity and generates a grounded response with source citations.",
)
async def query_knowledge_inbox(payload: QueryRequest):
    settings = get_settings()
    response = await rag_service.answer_query(
        query=payload.query,
        top_k=payload.top_k or settings.DEFAULT_TOP_K,
        min_score=payload.min_score or settings.MIN_SIMILARITY_SCORE,
    )
    return QueryResponse(**response)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Returns server status, active AI provider models, and database statistics.",
)
@router.get(
    "/healthz",
    response_model=HealthResponse,
    include_in_schema=False,
)
async def health_check():
    settings = get_settings()
    stats = db.get_stats()
    provider = settings.resolve_provider()

    active_emb = (
        settings.OPENAI_EMBEDDING_MODEL if provider == "openai"
        else settings.GEMINI_EMBEDDING_MODEL if provider == "gemini"
        else "deterministic-subword-384"
    )
    active_chat = (
        settings.OPENAI_CHAT_MODEL if provider == "openai"
        else settings.GEMINI_CHAT_MODEL if provider == "gemini"
        else "local-extractive-synthesizer"
    )

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        provider=provider,
        active_embedding_model=active_emb,
        active_chat_model=active_chat,
        items_count=stats["items_count"],
        chunks_count=stats["chunks_count"],
        database_path=stats["db_path"],
    )
