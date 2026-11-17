import pytest
from app.services.chunker import IntentionalChunker


def test_chunker_empty_text():
    chunker = IntentionalChunker(chunk_size=500, chunk_overlap=100)
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   \n\t  ") == []


def test_chunker_short_text():
    chunker = IntentionalChunker(chunk_size=500, chunk_overlap=100)
    short = "This is a short single-sentence note."
    chunks = chunker.chunk_text(short)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].content == short
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == len(short)


def test_chunker_preserves_paragraphs():
    chunker = IntentionalChunker(chunk_size=200, chunk_overlap=40)
    p1 = "Paragraph one discusses vector embeddings and semantic search pipelines."
    p2 = "Paragraph two covers SQLite storage and cosine similarity calculation."
    p3 = "Paragraph three focuses on frontend design in React with clean hooks."
    text = f"{p1}\n\n{p2}\n\n{p3}"

    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.content) <= 300  # reasonable bounds
        assert c.char_start >= 0
        assert c.char_end <= len(text)


def test_chunker_overlap():
    chunker = IntentionalChunker(chunk_size=120, chunk_overlap=40)
    text = (
        "Alpha beta gamma delta epsilon zeta eta theta. "
        "Iota kappa lambda mu nu xi omicron pi rho sigma. "
        "Tau upsilon phi chi psi omega end of text."
    )
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
    # Verify adjacent chunks share overlapping words/context
    c0 = chunks[0].content
    c1 = chunks[1].content
    assert any(word in c1 for word in c0.split()[-3:])
