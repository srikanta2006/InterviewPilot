import pytest
from app.services.chunker import (
    chunk_text,
    create_document_chunks,
    split_into_semantic_segments,
)


def test_split_into_semantic_segments():
    text = (
        "Paragraph one is about FastAPI and async handling.\n\n"
        "Paragraph two is about React hooks and state.\n\n"
        "Paragraph three discusses Redis caching topologies."
    )
    segments = split_into_semantic_segments(text)
    assert len(segments) == 3
    assert "FastAPI" in segments[0]
    assert "React" in segments[1]
    assert "Redis" in segments[2]


def test_chunk_text_sliding_window():
    # Long text with repeated paragraphs
    text = "\n\n".join([f"Section {i}: Technical content detailing engineering practices." * 15 for i in range(10)])
    chunks = chunk_text(text, target_size=500, overlap_size=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 50


def test_create_document_chunks_metadata():
    text = (
        "Python concurrency requires careful attention to async def vs def.\n\n"
        "Blocking I/O in async def degrades the entire event loop performance."
    )
    chunks = create_document_chunks(
        text=text,
        document_id="doc_fastapi_guide",
        source_name="FastAPI Concurrency Guide",
        scope="shared",
        topic="Backend Concurrency",
    )
    assert len(chunks) >= 1
    c0 = chunks[0]
    assert c0.chunk_id == "doc_fastapi_guide_c000"
    assert c0.document_id == "doc_fastapi_guide"
    assert c0.source_name == "FastAPI Concurrency Guide"
    assert c0.scope == "shared"
    assert c0.topic == "Backend Concurrency"
    assert len(c0.content_hash) == 64  # SHA-256


def test_chunking_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []
    assert create_document_chunks("", "doc_empty", "Empty") == []

