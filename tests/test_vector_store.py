import pytest
import uuid
from app.db.database import Database
from app.services.vector_store import SQLiteVectorStore


def test_vector_store_cosine_similarity(test_db):
    store = SQLiteVectorStore()
    store.db = test_db

    # Insert mock item
    item_id = str(uuid.uuid4())
    test_db.insert_item(
        item_id=item_id,
        source_type="note",
        title="Vector Database Architecture",
        raw_content="Vector databases store embeddings for similarity search.",
        content_preview="Vector databases store...",
        char_count=50,
        word_count=8,
        chunk_count=2,
        created_at="2026-11-17T10:00:00Z",
    )

    # Insert two chunks with known vectors
    # Chunk 1: [1.0, 0.0, 0.0]
    # Chunk 2: [0.0, 1.0, 0.0]
    test_db.insert_chunks([
        {
            "id": "c1",
            "item_id": item_id,
            "chunk_index": 0,
            "content": "First chunk content about vectors.",
            "char_start": 0,
            "char_end": 30,
            "embedding": [1.0, 0.0, 0.0],
            "created_at": "2026-11-17T10:00:00Z",
        },
        {
            "id": "c2",
            "item_id": item_id,
            "chunk_index": 1,
            "content": "Second chunk content about orthogonal topic.",
            "char_start": 31,
            "char_end": 60,
            "embedding": [0.0, 1.0, 0.0],
            "created_at": "2026-11-17T10:00:00Z",
        },
    ])

    # Query with vector [1.0, 0.0, 0.0] - should perfectly match chunk 1 with score 1.0
    results = store.search(query_vector=[1.0, 0.0, 0.0], top_k=2, min_score=0.0)
    assert len(results) >= 1
    assert results[0].chunk_id == "c1"
    assert pytest.approx(results[0].similarity_score, 0.01) == 1.0
    assert results[0].source_title == "Vector Database Architecture"


def test_vector_store_empty(test_db):
    store = SQLiteVectorStore()
    store.db = test_db
    results = store.search(query_vector=[0.5, 0.5], top_k=4)
    assert results == []
