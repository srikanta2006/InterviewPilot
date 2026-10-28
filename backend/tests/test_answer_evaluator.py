from unittest.mock import MagicMock
from app.schemas.evaluation import calculate_weighted_score
from app.schemas.knowledge import SearchResultItem
from app.services.answer_evaluator import (
    AnswerEvaluator,
    LLMEvaluationPayload,
)
from app.services.groq_client import GroqClientService


def create_sample_chunks():
    return [
        SearchResultItem(
            chunk_id="chunk_fastapi_001",
            document_id="doc_fastapi",
            source_name="FastAPI Concurrency Guide",
            scope="shared",
            topic="Python FastAPI Concurrency",
            chunk_index=0,
            text="FastAPI runs async def endpoints on the main asyncio event loop thread. Synchronous blocking calls must be offloaded via run_in_threadpool or asyncio.to_thread.",
            similarity_score=0.91,
            distance=0.18,
            metadata={"doc_hash": "hash123"},
        ),
        SearchResultItem(
            chunk_id="chunk_fastapi_002",
            document_id="doc_fastapi",
            source_name="FastAPI Concurrency Guide",
            scope="shared",
            topic="Python FastAPI Concurrency",
            chunk_index=1,
            text="Dependency injection with Depends manages connection pools and cleanup handlers using yield syntax within the request scope.",
            similarity_score=0.86,
            distance=0.28,
            metadata={"doc_hash": "hash123"},
        ),
    ]


def test_evaluation_fallback_comprehensive_answer():
    evaluator = AnswerEvaluator(groq_client=GroqClientService(api_key="placeholder_key"))
    chunks = create_sample_chunks()

    question_text = "How does FastAPI handle asynchronous endpoints and synchronous blocking I/O?"
    criteria = [
        "async def running on main event loop",
        "Event loop blocking from synchronous calls",
        "Offloading blocking calls to threadpool",
    ]
    candidate_answer = (
        "In FastAPI, defining a route with async def executes the handler directly on the main event loop thread. "
        "If you perform a blocking synchronous call inside async def, it starves the entire event loop and blocks all other concurrent requests. "
        "To prevent event loop blocking, you should offload synchronous blocking operations to a threadpool using run_in_threadpool or regular def."
    )

    result = evaluator.evaluate(
        session_id="sess_123",
        question_id="q_123",
        question_text=question_text,
        competency="Python FastAPI Concurrency",
        difficulty="Hard",
        expected_criteria=criteria,
        candidate_answer=candidate_answer,
        retrieved_chunks=chunks,
    )

    assert result.session_id == "sess_123"
    assert result.question_id == "q_123"
    assert result.evaluation_status == "completed"
    assert result.dimension_scores.correctness >= 4
    assert result.dimension_scores.completeness >= 4

    # Backend score matches formula
    expected_score = calculate_weighted_score(
        correctness=result.dimension_scores.correctness,
        completeness=result.dimension_scores.completeness,
        relevance=result.dimension_scores.relevance,
        clarity=result.dimension_scores.clarity,
    )
    assert result.weighted_score == expected_score

    # Citations must be grounded in provided chunks
    assert len(result.citation_chunk_ids) > 0
    for cid in result.citation_chunk_ids:
        assert cid in ["chunk_fastapi_001", "chunk_fastapi_002"]
    assert len(result.citations) == len(result.citation_chunk_ids)


def test_evaluation_fallback_empty_or_trivial_answer():
    evaluator = AnswerEvaluator(groq_client=GroqClientService(api_key="placeholder_key"))
    chunks = create_sample_chunks()

    result = evaluator.evaluate(
        session_id="sess_trivial",
        question_id="q_trivial",
        question_text="Explain FastAPI concurrency model.",
        competency="FastAPI",
        difficulty="Medium",
        expected_criteria=["Event loop", "Threadpool offloading"],
        candidate_answer="idk pass",
        retrieved_chunks=chunks,
    )

    # Poor / trivial answer receives very low scores
    assert result.dimension_scores.correctness == 0
    assert result.dimension_scores.completeness == 0
    assert result.weighted_score <= 10.0
    assert len(result.missing_concepts) >= 2
    assert "too brief" in result.actionable_feedback.lower()


def test_insufficient_evidence_handling():
    """When no reference chunks are found, evaluation is explicitly marked as insufficient_evidence."""
    evaluator = AnswerEvaluator(groq_client=GroqClientService(api_key="placeholder_key"))

    result = evaluator.evaluate(
        session_id="sess_no_evidence",
        question_id="q_no_evidence",
        question_text="Discuss esoteric quantum algorithms.",
        competency="Quantum Computing",
        difficulty="Hard",
        expected_criteria=["Quantum Fourier Transform"],
        candidate_answer="A detailed discussion on quantum phase estimation.",
        retrieved_chunks=[],  # Empty retrieval
    )

    assert result.evaluation_status == "insufficient_evidence"
    assert result.weighted_score == 0.0
    assert len(result.citation_chunk_ids) == 0
    assert "insufficient evidence" in result.actionable_feedback.lower()


def test_citation_validation_rejects_hallucinations():
    """If LLM outputs invented/hallucinated chunk IDs, evaluator discards them and preserves only valid IDs."""
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True
    mock_groq.extract_structured_json.return_value = LLMEvaluationPayload(
        correctness=5,
        completeness=4,
        relevance=5,
        clarity=4,
        strengths=["Clear explanation"],
        missing_concepts=["Monitoring metrics"],
        actionable_feedback="Great answer.",
        suggested_citation_chunk_ids=[
            "chunk_fastapi_001",  # Valid chunk
            "chunk_hallucinated_xyz",  # Hallucinated ID
            "invented_fake_chunk_999",  # Hallucinated ID
        ],
        is_insufficient_evidence=False,
    )

    evaluator = AnswerEvaluator(groq_client=mock_groq)
    chunks = create_sample_chunks()

    result = evaluator.evaluate(
        session_id="sess_hallucination_check",
        question_id="q_hallucination_check",
        question_text="How does FastAPI handle concurrency?",
        competency="FastAPI",
        difficulty="Medium",
        expected_criteria=["Event loop"],
        candidate_answer="It uses an async event loop with asyncio.",
        retrieved_chunks=chunks,
    )

    # Hallucinated IDs must be filtered out!
    assert result.citation_chunk_ids == ["chunk_fastapi_001"]
    assert "chunk_hallucinated_xyz" not in result.citation_chunk_ids
    assert "invented_fake_chunk_999" not in result.citation_chunk_ids
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chunk_fastapi_001"


def test_malformed_groq_response_activates_fallback():
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True
    mock_groq.extract_structured_json.return_value = None  # Simulates malformed response

    evaluator = AnswerEvaluator(groq_client=mock_groq)
    chunks = create_sample_chunks()

    result = evaluator.evaluate(
        session_id="sess_malformed",
        question_id="q_malformed",
        question_text="How does FastAPI dependency injection work?",
        competency="FastAPI",
        difficulty="Medium",
        expected_criteria=["Depends", "Request scope cleanup"],
        candidate_answer="FastAPI uses Depends to provide yield fixtures and clean up resources per request scope.",
        retrieved_chunks=chunks,
    )

    # Evaluator succeeds via fallback
    assert result.evaluation_id.startswith("eval_")
    assert result.evaluation_status == "completed"
    assert result.dimension_scores.correctness >= 3
    assert result.weighted_score > 0.0

