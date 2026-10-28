import os
os.environ["USE_MOCK_EMBEDDINGS"] = "1"
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_DOC_TEXT = """
# API Rate Limiting and Resilience Patterns
Token bucket and leaky bucket algorithms govern high-throughput client API rate limiting.
Exponential backoff with jitter prevents thundering herd problems on downstream services.
Circuit breakers transition between Closed, Open, and Half-Open states to isolate failing dependencies.
"""


def test_api_ingest_and_list_document():
    # Ingest via API
    res = client.post(
        "/api/knowledge/ingest",
        data={
            "text": SAMPLE_DOC_TEXT,
            "source_name": "API Resilience Patterns",
            "scope": "shared",
            "topic": "System Architecture",
            "document_id": "doc_api_resilience",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == "doc_api_resilience"
    assert data["chunks_created"] > 0
    assert data["status"] in ["ingested", "already_indexed"]

    # List documents
    list_res = client.get("/api/knowledge/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["document_id"] == "doc_api_resilience" for d in docs)


def test_api_search_knowledge():
    search_res = client.post(
        "/api/knowledge/search",
        json={
            "query": "circuit breaker token bucket rate limit",
            "top_k": 3,
        },
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_results"] > 0
    top_result = search_data["results"][0]
    assert "token bucket" in top_result["text"].lower() or "circuit breaker" in top_result["text"].lower()
    assert top_result["similarity_score"] > 0




def test_api_search_with_scope_filter():
    search_res = client.post(
        "/api/knowledge/search",
        json={
            "query": "circuit breaker",
            "scope": "shared",
            "top_k": 2,
        },
    )
    assert search_res.status_code == 200
    for item in search_res.json()["results"]:
        assert item["scope"] == "shared"


def test_api_seed_defaults():
    res = client.post("/api/knowledge/seed-defaults")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_seeded"] >= 3


def test_api_delete_document():
    # Ingest a temp document
    client.post(
        "/api/knowledge/ingest",
        data={
            "text": "Temporary document content for deletion test purpose.",
            "source_name": "Temp Deletion Target",
            "scope": "shared",
            "topic": "Testing",
            "document_id": "doc_to_delete_api",
        },
    )

    del_res = client.delete("/api/knowledge/documents/doc_to_delete_api")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Deleting again should return 404
    del_404 = client.delete("/api/knowledge/documents/doc_to_delete_api")
    assert del_404.status_code == 404

