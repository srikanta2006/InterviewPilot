import os
import shutil
import tempfile
import pytest
from app.services.embeddings import EmbeddingService
from app.services.retriever import KnowledgeRetriever

SAMPLE_FASTAPI_DOC = """
# Python and FastAPI Concurrency Guide
FastAPI natively supports asynchronous request processing through asyncio.
When an endpoint is declared with async def, it runs directly on the main event loop thread.
Blocking calls in async def starve the event loop, degrading throughput.
Standard def endpoints are automatically offloaded to an external threadpool.
"""

SAMPLE_REACT_DOC = """
# Modern React State Architecture
React manages UI through declarative component rendering and Virtual DOM reconciliation.
useState handles component local state, while useEffect coordinates side-effects.
Stable key props ensure reconciliation correctly tracks list element insertions and deletions.
useCallback and useMemo provide referential stability and performance optimization.
"""

SAMPLE_SYSTEM_DESIGN_DOC = """
# Distributed Caching and Database Architecture
Cache-Aside lazy loading queries the cache first, falling back to database on miss.
Write-Through writes synchronously to cache and database, ensuring data consistency.
Redis LRU and LFU eviction policies purge stale keys when memory limits are reached.
B-Tree indexes provide logarithmic search times for equality and range filters.
"""

SAMPLE_JOB_DOC = """
# Nexus Platform Evaluation Standards
All candidate evaluation pipelines must respond within 200 milliseconds at p99.
Scoring logic must reference grounded evidence chunks using stable chunk IDs.
Speculative judgments without evidence must be classified as insufficient_evidence.
"""


@pytest.fixture
def temp_retriever():
    """Create a KnowledgeRetriever instance operating in a temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
    # Use deterministic mock embedding for fast, isolated test runs
    mock_embeddings = EmbeddingService(use_mock_fallback=True)
    retriever_instance = KnowledgeRetriever(
        persist_dir=temp_dir,
        embedding_service=mock_embeddings,
    )
    yield retriever_instance
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_ingest_and_idempotency(temp_retriever):
    # Initial Ingestion
    res1 = temp_retriever.ingest_document(
        text=SAMPLE_FASTAPI_DOC,
        source_name="FastAPI Guide",
        scope="shared",
        topic="FastAPI Concurrency",
        document_id="doc_fastapi_test",
    )
    assert res1.status == "ingested"
    assert res1.chunks_created > 0
    assert res1.document_id == "doc_fastapi_test"

    # Duplicate Ingestion (Same Content)
    res2 = temp_retriever.ingest_document(
        text=SAMPLE_FASTAPI_DOC,
        source_name="FastAPI Guide",
        scope="shared",
        topic="FastAPI Concurrency",
        document_id="doc_fastapi_test",
    )
    assert res2.status == "already_indexed"
    assert "already indexed" in res2.message.lower()

    # Content Updated
    updated_text = SAMPLE_FASTAPI_DOC + "\nAdditional section covering Pydantic v2 core performance."
    res3 = temp_retriever.ingest_document(
        text=updated_text,
        source_name="FastAPI Guide",
        scope="shared",
        topic="FastAPI Concurrency",
        document_id="doc_fastapi_test",
    )
    assert res3.status == "updated"


def test_retrieval_relevance_labeled_queries(temp_retriever):
    # Ingest technical corpus
    temp_retriever.ingest_document(SAMPLE_FASTAPI_DOC, "FastAPI Guide", "shared", "Backend", "doc_fastapi")
    temp_retriever.ingest_document(SAMPLE_REACT_DOC, "React Guide", "shared", "Frontend", "doc_react")
    temp_retriever.ingest_document(SAMPLE_SYSTEM_DESIGN_DOC, "System Design Guide", "shared", "Architecture", "doc_sys_design")

    # Query 1: FastAPI Concurrency
    q1_res = temp_retriever.search("FastAPI async def event loop threadpool", top_k=3)
    assert q1_res.total_results > 0
    top_doc = q1_res.results[0]
    assert top_doc.document_id == "doc_fastapi"
    assert top_doc.similarity_score > 0.0

    # Query 2: React State & Keys
    q2_res = temp_retriever.search("React reconciliation Virtual DOM stable key props", top_k=3)
    assert q2_res.total_results > 0
    assert q2_res.results[0].document_id == "doc_react"

    # Query 3: Caching Topologies
    q3_res = temp_retriever.search("Redis Cache-Aside Write-Through B-Tree index", top_k=3)
    assert q3_res.total_results > 0
    assert q3_res.results[0].document_id == "doc_sys_design"


def test_scope_filtering(temp_retriever):
    temp_retriever.ingest_document(SAMPLE_FASTAPI_DOC, "FastAPI Guide", "shared", "Backend", "doc_shared_fastapi")
    temp_retriever.ingest_document(SAMPLE_JOB_DOC, "Nexus Standards", "job_specific", "Architecture", "doc_job_nexus")

    # Scope Filter: job_specific only
    job_res = temp_retriever.search("platform architecture latency", scope="job_specific", top_k=5)
    assert job_res.total_results > 0
    for item in job_res.results:
        assert item.scope == "job_specific"
        assert item.document_id == "doc_job_nexus"

    # Scope Filter: shared only
    shared_res = temp_retriever.search("FastAPI architecture", scope="shared", top_k=5)
    assert shared_res.total_results > 0
    for item in shared_res.results:
        assert item.scope == "shared"


def test_source_id_provenance(temp_retriever):
    temp_retriever.ingest_document(SAMPLE_FASTAPI_DOC, "FastAPI Guide", "shared", "Backend", "doc_fastapi_prov")
    search_res = temp_retriever.search("async def vs def", top_k=1)
    assert len(search_res.results) == 1
    top_chunk = search_res.results[0]

    # Verify ID structure and provenance traceability
    assert top_chunk.chunk_id.startswith("doc_fastapi_prov_c")
    assert top_chunk.source_name == "FastAPI Guide"
    assert top_chunk.document_id == "doc_fastapi_prov"
    assert top_chunk.chunk_index == 0
    assert "FastAPI" in top_chunk.text


def test_persistence_across_restarts():
    temp_dir = tempfile.mkdtemp(prefix="chroma_persist_test_")
    try:
        mock_embeddings = EmbeddingService(use_mock_fallback=True)
        # Instance 1: Ingest
        r1 = KnowledgeRetriever(persist_dir=temp_dir, embedding_service=mock_embeddings)
        r1.ingest_document(SAMPLE_FASTAPI_DOC, "Persistent Guide", "shared", "Backend", "doc_persist")

        # Instance 2: Brand new instance pointing to same directory
        r2 = KnowledgeRetriever(persist_dir=temp_dir, embedding_service=mock_embeddings)
        docs = r2.list_documents()
        assert len(docs) == 1
        assert docs[0].document_id == "doc_persist"

        # Search on restarted instance
        res = r2.search("async def", top_k=1)
        assert len(res.results) == 1
        assert res.results[0].document_id == "doc_persist"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delete_document(temp_retriever):
    temp_retriever.ingest_document(SAMPLE_FASTAPI_DOC, "FastAPI Guide", "shared", "Backend", "doc_to_delete")
    assert any(d.document_id == "doc_to_delete" for d in temp_retriever.list_documents())

    deleted = temp_retriever.delete_document("doc_to_delete")
    assert deleted is True
    assert not any(d.document_id == "doc_to_delete" for d in temp_retriever.list_documents())

    # Searching should return 0 results
    res = temp_retriever.search("FastAPI", top_k=5)
    assert len(res.results) == 0

